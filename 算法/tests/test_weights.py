from problem_time.weights import GRADE_RATIO, make_weights


def test_default_third_ai():
    w = make_weights(w_ai=1.0 / 3.0)
    assert abs(w.w_ai + w.w_lower + w.w_grade - 1.0) < 1e-12
    assert abs(w.w_lower / w.w_grade - GRADE_RATIO) < 1e-9
    assert abs(w.w_grade - (1 - 1 / 3) / 2.1) < 1e-12


def test_ai_025():
    w = make_weights(w_ai=0.25)
    assert abs(w.w_grade - 0.75 / 2.1) < 1e-12
    assert abs(w.w_lower - 1.1 * w.w_grade) < 1e-12
