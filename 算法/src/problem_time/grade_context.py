"""Load the grade-specific knowledge context before a paper is scored.

The context is deliberately descriptive: it makes the selected knowledge
bundle auditable without putting textbook text or a star label into the
formula.  Structural counting still produces P/R/C/E, and textbook matching
produces F.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from problem_time.project_paths import project_root


KNOWLEDGE = project_root() / "知识库"
MODELS = KNOWLEDGE / "课内模型"
TOPICS = KNOWLEDGE / "知识点" / "topics.json"


@dataclass(frozen=True)
class GradeKnowledgeContext:
    """The knowledge bundle selected from a paper's 使用年级."""

    code: str
    grades: tuple[int, ...]
    topic_count: int
    model_count: int
    model_files: tuple[str, ...]
    prompt: str

    def report(self) -> dict[str, object]:
        return {
            "code": self.code,
            "grades": list(self.grades),
            "topicCount": self.topic_count,
            "modelCount": self.model_count,
            "modelFiles": list(self.model_files),
            "prompt": self.prompt,
        }


def load_grade_context(code: str, grades: tuple[int, ...]) -> GradeKnowledgeContext:
    """Read the knowledge bundle for the paper before interpreting its stems.

    A single ``L5`` paper reads the Grade 5 topic slice and Grade 5 textbook
    models.  A shared paper, including 中考冲刺 grades 7–9, reads every listed
    grade.  高考冲刺 has no decided grade yet and keeps structural scoring.
    """
    selected = tuple(sorted({grade for grade in grades if 1 <= grade <= 9}))
    if not selected:
        pending = "高考冲刺的适用年级待定" if code == "GKCC" else f"使用年级为 {code}，没有 1–9 年级可套用"
        return GradeKnowledgeContext(
            code=code,
            grades=(),
            topic_count=0,
            model_count=0,
            model_files=(),
            prompt=f"{pending}；只按题面结构计 P、R、C、E，F 保持 0。",
        )

    topics = _topics_for_grades(selected)
    files = tuple(MODELS / f"grade-{grade}" / "models.json" for grade in selected)
    models = sum(_model_count(path) for path in files)
    labels = "、".join(f"{grade}年级" for grade in selected)
    return GradeKnowledgeContext(
        code=code,
        grades=selected,
        topic_count=len(topics),
        model_count=models,
        model_files=tuple(path.relative_to(project_root()).as_posix() for path in files),
        prompt=(
            (
                "中考冲刺读取 7、8、9 年级的知识点与课内模型，取更不熟的一档。"
                if code == "ZKCC"
                else f"先读取 {labels} 的知识点与课内模型，再计算这份 {code} 试卷。"
            )
            + "P、R、C、E 只数题面与必经结构；再以中、高置信模型命中写入 F。"
            "不得从星级、题目顺序或解析篇幅反推难度。"
        ),
    )


@lru_cache(maxsize=9)
def _topics_for_grades(grades: tuple[int, ...]) -> tuple[dict, ...]:
    rows = json.loads(TOPICS.read_text(encoding="utf-8"))
    wanted = {str(grade) for grade in grades} | set(grades)
    return tuple(row for row in rows if row.get("grade") in wanted)


@lru_cache(maxsize=9)
def _model_count(path: Path) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return len(payload.get("models", []))
