from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RelativeTimes:
    """
    以本题年级聚合耗时 t̃_g 为 1：

      T_AI = t̃_AI / t̃_g
      T_{g-1} = t̃_{g-1} / t̃_g
      T_g = 1
    """

    t_ai: float
    t_lower: float
    t_grade: float
    T_ai: float
    T_lower: float
    T_grade: float = 1.0

    @staticmethod
    def from_aggregated(t_ai: float, t_lower: float, t_grade: float) -> "RelativeTimes":
        if t_grade <= 0:
            raise ValueError("本题年级聚合耗时必须 > 0")
        if t_ai <= 0 or t_lower <= 0:
            raise ValueError("AI / 下一年级聚合耗时必须 > 0")
        return RelativeTimes(
            t_ai=t_ai,
            t_lower=t_lower,
            t_grade=t_grade,
            T_ai=t_ai / t_grade,
            T_lower=t_lower / t_grade,
            T_grade=1.0,
        )
