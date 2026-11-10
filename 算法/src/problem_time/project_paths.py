"""Locate the folders of the standalone 题目时间复杂度 project."""

from pathlib import Path


def project_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "知识库").is_dir() and (parent / "算法").is_dir():
            return parent
    raise RuntimeError("找不到题目时间复杂度项目根目录")


def examples_dir() -> Path:
    return project_root() / "历史对照" / "早期刻度卷"
