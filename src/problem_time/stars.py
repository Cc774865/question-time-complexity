"""Assign 2–8 stars after τ is already computed.

Stars are not an input to τ. The pair holding the lowest single-problem τ
is 2 stars. The other pairs are labeled from 3 upward by set τ.
"""

from __future__ import annotations

from typing import Any

# Adjacent star centers on the seven calibration papers sit about 0.03 apart.
STAR_GAP = 0.03
STAR_LADDER = (2, 3, 4, 5, 6, 7, 8)


def pair_tau(tau_example: float, tau_practice: float) -> dict[str, float | str]:
    """One τ for an example/practice pair.

    Gap below 0.03: arithmetic mean. Gap at or above 0.03: the higher τ.
    """
    gap = abs(tau_example - tau_practice)
    if gap < STAR_GAP:
        value = (tau_example + tau_practice) / 2.0
        rule = "mean"
    else:
        value = max(tau_example, tau_practice)
        rule = "higher"
    return {
        "tau_example": tau_example,
        "tau_practice": tau_practice,
        "gap": gap,
        "tau_set": value,
        "pair_rule": rule,
    }


def assign_stars(pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Label pairs 2, 3, … after τ exists.

    The pair that contains the lowest single-problem τ is 2 stars, whether
    that problem is the example or the practice. A tie keeps the earlier pair
    in the file. Every other pair is ranked by its set τ, smallest first.
    Equal set τ keeps file order. Seven pairs land on stars 2 through 8.
    A different count still starts at 2; stars past 8 are reported as-is.
    """
    scored: list[dict[str, Any]] = []
    for index, pair in enumerate(pairs):
        row = dict(pair)
        row.update(pair_tau(float(pair["tau_example"]), float(pair["tau_practice"])))
        row["source_order"] = index
        scored.append(row)
    if not scored:
        return scored

    pinned = min(
        range(len(scored)),
        key=lambda i: (min(scored[i]["tau_example"], scored[i]["tau_practice"]), i),
    )
    rest = sorted(
        (i for i in range(len(scored)) if i != pinned),
        key=lambda i: (scored[i]["tau_set"], i),
    )
    for rank, index in enumerate((pinned, *rest)):
        scored[index]["rank"] = rank
        scored[index]["star"] = STAR_LADDER[0] + rank
        scored[index]["star_rule"] = "lowest" if index == pinned else "set"
    return scored


HOMEWORK_LEVELS = ("B", "A", "AA", "AAA", "S")
PROMOTION_LEVELS = ("B", "A", "AA", "AAA")

# 班的内容只由已经分配完的 2–8 星决定。这张表写死，不从 τ 推。
LEVEL_STARS: dict[str, tuple[int, int]] = {
    "B": (2, 3),
    "A": (3, 4),
    "AA": (4, 5),
    "AAA": (5, 6),
    "S": (7, 8),
}

# 与某颗星的课件内容最像时，归到把这颗星当作上沿的那个班。
# 共用的下沿星因此归到前一个班。2 星没有更早的班。7 星不是任何班的上沿，只属于 S。
SIMILAR_STAR_LEVEL: dict[int, str] = {
    2: "B",
    3: "B",
    4: "A",
    5: "AA",
    6: "AAA",
    7: "S",
    8: "S",
}


class LevelsBeforeStarsError(RuntimeError):
    """晋级赛和作业题的等级在 2–8 星分配完成之前禁止计算。"""


def assign_levels(
    items: list[dict[str, Any]],
    kind: str,
    assigned_stars: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Place homework or promotion problems by content similarity.

    ``assigned_stars`` is the finished return value of ``assign_stars``.
    Calling this before that list exists raises ``LevelsBeforeStarsError``.
    Each item must already carry ``similar_star``: the star whose example and
    practice it resembles. τ is not read and cannot choose the level.
    A class keeps one item. Two or more items that land on the same class are
    all removed and marked ``review`` = ``人工审核``.
    """
    if kind not in ("homework", "promotion"):
        raise ValueError("kind 只能是 homework 或 promotion")
    _require_assigned_stars(assigned_stars)

    scored: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        row = dict(item)
        row["source_order"] = index
        if "similar_star" not in row:
            raise LevelsBeforeStarsError("必须先与各星课件内容比对相似度，得到 similar_star 之后才能判定等级")
        star = int(row["similar_star"])
        if star not in SIMILAR_STAR_LEVEL:
            raise ValueError(f"similar_star 只能是 2–8，当前={star}")
        level = SIMILAR_STAR_LEVEL[star]
        row["similar_star"] = star
        row["contested_level"] = level
        row["stars"] = LEVEL_STARS[level]
        scored.append(row)

    grouped: dict[str, list[int]] = {}
    for index, row in enumerate(scored):
        grouped.setdefault(row["contested_level"], []).append(index)

    for level, indexes in grouped.items():
        if len(indexes) == 1:
            row = scored[indexes[0]]
            if kind == "promotion" and level == "S":
                row["level"] = None
                row["rejected"] = "晋级赛没有 S 级"
            else:
                row["level"] = level
            continue
        stars = sorted({scored[index]["similar_star"] for index in indexes})
        shown = "、".join(f"{star} 星" for star in stars)
        reason = f"{level} 班只能留一个内容（最像 {shown}），全部交给人工审核"
        for index in indexes:
            row = scored[index]
            row["level"] = None
            row["review"] = "人工审核"
            row["review_reason"] = reason
            if kind == "promotion" and level == "S":
                row["rejected"] = "晋级赛没有 S 级"
    return scored


def _require_assigned_stars(assigned_stars: list[dict[str, Any]] | None) -> None:
    if not assigned_stars:
        raise LevelsBeforeStarsError("2–8 星尚未分配，禁止计算晋级赛和作业题的等级")
    stars = [row.get("star") for row in assigned_stars]
    if any(star is None for star in stars):
        raise LevelsBeforeStarsError("2–8 星尚未分配完成，禁止计算晋级赛和作业题的等级")
