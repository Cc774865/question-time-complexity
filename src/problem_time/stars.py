"""Assign 2–8 stars after τ is already computed.

Stars are not an input to τ. A lesson's example/practice pairs are ranked
by a single set τ and then labeled 2 through 8 from small to large.
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
    """Rank pair τ from small to large and label them 2, 3, … in that order.

    ``pairs`` keeps source order. Each item needs ``tau_example`` and
    ``tau_practice``. Equal τ keeps the earlier pair ahead of the later one.
    Seven pairs land on stars 2 through 8. A different count still ranks from
    2 upward; stars past 8 are reported as-is.
    """
    scored: list[dict[str, Any]] = []
    for index, pair in enumerate(pairs):
        row = dict(pair)
        row.update(pair_tau(float(pair["tau_example"]), float(pair["tau_practice"])))
        row["source_order"] = index
        scored.append(row)

    order = sorted(range(len(scored)), key=lambda i: (scored[i]["tau_set"], i))
    for rank, index in enumerate(order):
        star = STAR_LADDER[0] + rank
        scored[index]["rank"] = rank
        scored[index]["star"] = star
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
        if kind == "promotion" and level == "S":
            row["level"] = None
            row["similar_star"] = star
            row["stars"] = LEVEL_STARS["S"]
            row["rejected"] = "晋级赛没有 S 级"
            scored.append(row)
            continue
        row["similar_star"] = star
        row["level"] = level
        row["stars"] = LEVEL_STARS[level]
        scored.append(row)
    return scored


def _require_assigned_stars(assigned_stars: list[dict[str, Any]] | None) -> None:
    if not assigned_stars:
        raise LevelsBeforeStarsError("2–8 星尚未分配，禁止计算晋级赛和作业题的等级")
    stars = [row.get("star") for row in assigned_stars]
    if any(star is None for star in stars):
        raise LevelsBeforeStarsError("2–8 星尚未分配完成，禁止计算晋级赛和作业题的等级")
