from problem_time.calibration import score_calibrated_problem
from problem_time.early_number_counts import early_number_counts, uses_early_picture_numbers


def test_a_plain_count_stays_at_the_bottom_of_the_scale() -> None:
    counts = early_number_counts("数一数，图里一共有几个。")
    assert (counts.prereq, counts.reasoning, counts.compute, counts.error) == (1.5, 1.0, 0.5, 0.0)
    scored = score_calibrated_problem("count", "数一数", counts)
    hidden = early_number_counts("有的小动物挡住了，数一数一共有几只。")
    harder = score_calibrated_problem("hidden", "挡住", hidden)
    assert scored["tau"] < harder["tau"]


def test_hiding_and_sorting_add_structure_not_the_object_count() -> None:
    hidden = early_number_counts("有的小动物挡住了，数一数一共有几只。")
    assert (hidden.prereq, hidden.reasoning, hidden.error) == (2.5, 3.0, 1.0)
    six = early_number_counts("数一数，图里一共有几个。")
    eight = early_number_counts("数一数，图里一共有几个。")
    assert early_number_counts("数一数，图里一共有几个。").compute == six.compute == eight.compute


def test_only_grades_one_to_three_and_not_an_arithmetic_stem() -> None:
    stem = "数一数，图里一共有几个。"
    assert uses_early_picture_numbers((1,), stem)
    assert uses_early_picture_numbers((2,), "看图读数。")
    assert uses_early_picture_numbers((2, 3), stem)
    assert uses_early_picture_numbers((1, 2, 3), stem)
    for grades in ((), (4,), (5,), (6,), (8,), (3, 4), (1, 4)):
        assert not uses_early_picture_numbers(grades, stem)
        assert not uses_early_picture_numbers(grades, "看图读数。")
    for stem_text in (
        "计算 3+2。",
        "求这条中线的范围。",
        "看图写数。",
        "比多少。",
        "一共有多少米。",
        "小棒表示的数是多少。",
    ):
        assert not uses_early_picture_numbers((1,), stem_text)
        assert not uses_early_picture_numbers((2, 3), stem_text)
