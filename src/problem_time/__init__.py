"""做题时间模型：几何平均为主，中位数对照，三因子加权。"""

from .calibration import FourDimCounts, score_calibrated_problem
from .score import ProblemSamples, ProblemTimeResult, aggregate_set, score_problem
from .stars import assign_stars, pair_tau

__all__ = [
    "FourDimCounts",
    "ProblemSamples",
    "ProblemTimeResult",
    "aggregate_set",
    "assign_stars",
    "pair_tau",
    "score_calibrated_problem",
    "score_problem",
]


def score_problem_dict(*args, **kwargs):
    from .pipeline import score_problem_dict as _fn

    return _fn(*args, **kwargs)
