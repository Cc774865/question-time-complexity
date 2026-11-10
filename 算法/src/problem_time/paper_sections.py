"""See whether the input document actually contains homework or promotion."""

from __future__ import annotations

import re
from dataclasses import dataclass

_HOMEWORK_LINE = re.compile(
    r"^(?:(?:AAA|AA|A|B|S|N|\d+)(?:\s*[-－—]\s*作业题|作业题)|作业题)(?:（[^）]*）|\([^)]*\))?$"
)
_PROMOTION_LINE = re.compile(r"^晋级题(?:（[^）]*）|\([^)]*\))?$")


@dataclass(frozen=True)
class PaperSections:
    homework: bool
    promotion: bool


def paper_sections(text: str) -> PaperSections:
    """Homework and promotion exist only as headings in the input document.

    A missing heading means that block is not read and not written back.
    """
    homework = False
    promotion = False
    for raw in text.splitlines():
        line = raw.replace("\u200b", "").strip()
        if _HOMEWORK_LINE.match(line):
            homework = True
        if _PROMOTION_LINE.match(line):
            promotion = True
    return PaperSections(homework=homework, promotion=promotion)
