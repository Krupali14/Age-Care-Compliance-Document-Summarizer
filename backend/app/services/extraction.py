from typing import Literal

from pydantic import BaseModel

from app.services.docling_parser import ParsedSection
from app.services.llm import get_llm


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
    obligations: list[ExtractedObligation] = []
    risks: list[ExtractedRisk] = []
    deadlines: list[ExtractedDeadline] = []
    action_items: list[ExtractedActionItem] = []


PROMPT_TEMPLATE = """You are analysing a section of an aged-care compliance document.

Section heading: {heading}
Section text:
{text}

Extract: a short summary of this section, any obligations (things people/the \
organisation are required to do), any risks (with severity high/medium/low), \
any deadlines (with responsible role if stated), and any action items (with \
responsible role, timeframe, and priority where possible). Only extract what \
is explicitly stated or clearly implied in the text — do not invent details."""


def extract_section(section: ParsedSection) -> SectionExtraction:
    llm = get_llm()
    structured_llm = llm.with_structured_output(SectionExtraction)
    prompt = PROMPT_TEMPLATE.format(heading=section.heading, text=section.raw_text)
    return structured_llm.invoke(prompt)
