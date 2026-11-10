"""Structural calibration for time complexity τ.

Combines the four objective dimensions from k12-difficulty-calibration
(`prereq`, `reasoning`, `compute`, `error`) with a fifth, zero-centered
textbook-familiarity dimension.

P, R, C, E come from the question stem and the required mathematical
structure, never from prose length or document order. Familiarity is read
from the textbook-model library and does not rewrite those four counts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

# Exact weights from k12-difficulty-calibration (WEIGHTS_NO_HIST). They still sum to 1.
# Familiarity is not part of that set: it is centered at 0 and added on its own.
# Grades 1–7 use this set. Grade 8, grade 9, 中考冲刺 and 高考冲刺 do not.
DIMENSION_WEIGHTS: dict[str, float] = {
    "prereq": 0.18,
    "reasoning": 0.31,
    "compute": 0.25,
    "error": 0.26,
}
# Upper grades still sum to 1. Computation drops from 0.25 to 0.08, and the
# 0.17 moves to reasoning. A full calculation load then changes τ by about
# 0.027, which is less than one difficulty band.
UPPER_DIMENSION_WEIGHTS: dict[str, float] = {
    "prereq": 0.18,
    "reasoning": 0.48,
    "compute": 0.08,
    "error": 0.26,
}
UPPER_GRADE_CODES = frozenset({"ZKCC", "GKCC"})
FAMILIARITY_WEIGHT = 0.18

# Normalization caps so 8-star problems across primary and middle school do not saturate early.
# Familiarity uses the same ruler as prereq, so a gap of 3 is one star band (ΔD = 9).
CAPS: dict[str, float] = {
    "prereq": 6.0,     # knowledge points + cognitive depth (1..6)
    "reasoning": 12.0, # irreducible structural inference / transformation steps (1..12)
    "compute": 10.0,   # arithmetic / algebraic operation load + carries/regrouping (1..10)
    "error": 6.0,      # structural trap / constraint / branch / hidden-unit count (0..6)
    "familiarity": 6.0,
}

# Signed familiarity. 0 is "just introduced" or "not applied". Higher is less familiar.
FAMILIARITY_OFFSET: dict[str, float] = {
    "reinforced": -1.5,
    "core": -0.75,
    "introduced": 0.0,
    "uncommon_transform": 1.5,
    "out_of_scope": 2.0,
}

# τ is a difficulty index on the legacy display scale.  It is intentionally
# derived from D only: AI and lower-grade simulated completion times do not
# enter formal difficulty scoring.
TAU_BASE = 50.89 / 63.0
TAU_PER_D = 0.003414285714


@dataclass(frozen=True)
class FourDimCounts:
    """Auditable raw counts. The fifth field is textbook familiarity, default 0."""

    prereq: float      # P: knowledge points + cognitive depth
    reasoning: float   # R: irreducible structural steps / deductions
    compute: float     # C: operation + carry / fraction / algebraic load
    error: float       # E: structural traps / constraints / branches
    evidence: str = ""
    familiarity: float = 0.0  # F: signed; 0 leaves τ on the structural score

    def normalized(self) -> dict[str, float]:
        familiarity_cap = CAPS["familiarity"]
        return {
            "prereq": min(max(self.prereq, 0.0) / CAPS["prereq"], 1.0),
            "reasoning": min(max(self.reasoning, 0.0) / CAPS["reasoning"], 1.0),
            "compute": min(max(self.compute, 0.0) / CAPS["compute"], 1.0),
            "error": min(max(self.error, 0.0) / CAPS["error"], 1.0),
            "familiarity": min(max(self.familiarity, -familiarity_cap), familiarity_cap) / familiarity_cap,
        }

    def composite_score(self, weights: dict[str, float] | None = None) -> float:
        chosen = DIMENSION_WEIGHTS if weights is None else weights
        norm = self.normalized()
        structural = sum(chosen[k] * norm[k] for k in ("prereq", "reasoning", "compute", "error"))
        return 100.0 * (structural + FAMILIARITY_WEIGHT * norm["familiarity"])

    def grade_seconds(self) -> float:
        """Same-grade center seconds. Familiarity uses the same 8 seconds as P."""
        familiarity_cap = CAPS["familiarity"]
        familiarity = min(max(self.familiarity, -familiarity_cap), familiarity_cap)
        return float(
            18.0
            + 8.0 * self.prereq
            + 12.0 * self.reasoning
            + 8.0 * self.compute
            + 10.0 * self.error
            + 8.0 * familiarity
        )

def uses_upper_grade_weights(code: str = "", grades: tuple[int, ...] = ()) -> bool:
    """Grade 8, grade 9, 中考冲刺 and 高考冲刺 use the low computation weight.

    A shared paper uses it when any audience grade is 8 or 9. Standalone
    grade 7 stays on the original weights. 高考冲刺 has no grade bundle, so
    its code selects the rule by itself.
    """
    token = code.replace("\u200b", "").strip().upper()
    if token in UPPER_GRADE_CODES:
        return True
    return any(grade >= 8 for grade in grades)


def dimension_weights_for(code: str = "", grades: tuple[int, ...] = ()) -> dict[str, float]:
    """Return the structural weights for this paper's audience."""
    if uses_upper_grade_weights(code, grades):
        return UPPER_DIMENSION_WEIGHTS
    return DIMENSION_WEIGHTS


def score_calibrated_problem(
    problem_id: str,
    stem: str,
    counts: FourDimCounts,
    *,
    role: str = "",
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Score one problem from its structural counts and familiarity.

    No star rating, document order, or answer-text length enters the formula.
    Familiarity defaults to 0, which leaves the four structural dimensions alone.
    AI and lower-grade simulated times are intentionally not part of τ.
    ``weights`` selects the grade band. Omitted weights are the grade 1–7 set.
    """
    chosen = DIMENSION_WEIGHTS if weights is None else weights
    t_g = counts.grade_seconds()
    comp = counts.composite_score(chosen)
    norm = counts.normalized()
    tau = TAU_BASE + TAU_PER_D * comp
    return {
        "problem_id": problem_id,
        "role": role,
        "stem": stem,
        "counts": asdict(counts),
        "normalized": {k: round(v, 4) for k, v in norm.items()},
        "composite_D": round(comp, 2),
        "t_g": round(t_g, 2),
        "tau": tau,
        "grade_equivalent_seconds": round(tau * t_g, 2),
        "source": "derived_from_question_structure",
        "weightRule": "upper" if chosen == UPPER_DIMENSION_WEIGHTS else "standard",
        "dimensionWeights": {
            key: chosen[key] for key in ("prereq", "reasoning", "compute", "error")
        },
    }
