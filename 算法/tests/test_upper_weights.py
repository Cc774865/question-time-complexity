from problem_time.calibration import (
    DIMENSION_WEIGHTS,
    TAU_PER_D,
    UPPER_DIMENSION_WEIGHTS,
    FourDimCounts,
    dimension_weights_for,
    score_calibrated_problem,
    uses_upper_grade_weights,
)


def test_both_weight_sets_sum_to_one() -> None:
    for weights in (DIMENSION_WEIGHTS, UPPER_DIMENSION_WEIGHTS):
        total = sum(weights[key] for key in ("prereq", "reasoning", "compute", "error"))
        assert abs(total - 1.0) < 1e-9


def test_upper_rule_follows_the_named_audiences() -> None:
    assert dimension_weights_for("L7", (7,)) is DIMENSION_WEIGHTS
    assert dimension_weights_for("L6", (6,)) is DIMENSION_WEIGHTS
    assert dimension_weights_for("L8", (8,)) is UPPER_DIMENSION_WEIGHTS
    assert dimension_weights_for("L9", (9,)) is UPPER_DIMENSION_WEIGHTS
    assert dimension_weights_for("L7L8", (7, 8)) is UPPER_DIMENSION_WEIGHTS
    assert dimension_weights_for("ZKCC", (7, 8, 9)) is UPPER_DIMENSION_WEIGHTS
    assert dimension_weights_for("GKCC", ()) is UPPER_DIMENSION_WEIGHTS
    assert not uses_upper_grade_weights("L7", (7,))
    assert uses_upper_grade_weights("GKCC", ())


def test_full_calculation_cannot_move_one_band() -> None:
    light = score_calibrated_problem(
        "light", "stem", FourDimCounts(3.0, 4.0, 0.0, 1.0), weights=UPPER_DIMENSION_WEIGHTS
    )
    heavy = score_calibrated_problem(
        "heavy", "stem", FourDimCounts(3.0, 4.0, 10.0, 1.0), weights=UPPER_DIMENSION_WEIGHTS
    )
    assert heavy["weightRule"] == "upper"
    assert heavy["dimensionWeights"]["compute"] == 0.08
    assert heavy["dimensionWeights"]["reasoning"] == 0.48
    assert abs((heavy["tau"] - light["tau"]) - TAU_PER_D * 8.0) < 1e-9
    assert heavy["tau"] - light["tau"] < 0.030728571


def test_familiarity_gap_is_unchanged_on_the_upper_rule() -> None:
    familiar = score_calibrated_problem(
        "familiar",
        "stem",
        FourDimCounts(3.0, 4.0, 1.0, 0.5, familiarity=-1.5),
        weights=UPPER_DIMENSION_WEIGHTS,
    )["tau"]
    transformed = score_calibrated_problem(
        "transformed",
        "stem",
        FourDimCounts(3.0, 4.0, 1.0, 0.5, familiarity=1.5),
        weights=UPPER_DIMENSION_WEIGHTS,
    )["tau"]
    assert abs((transformed - familiar) - 0.030728571) < 1e-6


if __name__ == "__main__":
    test_both_weight_sets_sum_to_one()
    test_upper_rule_follows_the_named_audiences()
    test_full_calculation_cannot_move_one_band()
    test_familiarity_gap_is_unchanged_on_the_upper_rule()
