"""Four-dimension structural calibration for time complexity τ.

Combines the four objective dimensions from k12-difficulty-calibration
(`prereq`, `reasoning`, `compute`, `error`) with the three-factor
relative-time model (`AI`, `lower_grade`, `grade`).

All counts come strictly from the question stem and the required mathematical
structure of the problem, never from prose length or document order.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .lesson_w5 import SAMPLE_FACTORS, series
from .pipeline import samples_from_dict
from .score import ProblemTimeResult, aggregate_set, score_problem

# Exact weights from k12-difficulty-calibration (WEIGHTS_NO_HIST)
DIMENSION_WEIGHTS: dict[str, float] = {
    "prereq": 0.18,
    "reasoning": 0.31,
    "compute": 0.25,
    "error": 0.26,
}

# Normalization caps so 8-star problems across primary and middle school do not saturate early
CAPS: dict[str, float] = {
    "prereq": 6.0,     # knowledge points + cognitive depth (1..6)
    "reasoning": 12.0, # irreducible structural inference / transformation steps (1..12)
    "compute": 10.0,   # arithmetic / algebraic operation load + carries/regrouping (1..10)
    "error": 6.0,      # structural trap / constraint / branch / hidden-unit count (0..6)
}

# Base ratios at D = 0 and linear slopes per unit of D (0..100)
R_AI_BASE = 0.13
R_AI_SLOPE = 0.0027
R_LOWER_BASE = 1.28
R_LOWER_SLOPE = 0.0072


@dataclass(frozen=True)
class FourDimCounts:
    """Auditable raw counts for the four calibration dimensions."""

    prereq: float      # P: knowledge points + cognitive depth
    reasoning: float   # R: irreducible structural steps / deductions
    compute: float     # C: operation + carry / fraction / algebraic load
    error: float       # E: structural traps / constraints / branches
    evidence: str = ""

    def normalized(self) -> dict[str, float]:
        return {
            "prereq": min(max(self.prereq, 0.0) / CAPS["prereq"], 1.0),
            "reasoning": min(max(self.reasoning, 0.0) / CAPS["reasoning"], 1.0),
            "compute": min(max(self.compute, 0.0) / CAPS["compute"], 1.0),
            "error": min(max(self.error, 0.0) / CAPS["error"], 1.0),
        }

    def composite_score(self) -> float:
        norm = self.normalized()
        return 100.0 * sum(DIMENSION_WEIGHTS[k] * norm[k] for k in DIMENSION_WEIGHTS)

    def grade_seconds(self) -> float:
        """Same-grade center seconds derived from the four structural counts."""
        return float(
            18.0
            + 8.0 * self.prereq
            + 12.0 * self.reasoning
            + 8.0 * self.compute
            + 10.0 * self.error
        )

    def ratios(self) -> tuple[float, float]:
        comp = self.composite_score()
        r_ai = min(R_AI_BASE + R_AI_SLOPE * comp, 0.95)
        r_lower = min(R_LOWER_BASE + R_LOWER_SLOPE * comp, 3.00)
        return r_ai, r_lower


def score_calibrated_problem(
    problem_id: str,
    stem: str,
    counts: FourDimCounts,
    *,
    star: int | None = None,
    role: str = "",
) -> dict[str, Any]:
    t_g = counts.grade_seconds()
    r_ai, r_lower = counts.ratios()
    payload = {
        "problem_id": problem_id,
        "ai": series(t_g, r_ai),
        "lower_grade": series(t_g, r_lower),
        "grade": series(t_g, 1.0),
        "weight": 1.0,
    }
    res: ProblemTimeResult = score_problem(samples_from_dict(payload))
    comp = counts.composite_score()
    norm = counts.normalized()
    return {
        "problem_id": problem_id,
        "star": star,
        "role": role,
        "stem": stem,
        "counts": asdict(counts),
        "normalized": {k: round(v, 4) for k, v in norm.items()},
        "composite_D": round(comp, 2),
        "t_g": round(t_g, 2),
        "r_AI": round(r_ai, 6),
        "r_lower": round(r_lower, 6),
        "tau": res.tau,
        "grade_equivalent_seconds": round(res.tau * res.reports[2].primary_geo, 2),
        "source": "derived_from_question_structure",
        "_result": res,
    }
