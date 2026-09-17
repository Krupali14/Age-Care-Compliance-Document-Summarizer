# How risk severity and priority are decided

Answers the question "how do we know a risk is high, medium or low?" — where the
judgement is made, which file holds the prompt that makes it, and what happens to
the value afterwards. Nothing in this pipeline scores risk arithmetically: the
model reads the section and labels it, and every other layer only carries or
displays that label.

## Short answer

| Field | Model | Values | Decided by |
|---|---|---|---|
| Risk `severity` | `ExtractedRisk` | `high` / `medium` / `low` (required) | the LLM, from the section text |
| Obligation `priority` | `ExtractedObligation` | `high` / `medium` / `low` or null | the LLM, optional |
| Action item `priority` | `ExtractedActionItem` | `high` / `medium` / `low` or null | the LLM, optional |

## Where the prompt lives

`backend/app/services/extraction.py` — `PROMPT_TEMPLATE`. One instruction block is
sent per batch of sections. The clause that produces severity is:

> "...any risks (with severity high/medium/low), any deadlines (with responsible
> role if stated), and any action items (with responsible role, timeframe, and
> priority where possible)."

Two other clauses in the same prompt constrain it:

- *"Only extract what is explicitly stated or clearly implied in the text — do not
  invent details."* — the label must be supportable from the section, not from what
  the heading suggests.
- Table-of-contents fragments and heading-only sections return nothing at all, so
  they never produce a rated risk.

## How the value is constrained

`backend/app/services/extraction.py`:

```python
class ExtractedRisk(BaseModel):
    text: str
    severity: Literal["high", "medium", "low"]
```

The `Literal` is what makes the three levels the only possible answers. The call in
`extract_batch()` uses `with_structured_output(BatchExtraction, method="json_schema")`
— OpenAI strict structured output — so the schema is enforced by the API rather than
suggested: a fourth level such as "critical", or a missing severity, cannot come
back. On risks the field is required; on obligations and action items `priority` is
optional, so a null there means the model saw no basis for a rating, not that the
item is low priority.

A batch whose response fails validation is discarded and its sections are
re-extracted one at a time (`process_document()` in
`backend/app/services/processing.py`), so a bad severity loses one call, never the
document.

## Where it is stored and shown

- Stored: `backend/app/models/risk.py` — `severity = Column(String, nullable=False)`.
  Free text at the database level; the schema above is what keeps it to three values.
- Served: `backend/app/routers/risks.py` — passed through unchanged.
- Displayed: `frontend/src/components/CategoryTable.tsx` — `TONE_BAR` / `TONE_TEXT`
  map the level to a colour (high → coral, medium → amber, low → sage). The maps also
  accept `critical` so an older row rendered rather than falling back to grey.

## What this means in practice

- The rating is a **model judgement, not a computed score**. There is no likelihood ×
  consequence matrix, no keyword table, and no per-organisation risk appetite input.
- It is **section-local**. Each risk is rated from the one section it was found in;
  the model does not see the rest of the document when rating it.
- It is **not stable across re-processing**. Re-running extraction on the same
  document can move a borderline risk between medium and high.
- It is **not auditable to a rule**. If a user asks why a risk is high, the only
  honest answer today is the section text it was drawn from — which is why every row
  links back to its source section.

## If a defensible, repeatable rating is needed

The smallest change that gets there, in order:

1. Put the rubric in the prompt — define what high/medium/low mean for aged care
   (e.g. high = direct risk to resident safety or a reportable breach), so the label
   follows a stated standard instead of the model's prior.
2. Have the model return the reason alongside the level, and store it, so the rating
   can be reviewed.
3. Only then consider a deterministic score (likelihood × consequence) with the model
   supplying the two inputs rather than the answer.

Steps 1 and 2 are prompt and schema edits in `extraction.py` plus one column on
`risks`; step 3 changes the data model and the UI.
