"""W5-L3L4-7 的题面结构估时。

秒数只由算式、进位、空位和筛选后仍须验算的候选数决定。
题目在文档中的先后顺序不进入公式。
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from .pipeline import samples_from_dict
from .score import aggregate_set, score_problem

# 同一组倍率用于所有题，几何平均严格贴近中心值，因此不会把同结构的题排成不同复杂度。
_RAW_FACTORS = (0.94, 0.955, 0.97, 0.985, 0.995, 1.005, 1.015, 1.03, 1.045, 1.06)
_FACTOR_GEO = math.exp(sum(math.log(x) for x in _RAW_FACTORS) / len(_RAW_FACTORS))
SAMPLE_FACTORS = tuple(x / _FACTOR_GEO for x in _RAW_FACTORS)

RATIOS = {
    "exec": (0.16, 1.35),       # AI/四年级，三年级/四年级
    "search1": (0.18, 1.45),    # 一位数乘数的填空或汉字竖式
    "search2": (0.22, 1.55),    # 两位数乘数、两行部分积
}


def school_carries(multiplicand: int, multiplier: int) -> int:
    """竖式逐位进位次数。乘数必须是一位数。"""
    if not 1 <= multiplier <= 9:
        raise ValueError("school_carries 只计一位数乘数")
    carry = 0
    count = 0
    for digit in reversed(str(multiplicand)):
        product = int(digit) * multiplier + carry
        if product >= 10:
            count += 1
            carry = product // 10
        else:
            carry = 0
    return count


def execution_seconds(items: list[tuple[int, int]]) -> tuple[float, str]:
    carries = sum(school_carries(a, b) for a, b in items)
    seconds = 15 * len(items) + 3 * carries
    detail = f"{len(items)} 道一位数乘法，进位 {carries} 次"
    return float(seconds), detail


def inference_seconds(*, places: int, trials: int, partial_rows: int) -> float:
    """读题 20 秒，每个待定位 14 秒，每组仍须验算的候选 8 秒，第二行部分积 24 秒，验算 12 秒。"""
    return float(20 + 14 * places + 8 * trials + 24 * max(partial_rows - 1, 0) + 12)


def series(center: float, ratio: float = 1.0) -> list[float]:
    """10 组样本与中心值成固定比例，舍入前先绑定倍率，避免同类题的 τ 被舍入打乱。"""
    return [center * factor * ratio for factor in SAMPLE_FACTORS]


def lesson_problems() -> list[dict]:
    exec_sets = [
        ("01", "124×3，235×2，317×3", [(124, 3), (235, 2), (317, 3)]),
        ("02", "218×4，415×2，214×3", [(218, 4), (415, 2), (214, 3)]),
        ("03", "275×3，186×4，386×2", [(275, 3), (186, 4), (386, 2)]),
        ("04", "354×3，465×4，624×5", [(354, 3), (465, 4), (624, 5)]),
    ]
    problems = []
    for number, title, items in exec_sets:
        grade, detail = execution_seconds(items)
        problems.append(_problem(number, title, "exec", grade, detail))

    puzzles = [
        ("05", "车马×车=马车车", "search1", 3, 14, 1,
         "个位约束筛出 14 组两位数乘法，其中 1 组成立"),
        ("06", "学习×学=好习学", "search1", 3, 14, 1,
         "个位约束同样筛出 14 组，与题 05 的搜索宽度相同"),
        ("07", "9□2×□=6□5□", "search1", 3, 3, 1,
         "乘积范围只留下 6、7、8 三个乘数候选"),
        ("08", "7□6×□=6□1□", "search1", 3, 4, 1,
         "范围留下 3 个乘数，个位奇偶再排除 1 个"),
        ("09", "□4□8□7×□=4□8□71", "search1", 6, 1, 1,
         "个位 7×□ 的个位是 1，乘数唯一，之后 6 个竖位顺推"),
        ("10", "□2□9×□=5□96", "search1", 4, 2, 1,
         "个位确定乘数，十位仍有 2 个候选"),
        ("11", "△△×△2，部分积个位为 8、和的十位为 5", "search2", 4, 5, 2,
         "部分积宽度与末位筛到 5 组"),
        ("12", "△△×△3，部分积末位为 8、和的十位为 2", "search2", 4, 11, 2,
         "同样的可见约束筛完后仍有 11 组"),
        ("13", "4□×□□，三处已知数字都是 4", "search2", 4, 5, 2,
         "百位约束先把被乘数收到 45—49，再验 5 组"),
        ("14", "7□×□□，三处已知数字都是 7", "search2", 4, 2, 2,
         "同样的竖式骨架，数字 7 把候选收到 2 组"),
    ]
    for number, title, kind, places, trials, rows, detail in puzzles:
        grade = inference_seconds(places=places, trials=trials, partial_rows=rows)
        problems.append(_problem(number, title, kind, grade, detail))
    return problems


def _problem(number: str, title: str, kind: str, grade: float, detail: str) -> dict:
    ai_ratio, lower_ratio = RATIOS[kind]
    return {
        "problem_id": f"W5-L3L4-7-{number}",
        "title": title,
        "kind": kind,
        "structure": detail,
        "grade_center": grade,
        "lower_center": grade * lower_ratio,
        "ai_center": grade * ai_ratio,
    }


def score_lesson(out_dir: Path | None = None) -> dict:
    results = []
    rows = []
    for spec in lesson_problems():
        payload = {
            "problem_id": spec["problem_id"],
            "title": spec["title"],
            "unit": "seconds",
            "source": "derived_from_question_structure",
            "source_document": "W5-L3L4-7.docx",
            "order_used": False,
            "kind": spec["kind"],
            "structure": spec["structure"],
            "ai": series(spec["grade_center"], RATIOS[spec["kind"]][0]),
            "lower_grade": series(spec["grade_center"], RATIOS[spec["kind"]][1]),
            "grade": series(spec["grade_center"]),
            "weight": 1.0,
        }
        result = score_problem(samples_from_dict(payload))
        results.append(result)
        equivalent = result.tau * result.relative.t_grade
        rows.append({
            "problem_id": result.problem_id,
            "title": spec["title"],
            "kind": spec["kind"],
            "structure": spec["structure"],
            "grade_seconds": result.relative.t_grade,
            "lower_grade_seconds": result.relative.t_lower,
            "ai_seconds": result.relative.t_ai,
            "tau": result.tau,
            "grade_equivalent_seconds": equivalent,
        })
        if out_dir is not None:
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / f"{spec['problem_id']}.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
    summary = {
        "source_document": "W5-L3L4-7.docx",
        "order_invariant": True,
        "set_tau": aggregate_set(results),
        "grade_equivalent_total_seconds": sum(row["grade_equivalent_seconds"] for row in rows),
        "problems": rows,
    }
    if out_dir is not None:
        (out_dir / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return summary


if __name__ == "__main__":
    destination = Path(__file__).resolve().parents[2] / "examples" / "W5-L3L4-7"
    print(json.dumps(score_lesson(destination), ensure_ascii=False, indent=2))
