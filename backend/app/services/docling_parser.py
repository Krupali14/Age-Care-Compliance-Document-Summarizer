import logging
import re
from collections import Counter
from dataclasses import dataclass

import pypdfium2 as pdfium
from docling.document_converter import DocumentConverter

logger = logging.getLogger(__name__)

# A single LLM extraction call gets one section's raw_text, so an unbounded
# section (a 1.1M-char act with no detected headings) is unsendable. Oversize
# sections are split at this ceiling.
MAX_SECTION_CHARS = 6000

# Most lines at the top/bottom of a page that can be a running header/footer.
# Capped to a fraction of the page so a short page isn't entirely "margin".
HEADER_LINES = 6
FOOTER_LINES = 3

# Lines that look like a structural heading: "Part 5", "Division 1", "Section 92A",
# "3.2 Incident reporting", "12A Definitions".
_HEADING_RE = re.compile(
    r"^(?:(?:Chapter|Part|Division|Subdivision|Schedule|Section|Appendix|Annexure|Annex)\s+\d+[A-Za-z]?\b.*"
    r"|\d+(?:\.\d+)*[A-Za-z]?[.)]?\s+[A-Z].*)$"
)


@dataclass
class ParsedSection:
    heading: str
    order_idx: int
    page_ref: str | None
    raw_text: str


def _has_text_layer(file_path: str) -> bool:
    """True when the PDF carries embedded text, so OCR would be wasted work."""
    try:
        pdf = pdfium.PdfDocument(file_path)
        chars = sum(
            len(pdf[i].get_textpage().get_text_bounded()) for i in range(min(len(pdf), 20))
        )
        return chars > 200
    except Exception:  # noqa: BLE001 - not a readable PDF; let docling decide
        return False


def _page_texts(file_path: str) -> list[str]:
    pdf = pdfium.PdfDocument(file_path)
    return [page.get_textpage().get_text_bounded() for page in pdf]


# Table-of-contents entries ("24 Effect of Statement of Rights.......... 12")
# match the heading pattern but carry no content.
_DOT_LEADER_RE = re.compile(r"\.{4,}")


def _norm(line: str) -> str:
    """Running headers differ only by their page/section number."""
    return re.sub(r"\d+", "#", line)


def _strip_running_headers(pages: list[str]) -> list[list[tuple[str, int]]]:
    """Drop per-page running headers/footers, keeping (line, page_no) pairs."""
    lines_per_page = [[ln.strip() for ln in p.splitlines()] for p in pages]
    # Only lines at the top or bottom of a page can be furniture. Without this,
    # digit-normalised matching would also delete body lines that legitimately
    # repeat (e.g. a boilerplate clause appearing on half the pages).
    margins = [
        set(page[: min(HEADER_LINES, max(1, len(page) // 3))])
        | set(page[-min(FOOTER_LINES, max(1, len(page) // 4)) :])
        for page in lines_per_page
    ]
    counts = Counter(_norm(ln) for page in margins for ln in page if ln)
    threshold = max(3, int(len(pages) * 0.5))
    furniture = {ln for ln, n in counts.items() if n >= threshold} if len(pages) > 5 else set()
    return [
        [
            (ln, page_no)
            for ln in page
            if ln
            and not (_norm(ln) in furniture and ln in margins[page_no - 1])
            and not _DOT_LEADER_RE.search(ln)
        ]
        for page_no, page in enumerate(lines_per_page, start=1)
    ]


def _split_oversize(heading: str, page_ref: str | None, text: str) -> list[tuple[str, str | None, str]]:
    if len(text) <= MAX_SECTION_CHARS:
        return [(heading, page_ref, text)]
    out = []
    for i in range(0, len(text), MAX_SECTION_CHARS):
        part = text[i : i + MAX_SECTION_CHARS]
        label = heading if i == 0 else f"{heading} (cont. {i // MAX_SECTION_CHARS + 1})"
        out.append((label, page_ref, part))
    return out


def _parse_pdf_text_layer(file_path: str) -> list[ParsedSection]:
    """Fast path: read the embedded text layer instead of running the docling
    layout+OCR pipeline. Measured at ~0.8s vs ~2h for a 654-page PDF."""
    pages = _page_texts(file_path)
    cleaned = _strip_running_headers(pages)

    chunks: list[tuple[str, str | None, list[str]]] = []
    for page in cleaned:
        for line, page_no in page:
            if _HEADING_RE.match(line) and len(line) <= 120:
                chunks.append((line, str(page_no), []))
            elif chunks:
                chunks[-1][2].append(line)
            else:
                chunks.append(("Document", str(page_no), [line]))

    sections: list[ParsedSection] = []
    for heading, page_ref, body in chunks:
        text = "\n".join(body).strip()
        if not text:
            continue
        for h, pr, part in _split_oversize(heading, page_ref, text):
            sections.append(
                ParsedSection(heading=h, order_idx=len(sections), page_ref=pr, raw_text=part)
            )
    return sections


# ponytail: cache the converter per DocumentConverter class object rather than in a
# plain global — building one reloads the layout/table models, and keying on the
# class keeps tests that patch DocumentConverter from sharing a stale instance.
_converter_cache: dict[type, DocumentConverter] = {}


def _converter() -> DocumentConverter:
    cls = DocumentConverter
    converter = _converter_cache.get(cls)
    if converter is None:
        converter = _converter_cache[cls] = cls()
    return converter


def _parse_with_docling(file_path: str) -> list[ParsedSection]:
    result = _converter().convert(file_path)
    markdown = result.document.export_to_markdown()

    parts = re.split(r"^#{1,6}\s+(.+)$", markdown, flags=re.MULTILINE)
    # parts[0] is any preamble before the first heading; then alternating (heading, body)
    sections: list[ParsedSection] = []
    for i in range(1, len(parts), 2):
        heading = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        for h, _pr, part in _split_oversize(heading, None, body):
            sections.append(
                ParsedSection(heading=h, order_idx=len(sections), page_ref=None, raw_text=part)
            )

    if not sections and markdown.strip():
        for h, _pr, part in _split_oversize("Document", None, markdown.strip()):
            sections.append(
                ParsedSection(heading=h, order_idx=len(sections), page_ref=None, raw_text=part)
            )

    return sections


def parse_document(file_path: str) -> list[ParsedSection]:
    if file_path.lower().endswith(".pdf") and _has_text_layer(file_path):
        try:
            sections = _parse_pdf_text_layer(file_path)
            if sections:
                return sections
        except Exception:  # noqa: BLE001 - fall back to the full pipeline
            logger.exception("Text-layer parse failed for %s, falling back to docling", file_path)
    # Scanned PDFs (no text layer) and DOCX go through docling, OCR included.
    return _parse_with_docling(file_path)
