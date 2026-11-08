"""Turn a markdown question paper into the docx the scorer already reads.

The page accepts ``.md`` next to ``.docx``. Scoring, star order, and the
preview still go through the docx writer. ``解题方法`` is not an input.
"""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document

_FILE = re.compile(r"^(W\d+)-((?:ZKCC|GKCC|(?:L[1-9]\d*)+))-(\d+)", re.IGNORECASE)
_HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$")
_ROLE = re.compile(r"^(?:例题|练题|例|练)$")
_SKIP = re.compile(r"^解题方法$")
_STEM = re.compile(r"^题干$")
_ANSWER = re.compile(r"^答案$")
_SOLUTION = re.compile(r"^解析$")
_HOMEWORK = re.compile(r"^作业题$")
_PROMOTION = re.compile(r"^晋级题$")
_LATEX = (
    (r"\bigcirc", "○"),
    (r"\circ", "○"),
    (r"\blacktriangle", "△"),
    (r"\triangle", "△"),
    (r"\blacksquare", "□"),
    (r"\square", "□"),
    (r"\times", "×"),
    (r"\div", "÷"),
    (r"\cdot", "·"),
    (r"\underline", ""),
    (r"\quad", " "),
    (r"\qquad", " "),
)


def write_markdown_docx(source: Path, dest: Path) -> None:
    """Write ``dest`` as a docx whose paragraphs follow the markdown paper."""
    text = source.read_text(encoding="utf-8")
    document = Document()
    for line in markdown_paragraphs(text, source.stem):
        document.add_paragraph(line)
    dest.parent.mkdir(parents=True, exist_ok=True)
    document.save(dest)


def markdown_paragraphs(text: str, filename_stem: str) -> list[str]:
    """Map ``# 例`` / ``## 题干`` papers onto the paragraph labels the scorer uses."""
    body = text.replace("\r\n", "\n").replace("\ufeff", "")
    lines = body.splitlines()
    preamble: list[str] = []
    start = len(lines)
    for index, raw in enumerate(lines):
        if raw.strip().startswith("#"):
            start = index
            break
        line = _plain(raw)
        if line and line != "---":
            preamble.append(line)
    rows = _header("\n".join(preamble), filename_stem) + preamble
    skip = False
    for raw in lines[start:]:
        heading = _HEADING.match(raw.strip())
        if heading:
            title = _plain(heading.group(1))
            if _SKIP.match(title):
                skip = True
                continue
            skip = False
            label = _label(title)
            if label:
                rows.append(label)
            continue
        if skip or not raw.strip() or raw.strip() == "---":
            continue
        rows.append(_plain(raw))
    return rows


def _header(joined: str, filename_stem: str) -> list[str]:
    match = _FILE.match(filename_stem)
    rows: list[str] = []
    if not re.search(r"周次|课次", joined) and match:
        rows.append(f"周次：{match.group(1).upper()}")
    if "使用年级" not in joined and match:
        rows.append(f"使用年级：{match.group(2).upper()}")
    if not re.search(r"课次\s*[:：]\s*\d+\s*$", joined, re.MULTILINE) and match:
        rows.append(f"课次：{match.group(3)}")
    return rows


def _label(title: str) -> str:
    if _ROLE.match(title):
        return ""
    if _STEM.match(title):
        return "题目"
    if _ANSWER.match(title):
        return "答案"
    if _SOLUTION.match(title):
        return "解析"
    if _HOMEWORK.match(title):
        return "作业题"
    if _PROMOTION.match(title):
        return "晋级题"
    return ""


def _plain(line: str) -> str:
    text = line.replace("\u200b", "").strip()
    text = text.replace("$$", "").replace("$", "")
    for source, target in _LATEX:
        text = text.replace(source, target)
    text = text.replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", text).strip()
