from unittest.mock import MagicMock, patch


def test_parse_document_splits_into_sections():
    fake_result = MagicMock()
    fake_result.document.export_to_markdown.return_value = (
        "# Introduction\nThis is the intro.\n\n"
        "# Obligations\nStaff must report incidents within 24 hours.\n"
    )

    with patch("app.services.docling_parser.DocumentConverter") as MockConverter:
        MockConverter.return_value.convert.return_value = fake_result

        from app.services.docling_parser import parse_document
        sections = parse_document("/tmp/fake.pdf")

    assert len(sections) == 2
    assert sections[0].heading == "Introduction"
    assert sections[0].order_idx == 0
    assert "intro" in sections[0].raw_text
    assert sections[1].heading == "Obligations"
    assert sections[1].order_idx == 1


def test_parse_document_splits_on_h2_headings():
    fake_result = MagicMock()
    fake_result.document.export_to_markdown.return_value = (
        "Preamble text before any heading.\n\n"
        "## 1. Resident Information\nResident details here.\n\n"
        "## 2. Incident Summary\nIncident details here.\n"
    )

    with patch("app.services.docling_parser.DocumentConverter") as MockConverter:
        MockConverter.return_value.convert.return_value = fake_result

        from app.services.docling_parser import parse_document
        sections = parse_document("/tmp/fake.pdf")

    assert len(sections) == 2
    assert sections[0].heading == "1. Resident Information"
    assert "Resident details" in sections[0].raw_text
    assert "Incident details" not in sections[0].raw_text
    assert sections[1].heading == "2. Incident Summary"
    assert "Incident details" in sections[1].raw_text
