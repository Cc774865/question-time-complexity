from __future__ import annotations

import math
from statistics import median


def geometric_mean(values: list[float]) -> float:
    """正数序列的几何平均。含非正数则报错（需先清洗）。"""
    if not values:
        raise ValueError("几何平均需要至少 1 个样本")
    if any(v <= 0 for v in values):
        raise ValueError("几何平均要求全部样本 > 0")
    return math.exp(sum(math.log(v) for v in values) / len(values))


def median_time(values: list[float]) -> float:
    if not values:
        raise ValueError("中位数需要至少 1 个样本")
    return float(median(values))


def summarize(values: list[float]) -> dict[str, float]:
    """同时给出主指标（geo）与对照（median）。"""
    return {
        "geo": geometric_mean(values),
        "median": median_time(values),
        "n": float(len(values)),
    }
