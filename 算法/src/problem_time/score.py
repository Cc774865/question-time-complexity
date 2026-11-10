from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .aggregate import geometric_mean, median_time, summarize
from .clean import CleanResult, adopt_primary, relative_gap
from .normalize import RelativeTimes
from .weights import ThreeFactorWeights, make_weights


RECOMMENDED_N = 10
DEFAULT_GAP_THRESHOLD = 0.25


@dataclass(frozen=True)
class ProblemSamples:
    """
    单题三类原始耗时样本（同一单位：秒或毫秒均可，只要同类一致）。

    建议每类 n ≈ 10。
    """

    ai: list[float]
    lower_grade: list[float]  # g-1，如下一年级 / 三年级
    grade: list[float]  # g，本题年级 / 四年级
    problem_id: str = ""
    weight: float = 1.0  # 多题汇总时的题级权重 v_i


@dataclass(frozen=True)
class FactorReport:
    name: str
    primary_geo: float
    median: float
    n_raw: int
    n_used: int
    provisional: bool
    clean: CleanResult


@dataclass(frozen=True)
class ProblemTimeResult:
    """单题合成指标 τ 及诊断。"""

    problem_id: str
    tau: float
    relative: RelativeTimes
    weights: ThreeFactorWeights
    reports: tuple[FactorReport, FactorReport, FactorReport]
    provisional: bool
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "problem_id": self.problem_id,
            "tau": self.tau,
            "provisional": self.provisional,
            "notes": list(self.notes),
            "weights": asdict(self.weights),
            "relative": asdict(self.relative),
            "reports": [
                {
                    "name": r.name,
                    "primary_geo": r.primary_geo,
                    "median": r.median,
                    "n_raw": r.n_raw,
                    "n_used": r.n_used,
                    "provisional": r.provisional,
                    "clean": {
                        "triggered": r.clean.triggered,
                        "relative_gap": r.clean.relative_gap,
                        "removed": list(r.clean.removed),
                        "values_used": list(r.clean.values),
                        "note": r.clean.note,
                    },
                }
                for r in self.reports
            ],
        }


def _factor_report(
    name: str,
    samples: list[float],
    *,
    gap_threshold: float,
) -> FactorReport:
    if not samples:
        empty = CleanResult(
            values=(),
            removed=(),
            triggered=False,
            relative_gap=0.0,
            note="无样本",
        )
        return FactorReport(
            name=name,
            primary_geo=0.0,
            median=0.0,
            n_raw=0,
            n_used=0,
            provisional=True,
            clean=empty,
        )

    primary, cleaned = adopt_primary(samples, gap_threshold=gap_threshold)
    med = median_time(samples)
    return FactorReport(
        name=name,
        primary_geo=primary,
        median=med,
        n_raw=len(samples),
        n_used=len(cleaned.values),
        provisional=len(samples) < 8,
        clean=cleaned,
    )


def score_problem(
    samples: ProblemSamples,
    *,
    w_ai: float = 1.0 / 3.0,
    gap_threshold: float = DEFAULT_GAP_THRESHOLD,
) -> ProblemTimeResult:
    """
    单题：各类几何平均（中位数对照，偏差大则 trim）→ 相对时间 → 三因子加权 τ。

      τ = w_AI · T_AI + w_{g-1} · T_{g-1} + w_g · 1
    """
    weights = make_weights(w_ai=w_ai)
    reports = (
        _factor_report("ai", list(samples.ai), gap_threshold=gap_threshold),
        _factor_report(
            "lower_grade", list(samples.lower_grade), gap_threshold=gap_threshold
        ),
        _factor_report("grade", list(samples.grade), gap_threshold=gap_threshold),
    )

    notes: list[str] = []
    for r in reports:
        if r.n_raw == 0:
            raise ValueError(f"因子 {r.name} 缺少样本")
        if r.provisional:
            notes.append(f"{r.name}: n={r.n_raw}<8，τ 标为试算")
        if r.clean.triggered:
            notes.append(f"{r.name}: {r.clean.note}")

    relative = RelativeTimes.from_aggregated(
        t_ai=reports[0].primary_geo,
        t_lower=reports[1].primary_geo,
        t_grade=reports[2].primary_geo,
    )
    tau = (
        weights.w_ai * relative.T_ai
        + weights.w_lower * relative.T_lower
        + weights.w_grade * relative.T_grade
    )
    provisional = any(r.provisional for r in reports)

    return ProblemTimeResult(
        problem_id=samples.problem_id,
        tau=tau,
        relative=relative,
        weights=weights,
        reports=reports,
        provisional=provisional,
        notes=tuple(notes),
    )


def aggregate_set(
    results: list[ProblemTimeResult],
    weights: list[float] | None = None,
) -> float:
    """多题汇总：τ = Σ v_i τ_i / Σ v_i。"""
    if not results:
        raise ValueError("至少需要一道题的结果")
    if weights is None:
        weights = [1.0] * len(results)
    if len(weights) != len(results):
        raise ValueError("题级权重数量须与题目数一致")
    if any(v < 0 for v in weights):
        raise ValueError("题级权重不可为负")
    denom = sum(weights)
    if denom <= 0:
        raise ValueError("题级权重之和必须 > 0")
    return sum(v * r.tau for v, r in zip(weights, results)) / denom


def diagnose_samples(samples: list[float]) -> dict[str, Any]:
    """单序列诊断：几何平均、中位数、相对偏差。"""
    s = summarize(samples)
    gap = relative_gap(s["geo"], s["median"]) if samples else 0.0
    return {**s, "relative_gap_geo_vs_median": gap}
