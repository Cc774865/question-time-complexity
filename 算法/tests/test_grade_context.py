from problem_time.grade_context import load_grade_context


def test_single_grade_reads_its_own_knowledge_bundle() -> None:
    context = load_grade_context("L5", (5,))
    assert context.grades == (5,)
    assert context.topic_count > 0
    assert context.model_count == 13
    assert context.model_files == ("知识库/课内模型/grade-5/models.json",)
    assert "5年级" in context.prompt


def test_shared_grade_reads_every_selected_bundle() -> None:
    context = load_grade_context("L3L4", (3, 4))
    assert context.grades == (3, 4)
    assert context.model_count == 29
    assert len(context.model_files) == 2


def test_zhongkao_reads_grades_seven_through_nine() -> None:
    context = load_grade_context("ZKCC", (7, 8, 9))
    assert context.grades == (7, 8, 9)
    assert context.model_count == 38
    assert context.model_files == (
        "知识库/课内模型/grade-7/models.json",
        "知识库/课内模型/grade-8/models.json",
        "知识库/课内模型/grade-9/models.json",
    )
    assert "中考冲刺" in context.prompt


def test_gaokao_grade_stays_pending() -> None:
    context = load_grade_context("GKCC", ())
    assert context.model_count == 0
    assert context.topic_count == 0
    assert "待定" in context.prompt
    assert "F 保持 0" in context.prompt
