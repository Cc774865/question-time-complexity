import json
import tempfile
from pathlib import Path

from docx import Document

from problem_time.calibration import score_calibrated_problem
from problem_time.run_paper import PaperRunError, run_paper, run_started
from problem_time.structure_counts import structure_counts


def test_dragging_a_pair_to_the_top_makes_it_two_stars() -> None:
    from problem_time.arrange_docx import order_lesson_stars

    result = {"base": {"lessons": [[0, 6, "例"], [1, 6, "练"], [2, 2, "例"], [3, 2, "练"], [4, 3, "例"]]}}
    order_lesson_stars(result, [0, 2, 4])
    assert result["base"]["lessons"] == [[0, 2, "例"], [1, 2, "练"], [2, 3, "例"], [3, 3, "练"], [4, 4, "例"]]


def test_a_blank_puzzle_outranks_a_plain_product() -> None:
    plain = score_calibrated_problem("plain", "124×3", structure_counts("124 × 3 ＝"))
    puzzle = score_calibrated_problem("puzzle", "车马", structure_counts("车 马\n×    车\n───────\n马 车 车"))
    assert puzzle["tau"] > plain["tau"]


def test_start_writes_one_docx_from_the_clicked_file() -> None:
    with tempfile.TemporaryDirectory() as folder:
        inbox = Path(folder)
        source = inbox / "W5-L3L4-7.docx"
        _paper(source)
        (inbox / "start.json").write_text(
            json.dumps({"files": ["W5-L3L4-7.docx"]}),
            encoding="utf-8",
        )
        result = run_started(inbox)
        assert result["filename"] == "W5-L3L4-7.docx"
        assert result["released"] is False
        assert not (inbox / "output.docx").is_file()
        assert result["review"][0]["kind"] == "作业题"
        assert result["review"][0]["level"] == ""
        assert "请在人工审核里选定班型后提交" in (inbox / "progress.json").read_text(encoding="utf-8")
        result["review"][0]["level"] = "B"
        from problem_time.arrange_docx import apply_review_levels

        apply_review_levels(inbox, result)
        text = "\n".join(paragraph.text for paragraph in Document(inbox / "output.docx").paragraphs)
        assert "2星-例" in text
        assert "3星-例" in text
        assert "372" in text
        assert "B-作业题" in text
        assert "（　进位）" not in text


def test_an_unmatched_homework_stays_in_the_file() -> None:
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        source = root / "in.docx"
        document = Document()
        document.add_paragraph("周次：W8")
        document.add_paragraph("使用年级：L3L4")
        document.add_paragraph("课次：11")
        document.add_paragraph("题目：计算 12÷3。")
        document.add_paragraph("答案：4")
        document.add_paragraph("题目：计算 15÷3。")
        document.add_paragraph("答案：5")
        document.add_paragraph("A-作业题（3星　分配律）")
        document.add_paragraph("题目：计算 (505－85＋155)÷5。")
        document.add_paragraph("答案：115")
        document.add_paragraph("解析：")
        document.add_paragraph("= 115")
        document.add_paragraph("晋级题")
        document.add_paragraph("星级：3star")
        document.add_paragraph("课件 ID：W8-L3L4-11")
        document.add_paragraph("题目：计算 99999÷7。")
        document.add_paragraph("答案：14285")
        document.save(source)
        dest = root / "out.docx"
        result = run_paper(source, dest)
        assert result["released"] is False
        assert not dest.is_file()
        assert [item["kind"] for item in result["review"]] == ["作业题", "晋级题"]
        assert result["base"]["homework"] == []
        result["review"][0]["level"] = "A"
        result["review"][1]["level"] = "B"
        from problem_time.arrange_docx import write_plan

        write_plan(source, dest, result)
        text = "\n".join(paragraph.text for paragraph in Document(dest).paragraphs)
        assert "A-作业题" in text
        assert "（3星　分配律）" not in text
        assert "答案：115" in text
        assert "= 115" in text
        assert "S-作业题" not in text
        assert "B-晋级题" in text
        assert "99999÷7" in text


def test_printed_star_is_not_kept() -> None:
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        source = root / "in.docx"
        document = Document()
        document.add_paragraph("周次：W7")
        document.add_paragraph("使用年级：L5L6")
        document.add_paragraph("课次：10")
        document.add_paragraph("8星-例")
        document.add_paragraph("1+1")
        document.add_paragraph("答案：2")
        document.add_paragraph("2星-练")
        document.add_paragraph("车 马")
        document.add_paragraph("×    车")
        document.add_paragraph("───────")
        document.add_paragraph("马 车 车")
        document.add_paragraph("答案：8")
        document.save(source)
        dest = root / "out.docx"
        result = run_paper(source, dest)
        text = [paragraph.text for paragraph in Document(dest).paragraphs if paragraph.text.strip()]
        assert result["base"]["lessons"][0][1] == 2
        assert text.count("2星-例") == 1
        assert "8星-例" not in text


def test_a_reader_fills_numbers_without_replacing_the_picture() -> None:
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        source = root / "in.docx"
        _picture_paper(source, root / "dot.png")
        seen: list[str] = []

        def reader(images, context):
            seen.append(context)
            assert images and images[0][1] == "image/png"
            return "3/4"

        dest = root / "out.docx"
        run_paper(source, dest, image_reader=reader)
        written = Document(dest)
        text = "\n".join(paragraph.text for paragraph in written.paragraphs)
        assert seen
        assert "3/4" not in text
        assert "一根彩带长" in text
        from docx.oxml.ns import qn
        assert len(written.element.body.findall(".//" + qn("a:blip"))) == 1


