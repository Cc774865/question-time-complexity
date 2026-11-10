"""Count P, R, C, E from a worked solution when the figure has no digits.

The scales are the ones in docs/图形题按解析计分.md. How many lines the
solution uses does not enter. Stars do not enter.
"""

from __future__ import annotations

import re

from problem_time.calibration import FourDimCounts

_CONGRUENCE = re.compile(r"SAS|ASA|SSS|AAS|HL|全等|≌|≅")
_RANGE = re.compile(r"[<>≤≥](?:(?![<>≤≥]).){0,24}[<>≤≥]")
_OP = re.compile(r"\d+(?:\.\d+)?\s*[+\-－×÷*/]\s*\d+(?:\.\d+)?")
_DOUBLE = re.compile(r"(?<!\d)2\s*[A-Za-z]{1,3}")
_AUX = re.compile(r"延长|作辅助线|连接")
_OPEN = re.compile(r"<(?:(?![<>]).){0,16}<")


def solution_counts(solution: str, stem: str = "") -> FourDimCounts:
    """Count the four dimensions from the solution's necessary steps."""
    text = solution.replace("\u200b", "")
    blocks = _blocks(text)
    layers = _layers(text)
    auxiliary = 0 if _AUX.search(stem) else len(_AUX.findall(text))
    constructed = auxiliary > 0 or layers >= 2

    if constructed:
        prereq = 3.8 if layers + auxiliary <= 2 else 5.6
        prereq += 2.0 if layers >= 2 and auxiliary else 1.5
    elif blocks:
        prereq = {1: 1.5, 2: 2.0}.get(blocks, 2.5) + 1.0
    else:
        prereq = 1.5

    reasoning = 2 * layers
    if re.search(r"相似|∽", text):
        reasoning += 2
    if "sides" in _names(text):
        reasoning += 2
    elif re.search(r"\d", text):
        reasoning += 1
    reasoning += 2 * auxiliary

    operations = _OP.findall(text)
    compute = 0.8 * len(operations)
    if _DOUBLE.search(text) or re.search(r"[÷/]\s*2", text):
        compute += 0.8
    if compute == 0 and re.search(r"\d", text):
        compute = 0.8
    compute = round(compute, 1)

    error = 0.0
    if _OPEN.search(text) and not re.search(r"[≤≥]", text):
        error += 1.0
    elif re.search(r"[<>]", text):
        error += 0.5
    if _DOUBLE.search(text) and re.search(r"[<>≤≥]", text):
        error += 0.5
    if re.search(r"倍长|中线", text) and re.search(r"等腰|相似", text):
        error += 1.0

    evidence = f"解析：知识块 {blocks}，全等 {layers} 层，运算 {len(operations)} 步"
    return FourDimCounts(
        prereq=min(prereq, 6.0),
        reasoning=min(float(reasoning), 12.0),
        compute=min(compute, 10.0),
        error=min(error, 6.0),
        evidence=evidence,
    )


def _blocks(text: str) -> int:
    return len(_names(text))


def _names(text: str) -> set[str]:
    found: set[str] = set()
    if "中线" in text:
        found.add("median")
    if _CONGRUENCE.search(text):
        found.add("congruence")
    if re.search(r"相似|∽", text):
        found.add("similar")
    if "三边" in text or _RANGE.search(text):
        found.add("sides")
    if "角平分" in text:
        found.add("bisector")
    if "等腰" in text:
        found.add("isosceles")
    if re.search(r"勾股|直角", text):
        found.add("right")
    if re.search(r"平行|∥", text):
        found.add("parallel")
    if re.search(r"垂直|⊥", text):
        found.add("perpendicular")
    if re.search(r"sin|cos|tan|正弦|余弦|正切", text, re.IGNORECASE):
        found.add("trig")
    return found


def _layers(text: str) -> int:
    named = len(re.findall(r"SAS|ASA|SSS|AAS|HL", text))
    marked = len(re.findall(r"≌|≅|全等", text))
    if named and marked:
        return max(named, marked)
    return named or marked
