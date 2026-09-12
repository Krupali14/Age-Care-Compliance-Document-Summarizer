from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from app.services.docling_parser import ParsedSection
from app.services.extraction import (
    BatchExtraction, ExtractedDeadline, IndexedSectionExtraction, normalize_due_date, plan_batches,
)


def test_extract_section_calls_llm_with_structured_output():
    fake_extraction = BatchExtraction(
        sections=[IndexedSectionExtraction(
            index=0, heading="Obligations", summary="- **Staff** must report incidents.",
            obligations=[], risks=[], deadlines=[], action_items=[],
        )]
    )
    fake_structured_llm = MagicMock()
    fake_structured_llm.invoke.return_value = fake_extraction

    fake_llm = MagicMock()
    fake_llm.with_structured_output.return_value = fake_structured_llm

    section = ParsedSection(heading="Obligations", order_idx=0, page_ref=None, raw_text="Staff must report incidents.")

    with patch("app.services.extraction.get_llm", return_value=fake_llm):
        from app.services.extraction import extract_section
        result = extract_section(section)

    assert result.summary == "- **Staff** must report incidents."
    fake_llm.with_structured_output.assert_called_once()
    fake_structured_llm.invoke.assert_called_once()
    call_arg = fake_structured_llm.invoke.call_args[0][0]
    assert "Obligations" in call_arg
    assert "Staff must report incidents." in call_arg


def test_normalize_due_date_drops_past_dates_and_keeps_future_and_relative():
    today = date(2026, 9, 3)
    future = (today + timedelta(days=30)).isoformat()

    assert normalize_due_date(future, today) == future
    assert normalize_due_date(today.isoformat(), today) == today.isoformat()
    assert normalize_due_date("2019-07-01", today) is None
    assert normalize_due_date("commenced 1 July 2019", today) is None
    assert normalize_due_date("within 30 days of the incident", today) == "within 30 days of the incident"
    assert normalize_due_date("1 month", today) == "1 month"
    assert normalize_due_date(None, today) is None
    assert normalize_due_date("   ", today) is None


def test_normalize_due_date_reads_dates_as_documents_write_them():
    """A date that has passed is past whether or not it fell in an earlier year —
    the year alone cannot tell you, so the date itself has to be read."""
    today = date(2026, 9, 3)

    # Past, but in the current year: the case a year-only check cannot catch.
    assert normalize_due_date("11 August 2026", today) is None
    assert normalize_due_date("August 11, 2026", today) is None
    assert normalize_due_date("11/08/2026", today) is None
    assert normalize_due_date("Lodge notification by 31 Aug 2026", today) is None

    # Still ahead.
    assert normalize_due_date("31 December 2026", today) == "31 December 2026"
    assert normalize_due_date("1 October 2026", today) == "1 October 2026"
    assert normalize_due_date("15/10/2026", today) == "15/10/2026"

    # A month with no day only lapses once the whole month has.
    assert normalize_due_date("August 2026", today) is None
    assert normalize_due_date("September 2026", today) == "September 2026"

    # Relative phrasing names no calendar date and is left alone.
    assert normalize_due_date("24 hours after becoming aware of the incident", today) == \
        "24 hours after becoming aware of the incident"
    assert normalize_due_date("5 business days after the incident", today) == \
        "5 business days after the incident"
    # An impossible date is not evidence of anything, so the text is kept as written.
    assert normalize_due_date("31 February 2026", today) == "31 February 2026"


def test_extract_batch_normalises_deadlines_and_maps_by_index():
    sections = [
        ParsedSection(heading="A", order_idx=0, page_ref=None, raw_text="a"),
        ParsedSection(heading="B", order_idx=1, page_ref=None, raw_text="b"),
    ]
    batch_result = BatchExtraction(sections=[
        IndexedSectionExtraction(
            index=1, heading="B", summary="- b",
            obligations=[], risks=[], action_items=[],
            deadlines=[
                ExtractedDeadline(description="Old commencement", due_date="2019-07-01"),
                ExtractedDeadline(description="Report", due_date="within 30 days"),
            ],
        ),
        IndexedSectionExtraction(
            index=99, heading="Z", summary="- hallucinated index",
            obligations=[], risks=[], deadlines=[], action_items=[],
        ),
    ])
    fake_structured_llm = MagicMock()
    fake_structured_llm.invoke.return_value = batch_result
    fake_llm = MagicMock()
    fake_llm.with_structured_output.return_value = fake_structured_llm

    with patch("app.services.extraction.get_llm", return_value=fake_llm):
        from app.services.extraction import extract_batch
        out = extract_batch(list(enumerate(sections)))

    assert set(out) == {1}
    assert [d.due_date for d in out[1].deadlines] == [None, "within 30 days"]
    prompt = fake_structured_llm.invoke.call_args[0][0]
    assert "Section index 0" in prompt and "Section index 1" in prompt


def test_plan_batches_packs_sections_into_fewer_llm_calls():
    sections = [
        ParsedSection(heading=f"S{i}", order_idx=i, page_ref=None, raw_text="x" * 100)
        for i in range(20)
    ]
    batches = plan_batches(list(enumerate(sections)))

    assert len(batches) < len(sections)
    assert [i for batch in batches for i, _ in batch] == list(range(20))


def test_check_relevance_short_circuits_on_empty_document():
    with patch("app.services.extraction.get_llm") as get_llm:
        from app.services.extraction import check_relevance
        result = check_relevance("blank.pdf", [])

    assert result.is_relevant is False
    get_llm.assert_not_called()


def test_extract_batch_discards_results_attributed_to_the_wrong_section():
    """A heading that doesn't match means the findings belong to another section."""
    sections = [
        ParsedSection(heading="Incident reporting", order_idx=0, page_ref=None, raw_text="a"),
        ParsedSection(heading="Staff qualifications", order_idx=1, page_ref=None, raw_text="b"),
    ]
    batch_result = BatchExtraction(sections=[
        # Right index, wrong section's heading — must not be filed under index 0.
        IndexedSectionExtraction(
            index=0, heading="Staff qualifications", summary="- wrong",
            obligations=[], risks=[], deadlines=[], action_items=[],
        ),
        # Same content, re-cased and re-spaced — still the right section.
        IndexedSectionExtraction(
            index=1, heading="staff  qualifications", summary="- right",
            obligations=[], risks=[], deadlines=[], action_items=[],
        ),
    ])
    fake_structured_llm = MagicMock()
    fake_structured_llm.invoke.return_value = batch_result
    fake_llm = MagicMock()
    fake_llm.with_structured_output.return_value = fake_structured_llm

    with patch("app.services.extraction.get_llm", return_value=fake_llm):
        from app.services.extraction import extract_batch
        out = extract_batch(list(enumerate(sections)))

    assert set(out) == {1}
    assert out[1].summary == "- right"
