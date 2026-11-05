"""Reorder a question paper without rewriting its text.

Only star headings, class headings, and block order may change.
题干、答案、解析, including pictures, are copied from the source.
"""

from __future__ import annotations

import re
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
        block = lesson_blocks[index]
        if not block or not _retitle_lesson(block[0], star, role):
            body.append(_heading(f"{star}星-{role}"))
        for element in block:
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
        if level == "N":
            _mark_unplaced(block)
        else:
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
        if text.startswith("题目") and kind == "lesson" and current is not None and _only_lesson_heading(current):
            current.append(element)
            continue
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
    if _LESSON_HEADING.match(text):
        return "lesson"
    if text.startswith("题目") and current not in {"homework", "promotion"}:
        return "lesson"
    return ""


_LESSON_HEADING = re.compile(r"^\d+\s*星\s*[-－—]\s*[例练]")


def _retitle_lesson(element, star: int, role: str) -> bool:
    """Replace an existing star heading in place, keeping its parenthetical note."""
    text = _plain_text(element)
    match = _LESSON_HEADING.match(text)
    if not match:
        return False
    _set_plain_text(element, f"{star}星-{role}{text[match.end():]}")
    return True


def _only_lesson_heading(block: list) -> bool:
    texts = [text for element in block if (text := _plain_text(element))]
    return bool(texts) and all(_LESSON_HEADING.match(text) for text in texts)


def _classed_homework(text: str) -> bool:
    for level in ("AAA", "AA", "A", "B", "S", "N"):
        if text.startswith(f"{level}-作业题") or text.startswith(f"{level}作业题"):
            return True
    return False


def _with_level(original: str, level: str, marker: str) -> str:
    for prefix in ("AAA-", "AA-", "A-", "B-", "S-", "N-"):
        if original.startswith(prefix) and marker in original:
            original = original[len(prefix):]
            break
    return f"{level}-{original}"


def _classed_heading(original: str, level: str) -> str:
    return f"{level}-作业题"


def _mark_unplaced(block: list) -> None:
    """Leave a promotion block in the file and mark its class as undecided."""
    for element in block:
        text = _plain_text(element)
        if text.startswith("星级") or text.startswith("班型"):
            _set_plain_text(element, "班型：N")
            return
    block.insert(1, _heading("班型：N"))


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


_LEVEL_ORDER = {"B": 0, "A": 1, "AA": 2, "AAA": 3, "S": 4, "N": 5}


def write_plan(source: Path, dest: Path, result: dict) -> None:
    """Write the docx from a scored plan.

    A review item with no class stays in the file: homework headings become
    ``N-作业题``, and a promotion block is marked ``班型：N``.
    """
    base = result["base"]
    homework = [tuple(item) for item in base["homework"]]
    classes: list[tuple[int, str]] = []
    for item in result["review"]:
        level = item.get("level") or "N"
        if item["group"] == "homework":
            homework.append((int(item["block"]), level))
        else:
            classes.append((int(item["block"]), level))
    homework.sort(key=lambda item: (_LEVEL_ORDER[str(item[1])], int(item[0])))
    classes.sort(key=lambda item: (_LEVEL_ORDER[str(item[1])], int(item[0])))
    arrange_docx(
        source,
        dest,
        [tuple(item) for item in base["lessons"]],
        homework,
        [tuple(item) for item in base["promotion"]],
        classes,
    )


def order_lesson_stars(result: dict, example_blocks: list[int]) -> None:
    """Assign stars from the top of the list downward, starting at 2."""
    lessons = result["base"]["lessons"]
    star_by_example: dict[int, int] = {}
    for item in lessons:
        if str(item[2]) == "例":
            star_by_example[int(item[0])] = int(item[1])
    blocks = [int(block) for block in example_blocks]
    if set(blocks) != set(star_by_example) or len(blocks) != len(star_by_example):
        raise ValueError("这份排序和正课对不上")
    new_star = {block: 2 + index for index, block in enumerate(blocks)}
    old_to_new = {star_by_example[block]: new_star[block] for block in blocks}
    for item in lessons:
        item[1] = old_to_new[int(item[1])]


def apply_review_levels(inbox: Path, result: dict) -> None:
    """Rebuild the output from the source, adding any class a person picked."""
    source = inbox / result["source"]
    dest = inbox / "output.docx"
    write_plan(source, dest, result)
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
