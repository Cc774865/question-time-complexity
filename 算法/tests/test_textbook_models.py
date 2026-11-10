from __future__ import annotations

import importlib.util
from pathlib import Path

from problem_time.calibration import FourDimCounts, score_calibrated_problem
from problem_time.run_paper import _score_block
from problem_time.structure_counts import structure_counts
from problem_time.textbook_models import (
    familiarity_for_grades,
    load_textbook_models,
    shadow_familiarity,
)


ROOT = Path(__file__).resolve().parents[1]


def test_library_covers_grades_one_through_nine() -> None:
    models = load_textbook_models()
    assert models
    assert {int(model["grade"]) for model in models} == set(range(1, 10))
    assert len({model["id"] for model in models}) == len(models) == 119


def test_shared_grade_uses_the_least_familiar_audience() -> None:
    model = next(model for model in load_textbook_models() if model["id"] == "pep-g8-pythagorean")
    assert familiarity_for_grades(model, (8,)) in {"introduced", "core"}
    assert familiarity_for_grades(model, (8, 9)) in {"introduced", "core"}
    assert familiarity_for_grades(model, (7, 8, 9)) == "out_of_scope"


def test_uncommon_transform_is_one_band_harder() -> None:
    counts = FourDimCounts(3.0, 4.0, 1.0, 0.5, "same structure counts")
    familiar = shadow_familiarity(
        "两条直线平行，求拐点处的角。",
        "过拐点作已知直线的平行线，利用内错角。",
        (7,),
        counts,
    )
    transformed = shadow_familiarity(
        "两条直线平行，动点有三种位置，需要分类讨论各拐点角。",
        "过拐点作平行线，分三种位置讨论。",
        (7,),
        counts,
    )
    assert familiar["status"] == "matched"
    assert transformed["status"] == "matched"
    assert familiar["candidates"][0]["familiarity"] == "reinforced"
    assert transformed["candidates"][0]["familiarity"] == "uncommon_transform"
    assert familiar["affectsFormalTau"] and transformed["affectsFormalTau"]
    assert familiar["structuralP"] == transformed["structuralP"] == 3.0
    assert familiar["formalF"] == -1.5
    assert transformed["formalF"] == 1.5
    familiar_tau = score_calibrated_problem(
        "familiar", "stem", FourDimCounts(3.0, 4.0, 1.0, 0.5, familiarity=familiar["formalF"])
    )["tau"]
    transformed_tau = score_calibrated_problem(
        "transformed", "stem", FourDimCounts(3.0, 4.0, 1.0, 0.5, familiarity=transformed["formalF"])
    )["tau"]
    untouched_tau = score_calibrated_problem(
        "plain", "stem", FourDimCounts(3.0, 4.0, 1.0, 0.5)
    )["tau"]
    assert abs((transformed_tau - familiar_tau) - 0.030728571) < 1e-6
    assert untouched_tau == score_calibrated_problem(
        "zero", "stem", FourDimCounts(3.0, 4.0, 1.0, 0.5, familiarity=0.0)
    )["tau"]


def test_familiarity_gap_survives_the_prereq_cap() -> None:
    familiar = score_calibrated_problem(
        "familiar", "stem", FourDimCounts(6.0, 4.0, 1.0, 0.5, familiarity=-1.5)
    )["tau"]
    transformed = score_calibrated_problem(
        "transformed", "stem", FourDimCounts(6.0, 4.0, 1.0, 0.5, familiarity=1.5)
    )["tau"]
    assert abs((transformed - familiar) - 0.030728571) < 1e-6


def test_sprint_codes_do_not_guess_a_grade() -> None:
    counts = FourDimCounts(2.0, 2.0, 1.0, 0.0)
    result = shadow_familiarity("平行线求角", "作平行线", (), counts)
    assert result["status"] == "not_applicable"
    assert result["suggestedF"] is None
    assert result["formalF"] == 0.0


def test_scoring_uses_familiarity_when_the_match_is_confident() -> None:
    stem = "两条直线平行，求拐点处的角。"
    solution = "过拐点作平行线，利用内错角。"
    scored = _score_block(0, stem, solution, "", (7,))
    untouched = _score_block(0, stem, solution)
    assert scored["familiarity_shadow"]["affectsFormalTau"] is True
    assert scored["familiarity_shadow"]["status"] == "matched"
    assert scored["tau"] < untouched["tau"]
    assert structure_counts(stem).prereq > 0


def test_library_validator_passes() -> None:
    path = ROOT / "scripts" / "validate_textbook_models.py"
    spec = importlib.util.spec_from_file_location("validate_textbook_models", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.main() == 0


if __name__ == "__main__":
    test_library_covers_grades_one_through_nine()
    test_shared_grade_uses_the_least_familiar_audience()
    test_uncommon_transform_is_one_band_harder()
    test_familiarity_gap_survives_the_prereq_cap()
    test_sprint_codes_do_not_guess_a_grade()
    test_scoring_uses_familiarity_when_the_match_is_confident()
    test_library_validator_passes()
    print("ok")
