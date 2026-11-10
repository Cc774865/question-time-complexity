"""Turn a question stem into the four structural counts.

The counts follow the scales in docs/计算方法.md. Answer text and how
long the worked solution is do not enter. Stars do not enter.
"""

from __future__ import annotations

import re

from problem_time.calibration import FourDimCounts

_MUL = re.compile(r"(\d+)\s*[×xX*]\s*(\d+)(?!\d)")
_DIV = re.compile(r"(\d+)\s*[÷/]\s*(\d+)")
_OP = re.compile(r"[+＋\-－×÷*/]")
_BLANK = re.compile(r"[□△○▢]")
_RULE = re.compile(r"[─—━]{2,}")
_SPOKEN = (
    "题目", "计算", "列竖式", "如图", "所示", "不同", "汉字", "代表", "数字",
    "那么", "分别", "什么", "下面", "竖式", "补全", "下图", "中的", "有些",
    "三角形", "纸片", "盖住了", "盖住", "实际", "乘积", "结果", "应该", "多少",
    "残缺", "算式", "知道", "位置", "只", "上的", "是", "该", "求", "在",
)


def structure_counts(stem: str) -> FourDimCounts:
    """Count P, R, C, E from the stem alone."""
    text = stem.replace("\u200b", "")
    multiplications = [(int(left), int(right)) for left, right in _MUL.findall(text)]
    one_digit = [(left, right) for left, right in multiplications if right <= 9]
    divisions = _DIV.findall(text)
    blanks = len(_BLANK.findall(text))
    unknowns = blanks + len(_cjk_on_formula(text))
    rules = len(_RULE.findall(text))
    two_row = rules >= 2
    grown = sum(1 for left, right in one_digit if len(str(left * right)) > len(str(left)))
    carries = sum(_school_carries(left, right) for left, right in one_digit)
    chained = any(_school_carries(left, right) >= 2 for left, right in one_digit)

    if unknowns:
        prereq = 5.0 if two_row or _two_digit_multiplier(text) else 4.0
        reasoning = 2.0 + 0.8 * unknowns + (1.5 if two_row else 0.0)
        compute = 1.5 + 0.4 * unknowns
        error = 1.0 + (0.5 if two_row else 0.0)
        evidence = f"竖式里有 {unknowns} 个待定位"
        if two_row:
            evidence += "，并且有第二行部分积"
    elif one_digit:
        prereq = 2.0 if carries else 1.5
        reasoning = 1.0 + (0.5 if grown else 0.0)
        compute = 0.8 * len(one_digit) + 0.3 * carries
        error = 0.0
        if chained:
            error += 1.0
        elif carries:
            error += 0.5
        if grown:
            error += 0.5
        evidence = f"{len(one_digit)} 道一位数乘法，进位 {carries} 次"
        if grown:
            evidence += "，积升位"
    else:
        operations = len(_OP.findall(text))
        prereq = 2.0 if operations else 1.5
        reasoning = 1.0 + 0.4 * max(operations - 1, 0)
        compute = 0.9 * max(operations, len(divisions))
        error = 0.5 if operations else 0.0
        evidence = f"题面有 {operations} 处运算" if operations else "题面没有可数的算式"

    return FourDimCounts(
        prereq=min(prereq, 6.0),
        reasoning=min(reasoning, 12.0),
        compute=min(compute, 10.0),
        error=min(error, 6.0),
        evidence=evidence,
    )


def _school_carries(multiplicand: int, multiplier: int) -> int:
    carry = 0
    count = 0
    for digit in reversed(str(multiplicand)):
        product = int(digit) * multiplier + carry
        if product >= 10:
            count += 1
            carry = product // 10
        else:
            carry = 0
    return count


def _cjk_on_formula(stem: str) -> set[str]:
    stripped = stem
    for word in _SPOKEN:
        stripped = stripped.replace(word, "")
    found: set[str] = set()
    for raw in stripped.splitlines():
        compact = re.sub(r"\s+", "", raw)
        formula = any(mark in raw for mark in "×÷□△○─—━")
        if not formula and len(compact) > 8:
            continue
        for char in compact:
            if "\u4e00" <= char <= "\u9fff":
                found.add(char)
    return found


def _two_digit_multiplier(stem: str) -> bool:
    for line in stem.splitlines():
        if "×" not in line and "x" not in line and "X" not in line:
            continue
        right = re.split(r"[×xX]", line, maxsplit=1)[-1]
        slots = re.findall(r"\d|[□△○]|[\u4e00-\u9fff]", right)
        if len(slots) >= 2:
            return True
    return False
