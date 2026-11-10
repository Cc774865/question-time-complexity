"""Build the grade 1-9 textbook-model seed library.

The generated records are independently written model summaries.  They do
not contain textbook question text, answer choices, figures, or solutions.
Exact page and item locators stay null until checked against a licensed
physical/digital copyright page and textbook.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

def _project_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "知识库").is_dir() and (parent / "算法").is_dir():
            return parent
    raise RuntimeError("找不到题目时间复杂度项目根目录")


ROOT = _project_root()
KNOWLEDGE = ROOT / "知识库" / "知识点"
OUT = ROOT / "知识库" / "课内模型"
SEEDS_FILE = OUT / "model-seeds.json"

ELEMENTARY_OVERVIEW = (
    "https://www.pep.com.cn/xw/zt/hd/12/xjcjs/xx/202409/"
    "t20240920_1995566.html"
)
JUNIOR_OVERVIEW = (
    "https://www.pep.com.cn/xw/zt/hd/12/xjcjs/cz/202408/"
    "t20240826_1994351.html"
)
SERIES_OVERVIEW = (
    "https://www.pep.com.cn/xw/zt/hd/12/202409/"
    "t20240902_1994545.html"
)
MOE_STANDARD = (
    "http://www.moe.gov.cn/srcsite/A26/s8001/202204/"
    "t20220420_619921.html"
)
MOE_CATALOG = (
    "http://www.moe.gov.cn/jyb_xxgk/xxgk/neirong/fenlei/kcjc/kcjc_gl/"
)

AUXILIARY_REPETITION = (
    "同一模型内重复作同方向、同用途的线，只增加执行负荷；"
    "不能按新模型重复增加熟悉度难度。"
)


def _semester_from_chapter(chapter: str) -> str:
    if "上册" in chapter or re.search(r"[一二三四五六七八九]上", chapter):
        return "上"
    if "下册" in chapter or re.search(r"[一二三四五六七八九]下", chapter):
        return "下"
    return "跨册"


def _familiarity_by_grade(introduced: int, at_intro: str) -> dict[str, str]:
    if at_intro not in {"introduced", "core"}:
        at_intro = "core"
    result: dict[str, str] = {}
    for grade in range(1, 10):
        if grade < introduced:
            result[str(grade)] = "out_of_scope"
        elif grade == introduced:
            result[str(grade)] = at_intro
        else:
            result[str(grade)] = "reinforced"
    return result


def _source_id(grade: int, semester: str) -> str:
    suffix = {"上": "u", "下": "l", "跨册": "both"}[semester]
    return f"pep-math-g{grade}-{suffix}"


def build_sources() -> dict:
    books = []
    for grade in range(1, 10):
        overview = ELEMENTARY_OVERVIEW if grade <= 6 else JUNIOR_OVERVIEW
        for semester, label in (("上", "上册"), ("下", "下册")):
            books.append(
                {
                    "id": _source_id(grade, semester),
                    "publisher": "人民教育出版社",
                    "official_title": f"义务教育教科书 数学 {grade}年级{label}",
                    "grade": grade,
                    "semester": semester,
                    "school_system": "六三制",
                    "curriculum_standard": "义务教育数学课程标准（2022年版）",
                    "curriculum_standard_url": MOE_STANDARD,
                    "series": "人教版第十二套义务教育教材",
                    "isbn": None,
                    "cip_number": None,
                    "edition_date": None,
                    "printing_date": None,
                    "official_overview_url": overview,
                    "series_overview_url": SERIES_OVERVIEW,
                    "national_catalog_url": MOE_CATALOG,
                    "electronic_textbook_url": (
                        "https://download.pep.com.cn/xsxjc/22xjcsx11x/index.html"
                        if grade == 1 and semester == "上"
                        else None
                    ),
                    "verification_status": "series_verified_bibliography_pending",
                    "verification_note": (
                        "课程依据和系列由教育部、人教社官方页面核验；"
                        "精确ISBN、CIP、版次和页码须以当地实际使用册版权页复核，"
                        "在复核前不得用于正式熟悉度裁决。"
                    ),
                    "rights_status": "summary_only_no_textbook_expression",
                    "accessed_at": "2026-11-09",
                }
            )
    return {
        "version": 1,
        "policy": {
            "canonical_scope": "人教版六三制数学1-9年级",
            "copyright": (
                "只保存独立撰写的模型摘要和来源定位；不保存完整题干、"
                "选项、插图、答案或解析。"
            ),
            "bibliography_gate": (
                "ISBN/CIP/版次和页码尚未由版权页核验。"
                "中、高置信的课内熟悉度写入正式维度 F；低置信不改分。"
            ),
        },
        "books": books,
    }


def _chapter_for_seed(seed: dict, topics: dict[str, dict]) -> str:
    for topic_id in seed["topic_ids"]:
        row = topics.get(topic_id)
        if row and row.get("chapter"):
            return str(row["chapter"])
    grade = int(seed["grade"])
    return f"{grade}年级课内模型（topic 章名待补）"


def _load_seeds() -> list[dict]:
    payload = json.loads(SEEDS_FILE.read_text(encoding="utf-8"))
    models = payload.get("models", [])
    count = int(payload.get("model_count", 0))
    if len(models) != count:
        raise RuntimeError(
            f"{SEEDS_FILE.name}: model_count={count} 与 models 长度 {len(models)} 不一致"
        )
    return models


def build_models(topics: list[dict]) -> dict[int, list[dict]]:
    topic_map = {str(row["id"]): row for row in topics}
    topic_ids = set(topic_map)
    by_grade: dict[int, list[dict]] = {grade: [] for grade in range(1, 10)}
    for seed in _load_seeds():
        grade = int(seed["grade"])
        slug = str(seed["slug"])
        foreign = [tid for tid in seed["topic_ids"] if tid not in topic_ids]
        if foreign:
            raise RuntimeError(f"seed {slug}: 无效 topic_ids {foreign}")
        semester = str(seed.get("semester") or "上")
        if semester not in {"上", "下", "跨册"}:
            raise RuntimeError(f"seed {slug}: 非法 semester {semester}")
        chapter = _chapter_for_seed(seed, topic_map)
        if semester == "跨册":
            semester = _semester_from_chapter(chapter)
        method = str(seed["standard_method"]).strip()
        if not (8 <= len(method) <= 180):
            raise RuntimeError(f"seed {slug}: standard_method 长度 {len(method)} 非法")
        auxiliary = str(seed.get("auxiliary_strategy") or "").strip()
        required = bool(seed.get("auxiliary_required")) and bool(auxiliary)
        record = {
            "id": f"pep-g{grade}-{slug}",
            "name": str(seed["name"]),
            "grade": grade,
            "semester": semester,
            "domain": str(seed.get("domain") or ""),
            "introduced_grade": grade,
            "familiarity_by_grade": _familiarity_by_grade(
                grade,
                str(seed.get("introduced_familiarity") or "core"),
            ),
            "topic_ids": list(seed["topic_ids"]),
            "model_summary": method,
            "trigger_features": {
                "stem_terms": list(seed.get("stem_terms") or [])[:8],
                "solution_terms": list(seed.get("solution_terms") or [])[:8],
                "minimum_term_hits": 1,
            },
            "standard_method": method,
            "common_variants": list(seed.get("common_variants") or [])[:8],
            "uncommon_transforms": list(seed.get("uncommon_transforms") or [])[:8],
            "auxiliary_line": {
                "required": required,
                "strategy": auxiliary,
                "repetition_policy": AUXILIARY_REPETITION if required else "",
            },
            "source_id": _source_id(grade, semester),
            "item_refs": [
                {
                    "chapter": chapter,
                    "section": chapter,
                    "page": None,
                    "item_type": "model_summary",
                    "item_number": None,
                    "verification_status": "chapter_only_page_pending",
                }
            ],
            "summary_author": "AIClass production workflow",
            "summary_version": 1,
            "rights_status": "independent_non_reconstructive_summary",
        }
        if not record["trigger_features"]["stem_terms"]:
            raise RuntimeError(f"seed {slug}: stem_terms 不能为空")
        by_grade[grade].append(record)
    for grade, rows in by_grade.items():
        ids = [row["id"] for row in rows]
        if len(ids) != len(set(ids)):
            raise RuntimeError(f"grade {grade}: 模型 id 重复")
    total = sum(len(rows) for rows in by_grade.values())
    if total != 119:
        raise RuntimeError(f"期望 119 个模型，实际 {total}")
    return by_grade


def main() -> None:
    if not SEEDS_FILE.is_file():
        raise SystemExit(f"缺少种子文件 {SEEDS_FILE}")
    topics = json.loads((KNOWLEDGE / "topics.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sources.json").write_text(
        json.dumps(build_sources(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    by_grade = build_models(topics)
    for grade, models in by_grade.items():
        folder = OUT / f"grade-{grade}"
        folder.mkdir(parents=True, exist_ok=True)
        payload = {
            "grade": grade,
            "publisher": "人民教育出版社",
            "school_system": "六三制",
            "scope": "教材模型摘要；不含教材题目原文",
            "models": models,
        }
        (folder / "models.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    manifest = {
        "version": 1,
        "grades": list(range(1, 10)),
        "source_file": "sources.json",
        "model_files": [f"grade-{g}/models.json" for g in range(1, 10)],
        "seed_file": "model-seeds.json",
        "model_count": sum(len(rows) for rows in by_grade.values()),
        "generated_by": "scripts/build_textbook_models.py",
        "generated_at": "2026-11-09",
        "formal_scoring": False,
    }
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {manifest['model_count']} model summaries")


if __name__ == "__main__":
    main()
