import re
from dataclasses import dataclass

from docling.document_converter import DocumentConverter


@dataclass
class ParsedSection:
    heading: str
    order_idx: int
    page_ref: str | None
    raw_text: str


def parse_document(file_path: str) -> list[ParsedSection]:
    converter = DocumentConverter()
    result = converter.convert(file_path)
    markdown = result.document.export_to_markdown()

    parts = re.split(r"^#{1,6}\s+(.+)$", markdown, flags=re.MULTILINE)
    # parts[0] is any preamble before the first heading; then alternating (heading, body)
    sections: list[ParsedSection] = []
    order_idx = 0
    for i in range(1, len(parts), 2):
        heading = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        sections.append(ParsedSection(heading=heading, order_idx=order_idx, page_ref=None, raw_text=body))
        order_idx += 1

    if not sections and markdown.strip():
        sections.append(ParsedSection(heading="Document", order_idx=0, page_ref=None, raw_text=markdown.strip()))

    return sections
