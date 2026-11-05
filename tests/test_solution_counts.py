from problem_time.calibration import score_calibrated_problem
from problem_time.solution_counts import solution_counts

_MEDIAN = """解：∵AD是三角形ABC的中线，
∴BD=CD，
又∵ED=AD，∠BDE=∠CDA，
∴SAS，
∴BE=AC=5，
在三角形ABE中，∵AB-BE<AE<AB+BE，
∴8-5<2AD<8+5，
∴1.5<AD<6.5"""


def test_the_median_solution_matches_the_rule_file() -> None:
    counts = solution_counts(_MEDIAN, "倍长中线法")
    assert counts.prereq == 3.5
    assert counts.reasoning == 4
    assert counts.compute == 2.4
    assert counts.error == 1.5
    scored = score_calibrated_problem("median", "倍长中线", counts)
    assert round(scored["tau"], 5) == 0.92159
