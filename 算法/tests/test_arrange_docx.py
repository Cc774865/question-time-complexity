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
    assert "B-作业题" in text
    assert "（　缩小同一个数）" not in text
    assert "星级：2star" in text
    assert "= 222" in text
    assert "= 27" in text


def test_unplaced_blocks_stay_marked_n() -> None:
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        source = root / "in.docx"
        document = Document()
        document.add_paragraph("课次：W8")
        document.add_paragraph("使用年级：L3L4")
        document.add_paragraph("题目：计算。")
        document.add_paragraph("答案：1")
        document.add_paragraph("AAA-作业题（6星　添括号凑整）")
        document.add_paragraph("题目：计算 1800000÷8÷125÷2÷50。")
        document.add_paragraph("答案：18")
        document.add_paragraph("解析：")
        document.add_paragraph("= 18")
        document.add_paragraph("晋级题")
        document.add_paragraph("星级：6star")
        document.add_paragraph("课件 ID：W8-L3L4-11")
        document.add_paragraph("题目类型：运算与式")
        document.add_paragraph("题目：计算 6400÷(32×5÷17)。")
        document.add_paragraph("答案：680")
        document.save(source)
        dest = root / "out.docx"
        arrange_docx(source, dest, [(0, 2, "例")], [(0, "N")], [], [(0, "N")])
        text = "\n".join(paragraph.text for paragraph in Document(dest).paragraphs)
        assert "N-作业题" in text
        assert "（添括号凑整）" not in text
        assert "1800000÷8÷125÷2÷50" in text
        assert "= 18" in text
        assert "班型：N" in text
        assert "星级：6star" not in text
        assert "题目类型：运算与式" in text
        assert "6400÷(32×5÷17)" in text
        assert "答案：680" in text
