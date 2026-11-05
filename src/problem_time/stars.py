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


def level_anchor(level: str, kind: str, star_tau: dict[int, float]) -> dict[str, Any]:
    """Anchor τ for one level, taken from the lesson's already assigned stars.

    Homework sits on one star (B→3, A→4, AA→5, AAA→6, S→8).
    Promotion sits on two stars, folded with the same 0.03 rule as an example pair.
    """
    if kind == "homework":
        star = HOMEWORK_STAR[level]
        if star not in star_tau:
            raise KeyError(f"作业锚点缺少 {star} 星")
        return {
            "level": level,
            "anchor_stars": (star,),
            "anchor_tau": float(star_tau[star]),
            "anchor_rule": "star",
        }
    if kind != "promotion":
        raise ValueError("kind 只能是 homework 或 promotion")
    low, high = LEVEL_STARS[level]
    if low not in star_tau or high not in star_tau:
        raise KeyError(f"晋级锚点缺少 {low} 星或 {high} 星")
    folded = pair_tau(float(star_tau[low]), float(star_tau[high]))
    return {
        "level": level,
        "anchor_stars": (low, high),
        "anchor_tau": float(folded["tau_set"]),
        "anchor_rule": folded["pair_rule"],
    }


def _match_anchors(item_tau: list[float], anchor_tau: list[float]) -> dict[int, int]:
    """Map each used item index to an anchor index, minimizing total |τ − anchor|.

    Fewer items than anchors leaves the worse-fitting anchors empty.
    More items than anchors leaves the worse-fitting items unassigned.
    Equal cost keeps the smaller τ on the earlier anchor.
    """
    from itertools import combinations, permutations

    item_count = len(item_tau)
    anchor_count = len(anchor_tau)
    if item_count == 0 or anchor_count == 0:
        return {}

    order = sorted(range(item_count), key=lambda index: (item_tau[index], index))
    ordered_tau = [item_tau[index] for index in order]
    best_key: tuple[float, tuple[int, ...]] | None = None
    best_map: dict[int, int] = {}
    seat_count = min(item_count, anchor_count)

    if item_count <= anchor_count:
        choices = combinations(range(anchor_count), item_count)
        for chosen in choices:
            for perm in permutations(chosen):
                cost = sum(abs(ordered_tau[i] - anchor_tau[perm[i]]) for i in range(item_count))
                key = (round(cost, 12), perm)
                if best_key is None or key < best_key:
                    best_key = key
                    best_map = {order[i]: perm[i] for i in range(item_count)}
        return best_map

    for chosen_items in combinations(range(item_count), seat_count):
        for perm in permutations(chosen_items):
            cost = sum(abs(ordered_tau[perm[j]] - anchor_tau[j]) for j in range(anchor_count))
            key = (round(cost, 12), perm)
            if best_key is None or key < best_key:
                best_key = key
                best_map = {order[perm[j]]: j for j in range(anchor_count)}
    return best_map


def assign_levels(
    items: list[dict[str, Any]],
    kind: str,
    star_tau: dict[int, float] | None = None,
) -> list[dict[str, Any]]:
    """Give each homework or promotion problem one level.

    ``kind`` is ``"homework"`` (B, A, AA, AAA, S) or ``"promotion"``
    (B, A, AA, AAA; no S). Each item needs ``tau``.

    With ``star_tau`` from the lesson's 2–8 pairs, each level has an anchor:
    homework uses one star, promotion uses two stars folded by ``pair_tau``.
    Problems are matched to anchors by smallest total absolute gap. A level
    with no nearby problem stays empty, and a problem that fits none stays
    unassigned. Gap at or above 0.03 is a loose fit.

    Without ``star_tau``, levels are filled from B upward by τ order.
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

    if star_tau is None:
        order = sorted(range(len(scored)), key=lambda index: (scored[index]["tau"], index))
        for rank, index in enumerate(order):
            level = ladder[rank] if rank < len(ladder) else None
            _write_level(scored[index], kind, level, rank)
        return scored

    anchors = [level_anchor(level, kind, star_tau) for level in ladder]
    matched = _match_anchors(
        [row["tau"] for row in scored],
        [float(anchor["anchor_tau"]) for anchor in anchors],
    )
    for index, row in enumerate(scored):
        anchor_index = matched.get(index)
        if anchor_index is None:
            _write_level(row, kind, None, None)
            continue
        anchor = anchors[anchor_index]
        gap = abs(row["tau"] - float(anchor["anchor_tau"]))
        _write_level(row, kind, str(anchor["level"]), anchor_index)
        row["anchor_tau"] = anchor["anchor_tau"]
        row["anchor_rule"] = anchor["anchor_rule"]
        row["anchor_gap"] = gap
        row["fit"] = "tight" if gap < STAR_GAP else "loose"
    return scored


def _write_level(row: dict[str, Any], kind: str, level: str | None, rank: int | None) -> None:
    row["rank"] = rank
    row["level"] = level
    if level is None:
        return
    row["stars"] = LEVEL_STARS[level]
    if kind == "homework":
        row["homework_star"] = HOMEWORK_STAR[level]
