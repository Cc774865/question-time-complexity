"""Score one question paper and write the single output docx.

The page calls this when 开始工作 is clicked. Stars are assigned only after
τ exists. Homework and promotion are judged only when that paper has them,
and only after the stars exist.
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import replace
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

from problem_time.arrange_docx import _classed_homework, split_blocks, write_star_preview
from problem_time.calibration import dimension_weights_for, score_calibrated_problem, uses_upper_grade_weights
from problem_time.early_number_counts import early_number_counts, uses_early_picture_numbers
from problem_time.equation_text import equation_text
from problem_time.grade_context import load_grade_context
from problem_time.grade_use import GradeUseError, read_grade_use_with_filename
from problem_time.paper_sections import paper_sections
from problem_time.read_images import ImageReadError, deepseek_reader, stem_images
from problem_time.solution_counts import solution_counts
from problem_time.stars import SIMILAR_STAR_LEVEL, assign_levels, assign_stars
from problem_time.structure_counts import structure_counts
from problem_time.textbook_models import shadow_familiarity

_MATH = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"
_STOP = re.compile(r"^[【\[]?(答案|解析|详解|解题方法)")

_LEVEL_ORDER = {"B": 0, "A": 1, "AA": 2, "AAA": 3, "S": 4}


class PaperRunError(RuntimeError):
    """The paper cannot be scored. The message is shown on the progress bar."""


def run_started(inbox: Path, image_reader=None) -> dict:
    """Score every docx or markdown named in ``inbox/start.json``."""
    progress = inbox / "progress.json"
    current = ""
    try:
        sources = _sources_from_start(inbox)
        if image_reader is None:
            api_key = _api_key(inbox)
            image_reader = deepseek_reader(api_key) if api_key else None
        batch: list[dict] = []
        used: set[str] = set()
        primary: dict | None = None
        total = len(sources)
        for index, (original, source) in enumerate(sources):
            current = original
            _write_progress(progress, 8 + int(70 * index / total), f"正在计算 {index + 1}/{total}")
            scratch = inbox / f".batch-{index}.docx"
            result = run_paper(source, scratch, progress, image_reader)
            preview_name = _unique_preview_name(str(result["filename"]), used)
            scratch.replace(inbox / preview_name)
            result["previewName"] = preview_name
            result["previewBytes"] = (inbox / preview_name).stat().st_size
            result["inputName"] = original
            if index == 0:
                shutil.copyfile(inbox / preview_name, inbox / "preview.docx")
                primary = result
            batch.append({
                "filename": result["filename"],
                "previewName": preview_name,
                "previewBytes": result["previewBytes"],
                "inputName": original,
            })
        assert primary is not None
        primary["batch"] = batch
        (inbox / "result.json").write_text(
            json.dumps(primary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        _write_progress(progress, 100, "预览已生成，可拖拽调整星级", running=False)
        return primary
    except (PaperRunError, GradeUseError, ImageReadError) as exc:
        _clear_previous(inbox)
        message = f"{current}：{exc}" if current else str(exc)
        _write_progress(progress, 0, message, running=False)
        raise
    except Exception as exc:
        _clear_previous(inbox)
        _write_progress(progress, 0, "计算没有完成", running=False)
        raise PaperRunError("计算没有完成") from exc


def run_paper(source: Path, dest: Path, progress: Path | None = None, image_reader=None) -> dict:
    """Copy ``source`` into ``dest``, changing only stars, class headings, and order."""
    document = Document(source)
    header, lessons, homework, promotion = split_blocks(document)
    header_text = "\n".join(_plain_text(element) for element in header)
    grade = read_grade_use_with_filename(header_text, source.name)
    knowledge_context = load_grade_context(grade.code, grade.grades)
    week, lesson = _week_and_lesson(header_text)
    if not lessons:
        raise PaperRunError("这份稿里没有题目")
    lesson_rows = _with_pictures(document, lessons, image_reader, progress, grade.grades)

    from_solution = any(solution for _, solution, _mode in lesson_rows)
    from_early = any(mode == "early" for _stem, _solution, mode in lesson_rows)
    if from_early:
        label = "正在按看图认数计算 τ"
    elif from_solution:
        label = "正在按解析计算 τ"
    else:
        label = "正在计算 τ"
    _write_progress(progress, 45, label)
    weights = dimension_weights_for(grade.code, grade.grades)
    scored = [
        _score_block(index, stem, solution, mode, grade.grades, weights)
        for index, (stem, solution, mode) in enumerate(lesson_rows)
    ]
    ranked = assign_stars(_pairs(scored))

    sections = paper_sections("\n".join(paragraph.text for paragraph in document.paragraphs))
    review: list[dict] = []
    if sections.homework or sections.promotion:
        _write_progress(progress, 60, "作业题和晋级题留给人工审核")
        if sections.homework:
            for index, block in enumerate(homework):
                review.append(_review_item("homework", index, _stem_text(block)))
        if sections.promotion:
            for index, block in enumerate(promotion):
                review.append(_review_item("promotion", index, _stem_text(block)))
    elif homework or promotion:
        raise PaperRunError("作业题或晋级题的标题认不出来")

    lesson_plan = []
    for row in sorted(ranked, key=lambda item: int(item["star"])):
        lesson_plan.append((int(row["example_block"]), int(row["star"]), "例"))
        if int(row["practice_block"]) != int(row["example_block"]):
            lesson_plan.append((int(row["practice_block"]), int(row["star"]), "练"))
    result = {
        "filename": f"{week}-{grade.code}-{lesson}.docx",
        "copied": True,
        "released": False,
        "preview": True,
        "previewCount": 0,
        "previewRevisions": [],
        "source": source.name,
        "header": {"week": week, "grade": grade.code, "lesson": lesson},
        "knowledgeContext": knowledge_context.report(),
        "weightRule": "upper" if uses_upper_grade_weights(grade.code, grade.grades) else "standard",
        "dimensionWeights": {
            key: weights[key] for key in ("prereq", "reasoning", "compute", "error")
        },
        "base": {
            "lessons": [list(item) for item in lesson_plan],
            "homework": [],
            "promotion": [],
        },
        "familiarityShadow": [
            {
                "block": int(row["block"]),
                "role": "例" if int(row["block"]) % 2 == 0 else "练",
                **row["familiarity_shadow"],
            }
            for row in scored
        ],
        "review": review,
    }
    _write_progress(progress, 85, "正在写出预览")
    write_star_preview(source, dest, lesson_plan)
    result["previewBytes"] = dest.stat().st_size
    return result


def _sources_from_start(inbox: Path) -> list[tuple[str, Path]]:
    start = inbox / "start.json"
    if not start.is_file():
        raise PaperRunError("还没有开始")
    payload = json.loads(start.read_text(encoding="utf-8"))
    names = [str(name) for name in payload.get("files", [])]
    sources: list[tuple[str, Path]] = []
    for name in names:
        source = inbox / Path(name).name
        lower = source.name.lower()
        if lower.endswith(".docx"):
            if not source.is_file():
                raise PaperRunError("找不到这份输入")
            sources.append((source.name, source))
            continue
        if not lower.endswith((".md", ".markdown")):
            continue
        if not source.is_file():
            raise PaperRunError("找不到这份输入")
        from problem_time.markdown_docx import write_markdown_docx

        working = inbox / f".{source.stem}.docx"
        write_markdown_docx(source, working)
        sources.append((source.name, working))
    if not sources:
        raise PaperRunError("开始工作需要一份 docx 或 md")
    return sources


def _unique_preview_name(filename: str, used: set[str]) -> str:
    stem = Path(filename).stem or "预览"
    name = f"{stem}-预览.docx"
    serial = 2
    while name in used:
        name = f"{stem}-预览-{serial}.docx"
        serial += 1
    used.add(name)
    return name


def _source_from_start(inbox: Path) -> Path:
    start = inbox / "start.json"
    if not start.is_file():
        raise PaperRunError("还没有开始")
    payload = json.loads(start.read_text(encoding="utf-8"))
    names = [str(name) for name in payload.get("files", [])]
    chosen = next((name for name in names if name.lower().endswith(".docx")), "")
    if chosen:
        source = inbox / Path(chosen).name
        if not source.is_file():
            raise PaperRunError("找不到这份输入")
        return source
    markdown = next((name for name in names if name.lower().endswith((".md", ".markdown"))), "")
    if not markdown:
        raise PaperRunError("开始工作需要一份 docx 或 md")
    source = inbox / Path(markdown).name
    if not source.is_file():
        raise PaperRunError("找不到这份输入")
    from problem_time.markdown_docx import write_markdown_docx

    working = inbox / f".{source.stem}.docx"
    write_markdown_docx(source, working)
    return working


def _with_pictures(document, blocks: list[list], image_reader, progress: Path | None, grades: tuple[int, ...] = ()) -> list[tuple[str, str | None, str]]:
    rows: list[tuple[str, str | None, str]] = []
    total = len(blocks)
    for index, block in enumerate(blocks):
        text = _stem_text(block)
        if _early_picture(grades, text, block):
            _write_progress(
                progress,
                15 + int(25 * index / max(total, 1)),
                f"正在按看图认数计算 {index + 1}/{total}",
            )
            rows.append((text, None, "early"))
            continue
        if _digits_missing(text) and _has_figure_or_formula(block):
            solution = _solution_text(document, block)
            if _usable_solution(solution):
                _write_progress(
                    progress,
                    15 + int(25 * index / max(total, 1)),
                    f"正在按解析计算 {index + 1}/{total}",
                )
                rows.append((text, solution, ""))
                continue
        images = stem_images(document, block)
        written = text
        if images and image_reader is not None:
            _write_progress(progress, 15 + int(25 * index / max(total, 1)), f"正在读图 {index + 1}/{total}")
            text = f"{text}\n{image_reader(images, text)}".strip()
        elif images and _digits_missing(text) and _needs_a_digit(written):
            raise PaperRunError("题干里的数字在图片中。请先在输入区填写 DeepSeek 读图 API")
        if images and _digits_missing(text) and _needs_a_digit(written):
            raise PaperRunError("读图之后仍然没有数字，所以没有出文件")
        rows.append((text, None, ""))
    return rows


def _early_picture(grades: tuple[int, ...], text: str, block: list) -> bool:
    return uses_early_picture_numbers(grades, text) and _has_figure_or_formula(block)


def _digits_missing(text: str) -> bool:
    return re.search(r"\d", text) is None


def _has_figure_or_formula(block: list) -> bool:
    for element in _before_answer(block):
        if element.find(".//" + qn("a:blip")) is not None:
            return True
        if element.find(".//" + _MATH + "oMath") is not None:
            return True
        if any(node.tag.endswith("OLEObject") for node in element.iter()):
            return True
    return False


def _before_answer(block: list):
    for element in block:
        if _STOP.match(_plain_text(element)):
            break
        yield element


def _usable_solution(text: str) -> bool:
    if re.search(r"\d", text):
        return True
    return re.search(r"全等|相似|SAS|ASA|SSS|中线|三边|[<>≤≥=＝]", text) is not None


def _solution_text(document, block: list) -> str:
    """Readable 解析. Equation text is for scoring only."""
    started = False
    lines: list[str] = []
    for element in block:
        line = _math_line(document, element)
        if not started:
            if re.match(r"^[【\[]?(解析|详解)", line):
                started = True
                rest = re.sub(r"^[【\[]?(解析|详解)\s*[:：]?\s*", "", line)
                if rest:
                    lines.append(rest)
            continue
        if line.startswith("解题方法") or re.match(r"^\d+\s*星", line) or line.startswith("题目"):
            break
        if line:
            lines.append(line)
    return "\n".join(lines)


def _math_line(document, element) -> str:
    parts: list[str] = []
    for node in element.iter():
        if node.tag == qn("w:t") and node.text:
            parts.append(node.text)
        elif node.tag == _MATH + "t" and node.text:
            parts.append(node.text)
        elif node.tag.endswith("OLEObject"):
            relation = node.get(qn("r:id"))
            if not relation:
                continue
            part = document.part.related_parts.get(relation)
            if part is not None:
                parts.append(equation_text(part.blob))
    return "".join(parts).replace("\u200b", "").strip()


def _needs_a_digit(text: str) -> bool:
    """A bare picture stem still needs a digit. A written geometry question does not."""
    return len(re.findall(r"[\u4e00-\u9fff]", text)) < 12


def _api_key(inbox: Path) -> str:
    path = inbox / "vision.json"
    if not path.is_file():
        return ""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return str(payload.get("api_key") or "").strip()


def lesson_cards(source: Path, lessons: list) -> list[dict]:
    """One card per star, with the example and practice text a person can recognize."""
    blocks: list = []
    if source.is_file():
        _, blocks, _, _ = split_blocks(Document(source))
    grouped: dict[int, dict] = {}
    for item in lessons:
        block, star, role = int(item[0]), int(item[1]), str(item[2])
        card = grouped.setdefault(star, {"star": star, "example": "", "practice": "", "example_block": block})
        text = _short(_stem_text(blocks[block])) if 0 <= block < len(blocks) else ""
        if role == "练":
            card["practice"] = text
        else:
            card["example"] = text
            card["example_block"] = block
    return [grouped[star] for star in sorted(grouped)]


def _score_block(
    index: int,
    stem: str,
    solution: str | None,
    mode: str = "",
    grades: tuple[int, ...] = (),
    weights: dict[str, float] | None = None,
) -> dict:
    if mode == "early":
        counts = early_number_counts(stem)
    elif solution:
        counts = solution_counts(solution, stem)
    else:
        counts = structure_counts(stem)
    familiarity = shadow_familiarity(stem, solution or "", grades, counts)
    if familiarity["affectsFormalTau"]:
        counts = replace(counts, familiarity=float(familiarity["formalF"]))
    scored = score_calibrated_problem(
        f"lesson-{index}",
        stem,
        counts,
        role="例" if index % 2 == 0 else "练",
        weights=weights,
    )
    return {
        "block": index,
        "stem": stem,
        "tau": scored["tau"],
        "familiarity_shadow": familiarity,
    }


def _pairs(scored: list[dict]) -> list[dict]:
    pairs = []
    index = 0
    while index < len(scored):
        example = scored[index]
        practice = scored[index + 1] if index + 1 < len(scored) else example
        pairs.append({
            "tau_example": example["tau"],
            "tau_practice": practice["tau"],
            "example_block": example["block"],
            "practice_block": practice["block"],
            "example_stem": example["stem"],
            "practice_stem": practice["stem"],
        })
        index += 2
    return pairs


def _stems_by_star(ranked: list[dict], stems: list[str]) -> dict[int, str]:
    grouped: dict[int, str] = {}
    for row in ranked:
        star = int(row["star"])
        example = stems[int(row["example_block"])]
        practice = stems[int(row["practice_block"])]
        grouped[star] = f"{example}\n{practice}"
    return grouped


# Digit overlap below this is not a class. The block stays in the file as N.
_CLEAR_MATCH = 0.5


def _place(kind: str, stems: list[str], by_star: dict[int, str], ranked: list[dict], review: list[dict]):
    ready = []
    for index, stem in enumerate(stems):
        star = _similar_star(stem, by_star)
        if star is None:
            review.append(_review_item(kind, index, stem))
            continue
        ready.append({"similar_star": star, "stem": stem, "block": index})
    placed_rows = assign_levels(ready, kind, ranked) if ready else []
    kept: list[tuple[int, str] | tuple[int, int]] = []
    for row in placed_rows:
        if row.get("review") or row.get("level") is None:
            review.append(_review_item(kind, int(row["block"]), str(row["stem"])))
            continue
        if kind == "homework":
            kept.append((int(row["block"]), str(row["level"])))
        else:
            kept.append((int(row["block"]), int(row["similar_star"])))
    if kind == "homework":
        kept.sort(key=lambda item: _LEVEL_ORDER[str(item[1])])
    return kept, review


def _review_item(kind: str, index: int, stem: str) -> dict:
    return {
        "kind": "作业题" if kind == "homework" else "晋级题",
        "group": kind,
        "block": index,
        "level": "",
        "text": _short(stem),
    }


def _similar_star(stem: str, by_star: dict[int, str]) -> int | None:
    candidates = {star: text for star, text in by_star.items() if star in SIMILAR_STAR_LEVEL}
    if not candidates:
        raise PaperRunError("还没有可以对应的星级")
    best_star = min(candidates)
    best_score = -1.0
    left = _marks(stem)
    for star, text in candidates.items():
        score = _overlap(left, _marks(text))
        if score > best_score or (score == best_score and star < best_star):
            best_score = score
            best_star = star
    if best_score < _CLEAR_MATCH:
        return None
    if best_star not in SIMILAR_STAR_LEVEL:
        raise PaperRunError("归班时星级不在 2 到 8")
    return best_star


def _marks(text: str) -> set[str]:
    return set(re.findall(r"\d+|[+＋\-－×÷*/()（）□△○]", text))


def _overlap(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _stem_text(block: list) -> str:
    lines = []
    for element in block:
        text = _plain_text(element)
        if re.match(r"^[【\[]?(答案|解析|详解|解题方法)", text):
            break
        if re.match(r"^\d+\s*星\s*[-－—]\s*[例练]", text):
            continue
        if text.startswith("作业题") or _classed_homework(text) or text.startswith("晋级题"):
            continue
        if text.startswith(("星级", "班型", "课件", "题目类型")):
            continue
        if text.startswith("题目"):
            text = re.sub(r"^题目\s*[:：]?\s*", "", text)
        if text:
            lines.append(text)
    return "\n".join(lines)


def _plain_text(element) -> str:
    return "".join(node.text or "" for node in element.findall(".//" + qn("w:t"))).replace("\u200b", "").strip()


def _week_and_lesson(header: str) -> tuple[str, str]:
    week = ""
    lesson = ""
    for raw in header.splitlines():
        line = raw.replace("\u200b", "").strip()
        found_week = re.search(r"(?:周次|课次)\s*[:：]\s*(W\d+)", line, re.IGNORECASE)
        if found_week:
            week = found_week.group(1).upper()
        found_lesson = re.search(r"课次\s*[:：]\s*(\d+)\s*$", line)
        if found_lesson:
            lesson = found_lesson.group(1)
        if not week:
            bare = re.search(r"(W\d+)", line, re.IGNORECASE)
            if bare:
                week = bare.group(1).upper()
    if not week or not lesson:
        raise PaperRunError("课头里要有周次和课次")
    return week, lesson


def _short(stem: str) -> str:
    line = next((item.strip() for item in stem.splitlines() if item.strip()), "题目")
    return line if len(line) <= 80 else line[:80]


def _clear_previous(inbox: Path) -> None:
    for name in ("result.json", "output.docx", "preview.docx"):
        path = inbox / name
        if path.is_file():
            path.unlink()
    for path in inbox.glob("preview-*.docx"):
        if path.is_file():
            path.unlink()
    for path in inbox.glob("*-预览*.docx"):
        if path.is_file():
            path.unlink()
    for path in inbox.glob(".batch-*.docx"):
        if path.is_file():
            path.unlink()


def _write_progress(path: Path | None, percent: int, label: str, running: bool = True) -> None:
    if path is None:
        return
    path.write_text(
        json.dumps({"running": running, "percent": percent, "label": label}, ensure_ascii=False),
        encoding="utf-8",
    )
