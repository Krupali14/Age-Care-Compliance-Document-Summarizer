from unittest.mock import MagicMock, patch

from app.services.docling_parser import ParsedSection


def test_extract_section_calls_llm_with_structured_output():
    fake_extraction = MagicMock()
    fake_structured_llm = MagicMock()
    fake_structured_llm.invoke.return_value = fake_extraction

    fake_llm = MagicMock()
    fake_llm.with_structured_output.return_value = fake_structured_llm

    section = ParsedSection(heading="Obligations", order_idx=0, page_ref=None, raw_text="Staff must report incidents.")

    with patch("app.services.extraction.get_llm", return_value=fake_llm):
        from app.services.extraction import extract_section
        result = extract_section(section)

    assert result is fake_extraction
    fake_llm.with_structured_output.assert_called_once()
    fake_structured_llm.invoke.assert_called_once()
    call_arg = fake_structured_llm.invoke.call_args[0][0]
    assert "Obligations" in call_arg
    assert "Staff must report incidents." in call_arg
