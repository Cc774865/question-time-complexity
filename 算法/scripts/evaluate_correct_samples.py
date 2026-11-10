"""Evaluate formal scoring against the local correct-star samples.

This is an offline audit only.  It never copies sample stems into a result
file, never feeds star labels into ``score_calibrated_problem``, and never
changes weights automatically.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import replace
from pathlib import Path
from typing import Iterable

import joblib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from problem_time.calibration import score_calibrated_problem
from problem_time.solution_counts import solution_counts
from problem_time.structure_counts import structure_counts
from problem_time.textbook_models import shadow_familiarity


SAMPLES = ROOT.parent / "正确样本"


def main() -> int:
    summary: dict[str, dict[str, float | int]] = {}
    all_rows: list[tuple[float, float]] = []
    for path in sorted(SAMPLES.glob("*.joblib")):
        payload = joblib.load(path)
        grade_name = str(payload["grade"])
        if grade_name == "中考冲刺":
            grade = (7, 8, 9)
        elif grade_name and grade_name[0].isdigit():
            grade = (int(grade_name[0]),)
        else:
            grade = None
        rows: list[tuple[float, float]] = []
        matched = 0
        for index, item in enumerate(payload["items"]):
            stem = str(item["processed_text"])
            solution = str(item["model_response"])
            counts = solution_counts(solution, stem) if solution.strip() else structure_counts(stem)
            if grade is not None:
                familiarity = shadow_familiarity(stem, solution, grade, counts)
                if familiarity["affectsFormalTau"]:
                    counts = replace(counts, familiarity=float(familiarity["formalF"]))
                    matched += 1
            score = score_calibrated_problem(f"{path.stem}-{index}", stem, counts)
            rows.append((float(item["difficulty"]), float(score["composite_D"])))
        all_rows.extend(rows)
        summary[grade_name] = {
            "count": len(rows),
            "familiarityMatched": matched,
            "pearsonDifficultyD": round(_pearson(rows), 4),
        }
    print(
        json.dumps(
            {
                "sampleCount": len(all_rows),
                "overallPearsonDifficultyD": round(_pearson(all_rows), 4),
                "byGrade": summary,
                "note": "离线评估；不会自动改权重或读取样本题面到输出。",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _pearson(rows: Iterable[tuple[float, float]]) -> float:
    values = list(rows)
    if len(values) < 2:
        return 0.0
    labels = [label for label, _ in values]
    scores = [score for _, score in values]
    label_mean = sum(labels) / len(labels)
    score_mean = sum(scores) / len(scores)
    top = sum((label - label_mean) * (score - score_mean) for label, score in values)
    label_sum = sum((label - label_mean) ** 2 for label in labels)
    score_sum = sum((score - score_mean) ** 2 for score in scores)
    return top / math.sqrt(label_sum * score_sum) if label_sum and score_sum else 0.0


if __name__ == "__main__":
    raise SystemExit(main())
