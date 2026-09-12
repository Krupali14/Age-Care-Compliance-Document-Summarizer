import logging
import re
from calendar import monthrange
from datetime import date
from typing import Literal

from pydantic import BaseModel, field_validator

from app.services.docling_parser import ParsedSection
from app.services.llm import get_llm

logger = logging.getLogger(__name__)

# One LLM round-trip per section is the dominant cost on a long document, so
# sections are packed into a single call up to these ceilings.
# Batching trades two costs against each other: each call repeats a fixed
# instruction block (favouring few large calls), while a call's latency tracks the
# tokens it has to generate (favouring many small calls run in parallel). Measured
# on a 1300-section act, these sizes sit near the floor of that curve.
# The response carries a summary plus findings for every section in the batch, and a
# batch that overruns the model's output-token limit comes back as truncated,
# unparseable JSON — losing the whole call. These cap what one response has to hold.
MAX_BATCH_SECTIONS = 8
MAX_BATCH_CHARS = 6000

# How much of the document the relevance gate sees before deciding.
RELEVANCE_SAMPLE_CHARS = 6000


class ExtractedObligation(BaseModel):
    text: str
    responsible_role: str | None = None
    priority: Literal["high", "medium", "low"] | None = None


class ExtractedRisk(BaseModel):
    text: str
    severity: Literal["high", "medium", "low"]


class ExtractedDeadline(BaseModel):
    description: str
    due_date: str | None = None
    responsible_role: str | None = None


class ExtractedActionItem(BaseModel):
    text: str
    responsible_role: str | None = None
    timeframe: str | None = None
    priority: Literal["high", "medium", "low"] | None = None


class SectionExtraction(BaseModel):
    summary: str

    @field_validator("summary", mode="before")
    @classmethod
    def _coerce_summary(cls, value: object) -> str:
        """The summary is specified as Markdown bullets, and models routinely hand
        those back as a list of strings instead of one block. Rejecting that costs
        the whole batch its result, so join it instead."""
        if isinstance(value, list):
            return "\n".join(str(v).strip() for v in value if str(v).strip())
        if value is None:
            return ""
        return str(value)
    obligations: list[ExtractedObligation] = []
    risks: list[ExtractedRisk] = []
    deadlines: list[ExtractedDeadline] = []
    action_items: list[ExtractedActionItem] = []


class IndexedSectionExtraction(SectionExtraction):
    index: int
    heading: str
    # Re-declared without defaults on purpose. An optional list is a list the model
    # is allowed to omit, and in a batch of eight sections it omits all four of them
    # and returns summaries alone — an obligation-dense standards document came back
    # with zero obligations while the same sections extracted one at a time yielded
    # three apiece. Required fields force the key into every object, so "nothing
    # here" has to be an explicit empty list rather than a silent omission.
    obligations: list[ExtractedObligation]
    risks: list[ExtractedRisk]
    deadlines: list[ExtractedDeadline]
    action_items: list[ExtractedActionItem]


class BatchExtraction(BaseModel):
    sections: list[IndexedSectionExtraction] = []


class RelevanceCheck(BaseModel):
    is_relevant: bool
    reason: str


DEADLINE_RULES = """Today's date is {today}. Deadlines must be actionable from today \
onwards:
- If the document states a specific calendar date that is still in the future, set \
due_date to that date in YYYY-MM-DD form.
- Otherwise set due_date to the timeframe as stated relative to its trigger, e.g. \
"within 30 days of the incident", "1 month after commencement", "2 months".
- Never output a date that has already passed. Commencement dates, past amendments, \
historical reporting periods and superseded dates are not deadlines — omit them.
- A section that only records past dates has no deadlines; return an empty list for it."""


# The instruction block is held ahead of the section text so it forms a stable
# prefix across calls, which the API can serve from its prompt cache.
PROMPT_TEMPLATE = """You are analysing sections of an aged-care compliance document.

For EACH section supplied below, return an object carrying that section's "index" and \
its "heading" copied exactly as given, plus: a \
summary of the section, any obligations (things people/the organisation are required \
to do), any risks (with severity high/medium/low), any deadlines (with responsible \
role if stated), and any action items (with responsible role, timeframe, and priority \
where possible). Return one object per section, with no index repeated or omitted. \
Only extract what is explicitly stated or clearly implied in the text — do not invent \
details. If a section's text is only a heading, a cross-reference, or a table-of-\
contents entry with no substantive content, return an empty summary and no \
obligations, risks, deadlines or action items for it. Never describe what a section \
probably contains or what its title suggests — summarise only text you were given.

{deadline_rules}

Format each summary as Markdown bullet points — 1 to 3 bullets, each starting with \
"- ", one sentence each. Use a single bullet for a short, procedural or definitional \
section; only a dense section with several distinct duties needs three. Use emphasis \
to make the bullet scannable:

- **Bold** the hard facts: the duty itself, the responsible role, any date or \
deadline, and any dollar amount, number, or threshold.
- *Italicise* the qualifiers: conditions and exceptions ("*unless the provider \
notifies the Commission*"), and cross-references to other provisions \
("*see section 91*").

Bold and italicise individual terms or short phrases only — never a whole \
sentence, and never both marks on the same words. Do not add a heading or any \
text outside the bullets.

{sections}"""


