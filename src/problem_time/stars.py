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
