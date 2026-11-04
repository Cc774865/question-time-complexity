from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CleanResult:
    """清洗前后的样本与是否认定「坏样本」。"""

    values: tuple[float, ...]
    removed: tuple[float, ...]
    triggered: bool
    relative_gap: float
    note: str


def relative_gap(geo: float, med: float) -> float:
    """|geo - median| / median；median 近 0 时用 geo 作分母兜底。"""
    base = med if med > 1e-12 else (geo if geo > 1e-12 else 1.0)
    return abs(geo - med) / base


def trim_minmax(values: list[float]) -> tuple[list[float], list[float]]:
    """去掉一个最低、一个最高（n>=3）；不足则原样返回。"""
    if len(values) < 3:
        return list(values), []
    ordered = sorted(values)
    removed = [ordered[0], ordered[-1]]
    kept = ordered[1:-1]
    return kept, removed


def clean_if_geo_median_diverge(
    values: list[float],
    *,
    gap_threshold: float = 0.25,
) -> CleanResult:
    """
    几何平均与中位数相对偏差 >= gap_threshold（默认 25%）→ 视为可能有坏样本。

    清洗策略：去掉最低与最高各 1 个后再算（轻量 trimmed），供后续改用清洗后的几何平均。
    """
    from .aggregate import geometric_mean, median_time

    if len(values) < 2:
        return CleanResult(
            values=tuple(values),
            removed=(),
            triggered=False,
            relative_gap=0.0,
            note="样本过少，跳过对照清洗",
        )

    geo = geometric_mean(values)
    med = median_time(values)
    gap = relative_gap(geo, med)

    if gap < gap_threshold:
        return CleanResult(
            values=tuple(values),
            removed=(),
            triggered=False,
            relative_gap=gap,
            note="主对照接近，直接采用几何平均",
        )

    kept, removed = trim_minmax(values)
    if len(kept) < 1:
        return CleanResult(
            values=tuple(values),
            removed=(),
            triggered=True,
            relative_gap=gap,
            note="偏差大但无法再修剪，仍用原样本几何平均并告警",
        )

    return CleanResult(
        values=tuple(kept),
        removed=tuple(removed),
        triggered=True,
        relative_gap=gap,
        note=(
            f"主对照相对偏差 {gap:.1%} ≥ {gap_threshold:.0%}："
            f"已去掉最低/最高各 1 个（{removed}），改用清洗后几何平均"
        ),
    )


def adopt_primary(values: list[float], *, gap_threshold: float = 0.25) -> tuple[float, CleanResult]:
    """
    返回 (采用的主指标值, 清洗细节)。

    流程：先看原序列 geo vs median；若偏差大则 trim 后再取 geo；
    若 trim 后仍偏差很大，仍返回 trim 后的 geo，并在 note 里保留告警。
    """
    from .aggregate import geometric_mean, median_time

    cleaned = clean_if_geo_median_diverge(values, gap_threshold=gap_threshold)
    primary = geometric_mean(list(cleaned.values))

    if cleaned.triggered and len(cleaned.values) >= 2:
        gap2 = relative_gap(primary, median_time(list(cleaned.values)))
        if gap2 >= gap_threshold:
            note = cleaned.note + f"；清洗后偏差仍为 {gap2:.1%}，请人工复核样本"
            cleaned = CleanResult(
                values=cleaned.values,
                removed=cleaned.removed,
                triggered=True,
                relative_gap=cleaned.relative_gap,
                note=note,
            )

    return primary, cleaned
