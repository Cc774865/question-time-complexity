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


def _heading(text: str) -> etree._Element:
    paragraph = OxmlElement("w:p")
    run = OxmlElement("w:r")
    node = OxmlElement("w:t")
    node.set(_XML_SPACE, "preserve")
    node.text = text
    run.append(node)
    paragraph.append(run)
    return paragraph
