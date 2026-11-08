"""Count picture counting and number reading for grades 1–3 only.

The scales are the ones in docs/低年级看图认数.md. How many objects are in
the picture does not enter. Stars do not enter. Any other grade, and any
grade 1–3 question that is not 看图数数 or 看图读数, must not call this.
"""

from __future__ import annotations

import re

from problem_time.calibration import FourDimCounts

_TASK = re.compile(r"数一数|数数|有几个|有几只|有几朵|有几支|有几根|有几辆|有几本|读数|读作")
_ARITHMETIC = re.compile(r"\d\s*[+\-－×÷*/]\s*\d")
_HIDDEN = re.compile(r"挡住|遮住|重叠|看不见|藏着")
_SCATTERED = re.compile(r"散落|杂乱|不整齐|大小不一")
_GROUPED = re.compile(r"分别|各有|分类|几类|几种")
_BUNDLE = re.compile(r"一捆|十个一捆|计数器")
_COMPARE = re.compile(r"比多少|多几|少几|同样多")


def uses_early_picture_numbers(grades: tuple[int, ...], stem: str) -> bool:
    """The only gate. Both sides must hold, or this question keeps its old counts."""
    if not grades or any(grade not in {1, 2, 3} for grade in grades):
        return False
    text = stem.replace("\u200b", "")
    if _ARITHMETIC.search(text):
        return False
    return _TASK.search(text) is not None


def early_number_counts(stem: str) -> FourDimCounts:
    """Count P, R, C, E for one early picture-number task."""
    text = stem.replace("\u200b", "")
    hidden = _HIDDEN.search(text) is not None
    scattered = _SCATTERED.search(text) is not None
    grouped = _GROUPED.search(text) is not None
    bundled = _BUNDLE.search(text) is not None
    compare = _COMPARE.search(text) is not None

    if hidden:
        prereq = 2.5
        reasoning = 3.0
    elif grouped or bundled:
        prereq = 2.0
        reasoning = 3.0 if grouped and bundled else 2.0
    else:
        prereq = 1.5
        reasoning = 1.0
    if compare:
        reasoning += 1.0

    compute = 0.8 if compare else 0.5
    error = 0.0
    if hidden:
        error += 1.0
    elif scattered:
        error += 0.5
    if grouped:
        error += 0.5

    evidence = "低年级看图认数"
    if hidden:
        evidence += "，有挡住或重叠"
    if grouped:
        evidence += "，要分类再数"
    if bundled:
        evidence += "，按捆再数零头"
    if compare:
        evidence += "，数完再比多少"

    return FourDimCounts(
        prereq=min(prereq, 6.0),
        reasoning=min(reasoning, 12.0),
        compute=round(min(compute, 10.0), 1),
        error=min(error, 6.0),
        evidence=evidence,
    )
