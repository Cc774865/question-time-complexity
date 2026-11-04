from __future__ import annotations

from dataclasses import dataclass


# 下一年级权重 = 本题年级 × 1.1（三年级比四年级多约 10% 影响）
GRADE_RATIO = 1.1


@dataclass(frozen=True)
class ThreeFactorWeights:
    """
    三因子权重：AI、下一年级 (g-1)、本题年级 (g)。

    约束：
    - 三者之和 = 1
    - w_{g-1} = GRADE_RATIO * w_g
    """

    w_ai: float
    w_lower: float  # w_{g-1}
    w_grade: float  # w_g

    def __post_init__(self) -> None:
        s = self.w_ai + self.w_lower + self.w_grade
        if abs(s - 1.0) > 1e-9:
            raise ValueError(f"三因子权重之和必须为 1，当前={s}")
        if self.w_ai < 0 or self.w_lower < 0 or self.w_grade < 0:
            raise ValueError("权重不可为负")
        if self.w_grade > 0:
            ratio = self.w_lower / self.w_grade
            if abs(ratio - GRADE_RATIO) > 1e-6:
                raise ValueError(
                    f"要求 w_lower = {GRADE_RATIO} * w_grade，当前比值={ratio}"
                )


def make_weights(*, w_ai: float = 1.0 / 3.0) -> ThreeFactorWeights:
    """
    给定 AI 权重，按 w_lower = 1.1 * w_grade 且三者归一。

    剩余 R = 1 - w_ai：
      w_grade + w_lower = R
      w_lower = 1.1 * w_grade
    ⇒ w_grade = R / 2.1，w_lower = 1.1 * R / 2.1
    """
    if not (0.0 <= w_ai < 1.0):
        raise ValueError("w_ai 须在 [0, 1)")
    rem = 1.0 - w_ai
    w_grade = rem / (1.0 + GRADE_RATIO)
    w_lower = GRADE_RATIO * w_grade
    return ThreeFactorWeights(w_ai=w_ai, w_lower=w_lower, w_grade=w_grade)
