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


BODY = [
    "The System Governor must allocate places to eligible individuals.",
    "A registered provider must report an incident within 24 hours.",
    "Supporters may access information held about the individual.",
    "Conditions on registration continue until the registration ends.",
    "The Commission may vary a provider's registration category.",
    "Fees payable are worked out under the Fees and Payments Principles.",
    "An approved needs assessor conducts the assessment.",
    "The Minister may determine a guaranteed number of places.",
    "Reconsideration of a reviewable decision may be requested.",
    "This Part does not limit any other provision of this Act.",
    "A civil penalty provision applies to a contravention.",
    "The Rules may prescribe matters of a transitional nature.",
]


def test_strip_running_headers_drops_page_numbered_furniture():
    from app.services.docling_parser import _strip_running_headers

    # Running header repeats at the top of every page, varying only by page number.
    pages = [
        f"Aged Care Act 2024 {n}\nCompilation No. 2\n"
        + "\n".join(BODY[(n - 1 + k) % len(BODY)] for k in range(7))
        for n in range(1, len(BODY) + 1)
    ]
    kept = _strip_running_headers(pages)

    flat = [line for page in kept for line, _page_no in page]
    assert not any(line.startswith(("Aged Care Act", "Compilation")) for line in flat)
    assert flat.count(BODY[0]) == 7
    assert kept[3][0][1] == 4  # page numbers survive the strip


def test_strip_running_headers_keeps_repeated_body_text():
    from app.services.docling_parser import _strip_running_headers

    # A clause repeated mid-page is content, not furniture: only margin lines
    # are eligible for stripping.
    boilerplate = "Nothing in this section limits section 12."
    pages = [
        f"Aged Care Act 2024 {n}\n"
        + "\n".join(BODY[(n - 1 + k) % len(BODY)] for k in range(4))
        + f"\n{boilerplate}\n"
        + "\n".join(BODY[(n + k) % len(BODY)] for k in range(3))
        + "\nPage footer"
        for n in range(1, len(BODY) + 1)
    ]
    flat = [line for page in _strip_running_headers(pages) for line, _ in page]
    assert flat.count(boilerplate) == len(BODY)


def test_strip_running_headers_drops_toc_dot_leaders():
    from app.services.docling_parser import _strip_running_headers

    pages = [
        f"24 Effect of Statement of Rights..................... {n}\n{BODY[n - 1]}"
        for n in range(1, len(BODY) + 1)
    ]
    flat = [line for page in _strip_running_headers(pages) for line, _ in page]
    assert flat == BODY


def test_split_oversize_chunks_to_ceiling():
    from app.services.docling_parser import MAX_SECTION_CHARS, _split_oversize

    parts = _split_oversize("Part 1", "3", "x" * (MAX_SECTION_CHARS * 2 + 10))
    assert len(parts) == 3
    assert parts[0][0] == "Part 1"
    assert "cont." in parts[1][0]
    assert all(len(text) <= MAX_SECTION_CHARS for _h, _p, text in parts)


def test_parse_pdf_text_layer_splits_on_headings(monkeypatch):
    import app.services.docling_parser as dp

    pages = [
        "Part 1—Preliminary\nThis Act commences on 1 July 2026.",
        "Part 2—Obligations\nA provider must report incidents.",
    ]
    monkeypatch.setattr(dp, "_page_texts", lambda _path: pages)

    sections = dp._parse_pdf_text_layer("/tmp/whatever.pdf")

    assert [s.heading for s in sections] == ["Part 1—Preliminary", "Part 2—Obligations"]
    assert sections[0].page_ref == "1"
    assert sections[1].page_ref == "2"
    assert "report incidents" in sections[1].raw_text


def test_parse_document_falls_back_to_docling_without_text_layer(monkeypatch):
    import app.services.docling_parser as dp

    monkeypatch.setattr(dp, "_has_text_layer", lambda _path: False)
    fake_result = MagicMock()
    fake_result.document.export_to_markdown.return_value = "# Only Heading\nBody text.\n"

    with patch("app.services.docling_parser.DocumentConverter") as MockConverter:
        MockConverter.return_value.convert.return_value = fake_result
        sections = dp.parse_document("/tmp/scanned.pdf")

    assert [s.heading for s in sections] == ["Only Heading"]
