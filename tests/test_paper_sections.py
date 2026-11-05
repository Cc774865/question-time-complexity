from problem_time.paper_sections import paper_sections


def test_missing_blocks_are_absent() -> None:
    text = "使用年级：L5\n2星-例\n题目：计算\n答案：1\n解析：直接算"
    found = paper_sections(text)
    assert found.homework is False
    assert found.promotion is False


def test_blocks_follow_the_input_headings() -> None:
    homework_only = "B-作业题（2星）\n题目\n计算：1"
    found = paper_sections(homework_only)
    assert found.homework is True
    assert found.promotion is False

    both = homework_only + "\n晋级题\n星级：2star\n题目：计算：1"
    found = paper_sections(both)
    assert found.homework is True
    assert found.promotion is True
    assert paper_sections("N作业题\n题目\n计算：1").homework is True
    titled = paper_sections("作业题（缩小同一个数）\n题目：计算 1")
    assert titled.homework is True
    assert titled.promotion is False
