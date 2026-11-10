"""Match a question to grade-specific textbook models and set formal F.

A medium or high confidence hit writes the familiarity dimension used for τ.
Low confidence, a missing library, and 高考冲刺 keep F at 0.
中考冲刺 uses grades 7, 8, and 9 and keeps the least familiar status.
Structural P, R, C and E are not rewritten.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from problem_time.calibration import FAMILIARITY_OFFSET, FourDimCounts
from problem_time.project_paths import project_root

LIBRARY = project_root() / "知识库" / "课内模型"

_FAMILIARITY_ORDER = {
    "reinforced": 0,
    "core": 1,
    "introduced": 2,
    "uncommon_transform": 3,
    "out_of_scope": 4,
}
# F 与 P 同一把尺子：上限 6、权重 0.18。课内熟相对不常见变形相差 3，
# 综合难度 D 相差 9，τ 相差约 0.0307，也就是相邻两档星级中心的距离。
_TRANSFORM = re.compile(
    r"动点|分类讨论|参数|逆向|反求|分段|多层|二次全等|多次作图|"
    r"组合模型|位置变化|不唯一|隐藏条件"
)


@lru_cache(maxsize=1)
def load_textbook_models() -> tuple[dict[str, Any], ...]:
    """Load all grade files once. Missing shadow data is not a scoring error."""
    rows: list[dict[str, Any]] = []
    for grade in range(1, 10):
        path = LIBRARY / f"grade-{grade}" / "models.json"
        if not path.is_file():
            return ()
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows.extend(payload.get("models", []))
    return tuple(rows)


def familiarity_for_grades(model: dict[str, Any], grades: Iterable[int]) -> str:
    """Return the least familiar status among all audience grades."""
    statuses = [
        str(model.get("familiarity_by_grade", {}).get(str(grade), "out_of_scope"))
        for grade in grades
        if 1 <= grade <= 9
    ]
    if not statuses:
        return "unavailable"
    return max(statuses, key=lambda status: _FAMILIARITY_ORDER.get(status, 99))


def shadow_familiarity(
    stem: str,
    solution: str,
    grades: tuple[int, ...],
    counts: FourDimCounts,
    *,
    limit: int = 3,
) -> dict[str, Any]:
    """Return the textbook match and the F that formal scoring should use."""
    audience = tuple(sorted({grade for grade in grades if 1 <= grade <= 9}))
    base = float(counts.prereq)
    if not audience:
        return _unchanged("not_applicable", "使用年级不是1–9年级的明确年级", audience, base)
    models = load_textbook_models()
    if not models:
        return _unchanged("unavailable", "课内模型库缺失或不完整", audience, base)

    text = _clean(stem)
    solution_text = _clean(solution)
    candidates: list[dict[str, Any]] = []
    for model in models:
        features = model.get("trigger_features", {})
        stem_terms = [str(term) for term in features.get("stem_terms", [])]
        solution_terms = [str(term) for term in features.get("solution_terms", [])]
        stem_hits = [term for term in stem_terms if term and term in text]
        solution_hits = [term for term in solution_terms if term and term in solution_text]
        minimum = int(features.get("minimum_term_hits", 1))
        if len(stem_hits) + len(solution_hits) < minimum or not stem_hits:
            continue
        familiarity = familiarity_for_grades(model, audience)
        transformed = _is_uncommon_transform(text, solution_text, model)
        if transformed and familiarity not in {"out_of_scope", "unavailable"}:
            familiarity = "uncommon_transform"
        confidence = _confidence(stem_hits, solution_hits)
        score = 2 * len(stem_hits) + len(solution_hits)
        suggested = FAMILIARITY_OFFSET.get(familiarity, 0.0)
        candidates.append(
            {
                "modelId": model["id"],
                "modelName": model["name"],
                "introducedGrade": model["introduced_grade"],
                "familiarity": familiarity,
                "confidence": confidence,
                "matchedStemTerms": stem_hits,
                "matchedSolutionTerms": solution_hits,
                "suggestedF": round(suggested, 2) if confidence != "low" else None,
                "reason": _reason(model, familiarity, transformed),
                "sourceId": model["source_id"],
                "sourceLocator": model.get("item_refs", []),
                "_score": score,
            }
        )
    candidates.sort(
        key=lambda row: (
            -int(row["_score"]),
            _FAMILIARITY_ORDER.get(str(row["familiarity"]), 99),
            str(row["modelId"]),
        )
    )
    shown = candidates[: max(limit, 0)]
    for row in shown:
        row.pop("_score", None)
    best = next((row for row in shown if row["suggestedF"] is not None), None)
    if best is None:
        return {
            "status": "candidates_need_review" if shown else "no_match",
            "reason": (
                "只有低置信候选，必须人工复核，不能改正式 F"
                if shown
                else "没有足够确定的课内模型候选"
            ),
            "grades": list(audience),
            "structuralP": base,
            "formalF": 0.0,
            "suggestedF": None,
            "affectsFormalTau": False,
            "candidates": shown,
        }
    formal = float(best["suggestedF"])
    return {
        "status": "matched",
        "reason": "课内熟悉度已计入正式维度 F",
        "grades": list(audience),
        "structuralP": base,
        "formalF": formal,
        "suggestedF": formal,
        "affectsFormalTau": True,
        "candidates": shown,
    }


def _unchanged(status: str, reason: str, grades: tuple[int, ...], base: float) -> dict[str, Any]:
    return {
        "status": status,
        "reason": reason,
        "grades": list(grades),
        "structuralP": base,
        "formalF": 0.0,
        "suggestedF": None,
        "affectsFormalTau": False,
        "candidates": [],
    }


def _clean(text: str) -> str:
    return re.sub(r"\s+", "", text.replace("\u200b", ""))


def _confidence(stem_hits: list[str], solution_hits: list[str]) -> str:
    if len(stem_hits) >= 2 or (stem_hits and len(solution_hits) >= 2):
        return "high"
    if stem_hits and solution_hits:
        return "medium"
    return "low"


def _is_uncommon_transform(stem: str, solution: str, model: dict[str, Any]) -> bool:
    text = f"{stem}\n{solution}"
    if _TRANSFORM.search(text):
        return True
    auxiliary = model.get("auxiliary_line", {})
    if auxiliary.get("required") and re.search(r"动点|分类|多层|二次", text):
        return True
    return False


def _reason(model: dict[str, Any], familiarity: str, transformed: bool) -> str:
    if transformed:
        return (
            f"知识点与“{model['name']}”相近，但题面含不常见重组、动态或分类特征；"
            "不能按标准熟模型降难度"
        )
    if familiarity == "reinforced":
        return f"“{model['name']}”在更早年级已引入，本年级属于复现模型"
    if familiarity == "introduced":
        return f"“{model['name']}”在本年级首次系统出现"
    if familiarity == "out_of_scope":
        return f"至少一个适用年级尚未进入“{model['name']}”的课内范围"
    return f"候选模型“{model['name']}”"