RELEVANCE_PROMPT = """You are the intake filter for an aged-care compliance \
summariser. Your only job is to catch documents that are plainly not compliance \
material. You are not judging quality, completeness or how the document is written.

IN SCOPE — always relevant, and the most common case:
- Legislation, Acts, Bills, Rules, Regulations, determinations and compilations
- Quality standards, guidelines, codes of practice, regulatory guidance
- Provider policies, procedures, manuals, position descriptions
- Audit reports, assessment reports, notices, contracts, agreements
- Governance, clinical governance, incident, complaints and risk material

A document is in scope even when the pages shown are only a cover page, a title \
page, front matter, a table of contents, endnotes or a schedule — long documents \
begin that way, and later pages carry the substance.

OUT OF SCOPE — the only reason to answer false:
- Invoices, receipts, bank statements, purchase orders, payslips
- Résumés, CVs, job applications, personal correspondence
- Marketing brochures, newsletters, event flyers
- Photos, raw data dumps, or a file with no readable text

Filename: {filename}
Beginning of the document:
{sample}

If the document is anything on the in-scope list, or you are unsure which list it \
belongs to, answer is_relevant = true. Answer false only when it clearly matches the \
out-of-scope list. Set reason to one short sentence, addressed to the user, saying \
what the document appears to be and why it cannot be summarised."""


_MONTHS = {
    m: i
    for i, names in enumerate(
        [
            ("january", "jan"), ("february", "feb"), ("march", "mar"), ("april", "apr"),
            ("may",), ("june", "jun"), ("july", "jul"), ("august", "aug"),
            ("september", "sep", "sept"), ("october", "oct"), ("november", "nov"),
            ("december", "dec"),
        ],
        start=1,
    )
    for m in names
}