def test_a_written_geometry_question_does_not_need_a_digit() -> None:
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        source = root / "in.docx"
        picture = root / "dot.png"
        picture.write_bytes(bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
            "890000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
        ))
        document = Document()
        document.add_paragraph("周次：W9")
        document.add_paragraph("使用年级：ZKCC")
        document.add_paragraph("课次：18")
        document.add_paragraph("题目")
        paragraph = document.add_paragraph("在通过构造全等三角形解决的问题中，有一种方法叫倍长中线法。")
        paragraph.add_run().add_picture(str(picture))
        document.add_paragraph("答案：1.5到6.5")
        document.add_paragraph("题目")
        document.add_paragraph("同样用倍长中线，求另一条中线的取值范围。")
        document.add_paragraph("答案：2到7")
        document.save(source)

        def reader(images, context):
            return "三角形，没有数字"

        dest = root / "out.docx"
        result = run_paper(source, dest, image_reader=reader)
        assert result["base"]["lessons"]
        assert dest.is_file()


_MEDIAN = """解：∵AD是三角形ABC的中线，
∴BD=CD，
又∵ED=AD，∠BDE=∠CDA，
∴SAS，
∴BE=AC=5，
在三角形ABE中，∵AB-BE<AE<AB+BE，
∴8-5<2AD<8+5，
∴1.5<AD<6.5"""


def test_a_figure_without_digits_is_scored_from_the_solution() -> None:
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        source = root / "in.docx"
        picture = root / "dot.png"
        _write_png(picture)
        document = Document()
        document.add_paragraph("周次：W9")
        document.add_paragraph("使用年级：ZKCC")
        document.add_paragraph("课次：18")
        _lesson(document, picture, "求这条中线的范围。", "代入得6")
        _lesson(document, picture, "再求一次范围。", "代入得7")
        _lesson(document, picture, "在通过构造全等三角形解决的问题中，有一种方法叫倍长中线法。", _MEDIAN)
        _lesson(document, picture, "同样用倍长中线，求另一条中线的取值范围。", _MEDIAN)
        document.save(source)

        def reader(images, context):
            raise AssertionError("the figure is not the source of the numbers")

        dest = root / "out.docx"
        result = run_paper(source, dest, image_reader=reader)
        stars = [item[1] for item in result["base"]["lessons"] if item[2] == "例"]
        assert stars == [2, 3]
        text = "\n".join(paragraph.text for paragraph in Document(dest).paragraphs)
        assert "求这条中线的范围。" in text
        assert "8-5<2AD<8+5" in text
        assert "代入得6" in text


def test_picture_numbers_do_not_become_a_file() -> None:
    with tempfile.TemporaryDirectory() as folder:
        inbox = Path(folder)
        source = inbox / "W7-L5L6-10.docx"
        _picture_paper(source, inbox / "dot.png")
        (inbox / "start.json").write_text(json.dumps({"files": [source.name]}), encoding="utf-8")
        (inbox / "output.docx").write_bytes(b"old")
        try:
            run_started(inbox)
        except PaperRunError as exc:
            assert "图片" in str(exc)
        else:
            raise AssertionError("picture stem was scored")
        assert not (inbox / "output.docx").is_file()
        assert not (inbox / "result.json").is_file()


def _write_png(picture: Path) -> None:
    picture.write_bytes(bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
    ))


def _lesson(document: Document, picture: Path, stem: str, solution: str) -> None:
    document.add_paragraph("题目")
    paragraph = document.add_paragraph(stem)
    paragraph.add_run().add_picture(str(picture))
    document.add_paragraph("答案：见解析")
    document.add_paragraph("解析")
    document.add_paragraph(solution)


def _picture_paper(source: Path, picture: Path) -> None:
    picture.write_bytes(bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
    ))
    document = Document()
    document.add_paragraph("周次：W7")
    document.add_paragraph("使用年级：L5L6")
    document.add_paragraph("课次：10")
    document.add_paragraph("2星-例")
    paragraph = document.add_paragraph("一根彩带长")
    paragraph.add_run().add_picture(str(picture))
    paragraph.add_run("米")
    document.add_paragraph("【答案】")
    document.save(source)


def _paper(path: Path) -> None:
    document = Document()
    document.add_paragraph("周次：W5")
    document.add_paragraph("使用年级：L3L4")
    document.add_paragraph("课次：7")
    document.add_paragraph("题目")
    document.add_paragraph("124 × 3 ＝")
    document.add_paragraph("答案：372")
    document.add_paragraph("解析：")
    document.add_paragraph("= 372")
    document.add_paragraph("题目")
    document.add_paragraph("218 × 4 ＝")
    document.add_paragraph("答案：872")
    document.add_paragraph("题目")
    document.add_paragraph("车 马")
    document.add_paragraph("×    车")
    document.add_paragraph("───────")
    document.add_paragraph("马 车 车")
    document.add_paragraph("答案：车 = 8")
    document.add_paragraph("题目")
    document.add_paragraph("学")
    document.add_paragraph("× 学")
    document.add_paragraph("好学习")
    document.add_paragraph("答案：学 = 5")
    document.add_paragraph("作业题（　进位）")
    document.add_paragraph("题目：计算 124×3。")
    document.add_paragraph("答案：372")
    document.save(path)
