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

# 晋级赛对应该等级的两颗正课星。作业题对应该等级的一颗作业星。
LEVEL_STARS: dict[str, tuple[int, int]] = {
    "B": (2, 3),
    "A": (3, 4),
    "AA": (4, 5),
    "AAA": (5, 6),
    "S": (7, 8),
}
HOMEWORK_STAR: dict[str, int] = {
    "B": 3,
    "A": 4,
    "AA": 5,
    "AAA": 6,
    "S": 8,
}


def assign_levels(items: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    """Rank homework or promotion problems into one level each.

    ``kind`` is ``"homework"`` (B, A, AA, AAA, S) or ``"promotion"``
    (B, A, AA, AAA; no S). Each item needs ``tau``. Equal τ keeps source order.
    A count other than the ladder length still ranks from B upward; extras get
    ``level=None``.
    """
    if kind == "homework":
        ladder = HOMEWORK_LEVELS
    elif kind == "promotion":
        ladder = PROMOTION_LEVELS
    else:
        raise ValueError("kind 只能是 homework 或 promotion")

    scored: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        row = dict(item)
        row["tau"] = float(item["tau"])
        row["source_order"] = index
        scored.append(row)

    order = sorted(range(len(scored)), key=lambda i: (scored[i]["tau"], i))
    for rank, index in enumerate(order):
        level = ladder[rank] if rank < len(ladder) else None
        scored[index]["rank"] = rank
        scored[index]["level"] = level
        if level is not None:
            scored[index]["stars"] = LEVEL_STARS[level]
            if kind == "homework":
                scored[index]["homework_star"] = HOMEWORK_STAR[level]
    return scored
