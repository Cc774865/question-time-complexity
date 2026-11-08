import json
import tempfile
from pathlib import Path

from docx import Document

from problem_time.markdown_docx import markdown_paragraphs
from problem_time.run_paper import run_started


_PAPER = """# 例

## 题干

一根彩带长55米，第一次用去10米，第二次用去25米。这根彩带比原来短了多少米？

## 答案

35

## 解析

$10+25=35$

## 解题方法

纯文本

---

# 练

## 题干

购进76本数学绘本，借走后剩下14本。借走了多少本？

## 答案

62

## 解析

$76-14=62$

## 解题方法

纯文本
"""


def test_a_markdown_paper_starts_without_a_docx() -> None:
    lines = markdown_paragraphs(_PAPER, "W3-L1-2-混合")
    assert lines[:3] == ["周次：W3", "使用年级：L1", "课次：2"]
    assert "纯文本" not in lines
    assert lines.count("题目") == 2
    with tempfile.TemporaryDirectory() as folder:
        inbox = Path(folder)
        (inbox / "W3-L1-2-混合.md").write_text(_PAPER, encoding="utf-8")
        (inbox / "start.json").write_text(
            json.dumps({"files": ["W3-L1-2-混合.md"]}),
            encoding="utf-8",
        )
        result = run_started(inbox)
        assert result["header"] == {"week": "W3", "grade": "L1", "lesson": "2"}
        assert (inbox / "preview.docx").is_file()
        assert (inbox / ".W3-L1-2-混合.docx").is_file()
        preview = "\n".join(paragraph.text for paragraph in Document(inbox / "preview.docx").paragraphs)
        assert "2星-例" in preview
        assert "2星-练" in preview
        assert "纯文本" not in preview


def test_every_markdown_file_gets_its_own_preview() -> None:
    second = _PAPER.replace("55米", "40米").replace("10米", "8米").replace("25米", "12米")
    with tempfile.TemporaryDirectory() as folder:
        inbox = Path(folder)
        (inbox / "W3-L1-2-混合.md").write_text(_PAPER, encoding="utf-8")
        (inbox / "W3-L2-2-混合.md").write_text(second, encoding="utf-8")
        (inbox / "start.json").write_text(
            json.dumps({"files": ["W3-L1-2-混合.md", "W3-L2-2-混合.md"]}),
            encoding="utf-8",
        )
        result = run_started(inbox)
        names = [item["previewName"] for item in result["batch"]]
        assert names == ["W3-L1-2-预览.docx", "W3-L2-2-预览.docx"]
        assert (inbox / "W3-L1-2-预览.docx").is_file()
        assert (inbox / "W3-L2-2-预览.docx").is_file()


if __name__ == "__main__":
    test_a_markdown_paper_starts_without_a_docx()
    test_every_markdown_file_gets_its_own_preview()
    print("ok")
