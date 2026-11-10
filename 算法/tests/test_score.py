from problem_time.pipeline import demo_payload, samples_from_dict
from problem_time.score import aggregate_set, score_problem
from problem_time.weights import make_weights


def test_tau_formula_identity():
    samples = samples_from_dict(demo_payload())
    result = score_problem(samples, w_ai=1.0 / 3.0)
    w = make_weights(w_ai=1.0 / 3.0)
    expected = (
        w.w_ai * result.relative.T_ai
        + w.w_lower * result.relative.T_lower
        + w.w_grade * 1.0
    )
    assert abs(result.tau - expected) < 1e-12
    assert result.relative.T_grade == 1.0
    assert result.provisional is False


def test_relative_scale():
    samples = samples_from_dict(demo_payload())
    result = score_problem(samples)
    # AI 约 12s，年级约 20s → T_ai < 1；下一年级约 29s → T_lower > 1
    assert result.relative.T_ai < 1.0
    assert result.relative.T_lower > 1.0


def test_aggregate_set():
    a = score_problem(samples_from_dict(demo_payload()))
    b = score_problem(samples_from_dict({**demo_payload(), "problem_id": "b"}))
    mean = aggregate_set([a, b], weights=[1.0, 1.0])
    assert abs(mean - (a.tau + b.tau) / 2) < 1e-12