# Dates as documents actually write them: "11 August 2026", "August 11, 2026",
# "11/08/2026", and the month-only "August 2026". Matched anywhere in the string so
# a phrase like "by 31 December 2026" is still recognised as carrying a date.
_DAY_MONTH_YEAR = re.compile(r"\b(\d{1,2})\s+([A-Za-z]{3,9})\.?,?\s+(\d{4})\b")
_MONTH_DAY_YEAR = re.compile(r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b")
_NUMERIC_DMY = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b")
_MONTH_YEAR = re.compile(r"\b([A-Za-z]{3,9})\.?\s+(\d{4})\b")
_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")


def _latest_date_in(value: str) -> date | None:
    """The date a due-date string refers to, or None if it names no calendar date.

    Returns the *last* day the string could mean, so a month without a day ("August
    2026") only counts as past once that whole month has gone by.
    """
    try:
        for match in _DAY_MONTH_YEAR.finditer(value):
            day, month, year = match.group(1), _MONTHS.get(match.group(2).lower()), match.group(3)
            if month:
                return date(int(year), month, int(day))
        for match in _MONTH_DAY_YEAR.finditer(value):
            month, day, year = _MONTHS.get(match.group(1).lower()), match.group(2), match.group(3)
            if month:
                return date(int(year), month, int(day))
        for match in _NUMERIC_DMY.finditer(value):
            # Australian day-first ordering, matching the documents this reads.
            return date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
        for match in _MONTH_YEAR.finditer(value):
            month, year = _MONTHS.get(match.group(1).lower()), int(match.group(2))
            if month:
                return date(year, month, monthrange(year, month)[1])
    except ValueError:
        # A malformed date ("31 February 2026") tells us nothing reliable.
        return None
    years = [int(y) for y in _YEAR.findall(value)]
    return date(max(years), 12, 31) if years else None


def normalize_due_date(value: str | None, today: date | None = None) -> str | None:
    """Keep future dates and relative timeframes; drop dates already in the past.

    A commencement date from 2019 is not a deadline, and neither is one from three
    weeks ago — showing either as "due" is the thing users complained about.
    Relative phrasing ("within 30 days of the incident") names no calendar date and
    survives untouched.
    """
    if not value or not value.strip():
        return None
    value = value.strip()
    today = today or date.today()
    try:
        return value if date.fromisoformat(value) >= today else None
    except ValueError:
        pass
    when = _latest_date_in(value)
    return None if when is not None and when < today else value


def _headings_match(returned: str, expected: str) -> bool:
    """Lenient identity check — the model may re-space or re-case what it echoes."""
    norm = lambda h: re.sub(r"[^a-z0-9]", "", h.lower())[:30]  # noqa: E731
    a, b = norm(returned), norm(expected)
    return bool(a) and bool(b) and (a == b or a.startswith(b) or b.startswith(a))


def _batch(indexed: list[tuple[int, ParsedSection]]) -> list[list[tuple[int, ParsedSection]]]:
    batches: list[list[tuple[int, ParsedSection]]] = []
    current: list[tuple[int, ParsedSection]] = []
    size = 0
    for i, section in indexed:
        length = len(section.raw_text)
        if current and (len(current) >= MAX_BATCH_SECTIONS or size + length > MAX_BATCH_CHARS):
            batches.append(current)
            current, size = [], 0
        current.append((i, section))
        size += length
    if current:
        batches.append(current)
    return batches


def _render(indexed: list[tuple[int, ParsedSection]]) -> str:
    return "\n\n".join(
        f"--- Section index {i} ---\nSection heading: {s.heading}\nSection text:\n{s.raw_text}"
        for i, s in indexed
    )


def extract_batch(indexed: list[tuple[int, ParsedSection]]) -> dict[int, SectionExtraction]:
    """Extract several sections in one LLM call, keyed by the caller's index."""
    llm = get_llm()
    # json_schema (OpenAI strict structured outputs) enforces the required fields
    # above; the default function_calling mode treats the schema as a hint and lets
    # the model drop them.
    structured_llm = llm.with_structured_output(BatchExtraction, method="json_schema")
    prompt = PROMPT_TEMPLATE.format(
        sections=_render(indexed),
        deadline_rules=DEADLINE_RULES.format(today=date.today().isoformat()),
    )
    result = structured_llm.invoke(prompt)

    by_index = dict(indexed)
    out: dict[int, SectionExtraction] = {}
    for item in result.sections:
        section = by_index.get(item.index)
        # An index the model invented, returned twice, or paired with the wrong
        # heading means the result cannot be trusted to belong to this section.
        # Dropping it leaves the index missing, and the caller re-extracts it alone
        # rather than filing another section's findings under it.
        if section is None or item.index in out:
            continue
        if not _headings_match(item.heading, section.heading):
            logger.warning(
                "Discarding extraction for section index %s: model returned heading %r for %r",
                item.index, item.heading, section.heading,
            )
            continue
        for deadline in item.deadlines:
            deadline.due_date = normalize_due_date(deadline.due_date)
        out[item.index] = SectionExtraction(**item.model_dump(exclude={"index", "heading"}))
    return out


def plan_batches(
    indexed: list[tuple[int, ParsedSection]],
) -> list[list[tuple[int, ParsedSection]]]:
    """Group (index, section) pairs into the calls that will extract them."""
    return _batch(indexed)


def extract_section(section: ParsedSection) -> SectionExtraction:
    """Single-section extraction — kept for callers that have just one section."""
    return extract_batch([(0, section)]).get(0, SectionExtraction(summary=""))


def check_relevance(filename: str, sections: list[ParsedSection]) -> RelevanceCheck:
    """One cheap call deciding whether this document is in scope at all."""
    # A long document opens with a cover page and a table of contents, so a sample
    # taken purely from the front tells you little about what it is. Take half from
    # the start and half from the middle, skipping heading-only fragments.
    substantive = [s for s in sections if len(s.raw_text) >= 80] or sections
    half = RELEVANCE_SAMPLE_CHARS // 2
    sample = ""
    for group, budget in ((substantive, half), (substantive[len(substantive) // 2:], half)):
        part = ""
        for section in group:
            part += f"{section.heading}\n{section.raw_text}\n"
            if len(part) >= budget:
                break
        sample += part[:budget]
    if not sample.strip():
        return RelevanceCheck(is_relevant=False, reason="No readable text was found in this file.")

    llm = get_llm()
    structured_llm = llm.with_structured_output(RelevanceCheck)
    return structured_llm.invoke(
        RELEVANCE_PROMPT.format(filename=filename, sample=sample[:RELEVANCE_SAMPLE_CHARS])
    )
