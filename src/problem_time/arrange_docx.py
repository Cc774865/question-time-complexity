"""Reorder a question paper without rewriting its text.

Only star headings, class headings, and block order may change.
题干、答案、解析, including pictures, are copied from the source.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from lxml import etree

_XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


def arrange_docx(
    source: Path,
    dest: Path,
    lessons: list[tuple[int, int, str]],
    homework: list[tuple[int, str]],
    promotion: list[tuple[int, int]],
    promotion_classes: list[tuple[int, str]] | None = None,
) -> None:
    """Write ``dest`` from ``source``.

    ``lessons`` is ``(block_index, star, role)`` in output order.
    ``homework`` is ``(block_index, level)`` for blocks that stay.
    ``promotion`` is ``(block_index, star)`` for blocks that stay.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, dest)
    document = Document(dest)
    header, lesson_blocks, homework_blocks, promotion_blocks = split_blocks(document)
    body = document.element.body
    sect = body.find(qn("w:sectPr"))
    for child in list(body):
        if child is not sect:
            body.remove(child)

    for element in header:
        body.append(element)
    for index, star, role in lessons:
        body.append(_heading(f"{star}星-{role}"))
        for element in lesson_blocks[index]:
            body.append(element)
    for index, level in homework:
        block = homework_blocks[index]
        _set_plain_text(block[0], _classed_heading(_plain_text(block[0]), level))
        for element in block:
            body.append(element)
    for index, star in promotion:
        block = promotion_blocks[index]
        for element in block:
            if _plain_text(element).startswith("星级"):
                _set_plain_text(element, f"星级：{star}star")
            body.append(element)
    for index, level in promotion_classes or []:
        block = promotion_blocks[index]
        _set_plain_text(block[0], _with_level(_plain_text(block[0]), level, "晋级题"))
        for element in block:
            body.append(element)
    if sect is not None:
        body.append(sect)
    document.save(dest)


def split_blocks(document: Document) -> tuple[list, list[list], list[list], list[list]]:
    header: list = []
    lessons: list[list] = []
    homework: list[list] = []
    promotion: list[list] = []
    current: list | None = None
    kind = ""
    for element in document.element.body.iterchildren():
        if element.tag != qn("w:p"):
            if current is None:
                header.append(element)
            else:
                current.append(element)
            continue
        text = _plain_text(element)
        start = _block_kind(text, kind)
        if start:
            current = [element]
            kind = start
            {"lesson": lessons, "homework": homework, "promotion": promotion}[kind].append(current)
            continue
        if current is None:
            header.append(element)
        else:
            current.append(element)
    return header, lessons, homework, promotion


def _block_kind(text: str, current: str) -> str:
    if text.startswith("作业题") or _classed_homework(text):
        return "homework"
    if text.startswith("晋级题"):
        return "promotion"
    if text.startswith("题目") and current not in {"homework", "promotion"}:
        return "lesson"
    return ""


def _classed_homework(text: str) -> bool:
    for level in ("AAA", "AA", "A", "B", "S"):
        if text.startswith(f"{level}-作业题") or text.startswith(f"{level}作业题"):
            return True
    return False


def _with_level(original: str, level: str, marker: str) -> str:
    for prefix in ("AAA-", "AA-", "A-", "B-", "S-"):
        if original.startswith(prefix) and marker in original:
            original = original[len(prefix):]
            break
    return f"{level}-{original}"


def _classed_heading(original: str, level: str) -> str:
    for prefix in ("AAA-", "AA-", "A-", "B-", "S-", "AAA", "AA", "A", "B", "S"):
        if original.startswith(prefix) and "作业题" in original[len(prefix):len(prefix) + 4]:
            original = original[len(prefix):].lstrip("-")
            break
    return f"{level}-{original}"


def _plain_text(element) -> str:
    return "".join(node.text or "" for node in element.findall(".//" + qn("w:t"))).replace("\u200b", "").strip()


def _set_plain_text(element, text: str) -> None:
    if element.find(".//" + qn("a:blip")) is not None:
        raise ValueError("含图片的段落不能改字")
    nodes = element.findall(".//" + qn("w:t"))
    if not nodes:
        run = OxmlElement("w:r")
        node = OxmlElement("w:t")
        node.set(_XML_SPACE, "preserve")
        node.text = text
        run.append(node)
        element.append(run)
        return
    nodes[0].set(_XML_SPACE, "preserve")
    nodes[0].text = text
    for extra in nodes[1:]:
        extra.text = ""


_LEVEL_ORDER = {"B": 0, "A": 1, "AA": 2, "AAA": 3, "S": 4}


def apply_review_levels(inbox: Path, result: dict) -> None:
    """Rebuild the output from the source, adding any class a person picked."""
    source = inbox / result["source"]
    dest = inbox / "output.docx"
    base = result["base"]
    homework = [tuple(item) for item in base["homework"]]
    classes: list[tuple[int, str]] = []
    for item in result["review"]:
        level = item.get("level") or ""
        if not level:
            continue
        if item["group"] == "homework":
            homework.append((int(item["block"]), level))
        else:
            classes.append((int(item["block"]), level))
    homework.sort(key=lambda item: _LEVEL_ORDER[item[1]])
    classes.sort(key=lambda item: _LEVEL_ORDER[item[1]])
    arrange_docx(
        source,
        dest,
        [tuple(item) for item in base["lessons"]],
        homework,
        [tuple(item) for item in base["promotion"]],
        classes,
    )
    result["bytes"] = dest.stat().st_size


def _heading(text: str) -> etree._Element:
    paragraph = OxmlElement("w:p")
    run = OxmlElement("w:r")
    node = OxmlElement("w:t")
    node.set(_XML_SPACE, "preserve")
    node.text = text
    run.append(node)
    paragraph.append(run)
    return paragraph
