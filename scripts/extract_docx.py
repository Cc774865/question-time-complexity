"""Extract auditable text inventory from a Word question paper.

Usage:
  python scripts/extract_docx.py path/to/questions.docx > inventory.json
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn


def normalized_hash(value: str) -> str:
    normalized = re.sub(r"\s+", "", value)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: extract_docx.py path/to/questions.docx", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    document = Document(path)
    paragraphs = [
        {"source_index": i, "text": paragraph.text, "hash": normalized_hash(paragraph.text)}
        for i, paragraph in enumerate(document.paragraphs)
        if paragraph.text.strip()
    ]
    tables = [
        {
            "table_index": table_index,
            "rows": [[cell.text for cell in row.cells] for row in table.rows],
        }
        for table_index, table in enumerate(document.tables)
    ]
    image_count = len(document.element.body.findall(".//" + qn("a:blip")))
    print(
        json.dumps(
            {
                "source_file": path.name,
                "paragraph_count": len(paragraphs),
                "table_count": len(tables),
                "image_count": image_count,
                "paragraphs": paragraphs,
                "tables": tables,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

