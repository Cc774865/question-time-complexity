from problem_time.grade_use import GradeUseError, read_grade_use


def test_joint_and_single_grades() -> None:
    joint = read_grade_use("使用年级：L3L4")
    assert joint.grades == (3, 4)
    assert joint.shared is True
    assert joint.label == "3年级、4年级共同使用"

    third = read_grade_use("L3")
    assert third.grades == (3,)
    assert third.shared is False
    assert third.label == "3年级使用"

    fifth = read_grade_use("使用年级：L5")
    assert fifth.label == "5年级使用"

    middle = read_grade_use("使用年级：L7L8L9\u200b")
    assert middle.grades == (7, 8, 9)
    assert middle.label == "7年级、8年级、9年级共同使用"


def test_every_grade_from_one_to_eight() -> None:
    for grade in range(1, 9):
        found = read_grade_use(f"使用年级：L{grade}")
        assert found.grades == (grade,)
        assert found.label == f"{grade}年级使用"
    pair = read_grade_use("使用年级：L1L2")
    assert pair.grades == (1, 2)
    assert pair.label == "1年级、2年级共同使用"
    upper = read_grade_use("使用年级：L7L8")
    assert upper.grades == (7, 8)


def test_sprint_codes() -> None:
    assert read_grade_use("使用年级：ZKCC").label == "中考冲刺"
    assert read_grade_use("使用年级：zkcc").code == "ZKCC"
    assert read_grade_use("使用年级：zkcc").label == "中考冲刺"
    assert read_grade_use("GKCC").label == "高考冲刺"
    assert read_grade_use("gkcc").code == "GKCC"
    assert read_grade_use("使用年级：ZKCC").grades == ()


def test_grade_is_required_before_questions() -> None:
    for source in ("课次：8\n2星-例\n题目：计算", "使用年级：五年级"):
        try:
            read_grade_use(source)
        except GradeUseError:
            continue
        raise AssertionError(source)
