"""Read 使用年级 before any question text is interpreted."""

from __future__ import annotations

import re
from dataclasses import dataclass

_SPRINT_LABELS = {
    "ZKCC": "中考冲刺",
    "GKCC": "高考冲刺",
}
_CODE = re.compile(r"(?:ZKCC|GKCC|(?:L[1-9]\d*)+)")
_GRADE_LINE = re.compile(r"使用年级\s*[:：]\s*(\S+)")


class GradeUseError(ValueError):
    """使用年级缺失或无法识别。读题不得开始。"""


@dataclass(frozen=True)
class GradeUse:
    code: str
    grades: tuple[int, ...]
    shared: bool
    label: str


def read_grade_use(source: str) -> GradeUse:
    """Resolve 使用年级 from a header line or a bare code.

    Input files carry the audience only in this field. Question text is not
    consulted. ``L1`` through ``L8`` are those grades alone. Codes stuck
    together, such as ``L1L2`` or ``L5L6``, are shared by those grades.
    ``ZKCC`` is 中考冲刺 and ``GKCC`` is 高考冲刺.
    """
    code = _extract_code(source)
    if code in _SPRINT_LABELS:
        return GradeUse(code=code, grades=(), shared=False, label=_SPRINT_LABELS[code])
    grades = _grades_in(code)
    if len(grades) > 1:
        label = "、".join(f"{grade}年级" for grade in grades) + "共同使用"
    else:
        label = f"{grades[0]}年级使用"
    return GradeUse(code=code, grades=grades, shared=len(grades) > 1, label=label)


def _extract_code(source: str) -> str:
    text = source.replace("\u200b", "").strip()
    found = _GRADE_LINE.search(text)
    token = found.group(1) if found else text
    token = token.replace("\u200b", "").strip().upper()
    if not _CODE.fullmatch(token):
        raise GradeUseError("读题之前必须先认出使用年级")
    return token


def _grades_in(code: str) -> tuple[int, ...]:
    numbers = re.findall(r"L([1-9]\d*)", code)
    if not numbers or "".join(f"L{number}" for number in numbers) != code:
        raise GradeUseError("读题之前必须先认出使用年级")
    return tuple(int(number) for number in numbers)
