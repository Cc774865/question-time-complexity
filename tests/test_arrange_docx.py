import tempfile
from pathlib import Path

from docx import Document

from problem_time.arrange_docx import arrange_docx


def test_only_star_class_and_order_change() -> None:
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        _check(root / "in.docx", root / "out.docx")


def _check(source: Path, dest: Path) -> None:
    document = Document()
    document.add_paragraph("课次：W8")
    document.add_paragraph("使用年级：L3L4")
    document.add_paragraph("题目：计算。")
    document.add_paragraph("（1）325÷25")
    document.add_paragraph("答案：（1）13")
    document.add_paragraph("解析：")
    document.add_paragraph("= 13")
    document.add_paragraph("题目：计算。")
    document.add_paragraph("（1）360÷20")
    document.add_paragraph("答案：（1）18")
    document.add_paragraph("解析：")
    document.add_paragraph("= 18")
    document.add_paragraph("作业题（　缩小同一个数）")
    document.add_paragraph("题目：计算 88800÷400。")
    document.add_paragraph("答案：222")
    document.add_paragraph("解析：")
    document.add_paragraph("= 222")
    document.add_paragraph("晋级题")
    document.add_paragraph("星级：")
    document.add_paragraph("题目：计算 675÷25。")
    document.add_paragraph("解析：")
    document.add_paragraph("= 27")
    document.save(source)

    arrange_docx(
        source,
        dest,
        lessons=[(1, 2, "例"), (0, 2, "练")],
        homework=[(0, "B")],
        promotion=[(0, 2)],
    )
    text = [paragraph.text for paragraph in Document(dest).paragraphs if paragraph.text.strip()]
    assert text[:4] == ["课次：W8", "使用年级：L3L4", "2星-例", "题目：计算。"]
    assert "（1）360÷20" in text
    assert text[text.index("2星-例") + 1] == "题目：计算。"
    assert text[text.index("（1）360÷20") + 3] == "= 18"
    assert text[text.index("（1）325÷25") + 3] == "= 13"
    assert "B-作业题（　缩小同一个数）" in text
    assert "星级：2star" in text
    assert "= 222" in text
    assert "= 27" in text
