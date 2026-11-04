import json
from pathlib import Path

from problem_time.pipeline import demo_with_outlier, main, run_demo, score_problem_dict


def test_demo_runs():
    out = run_demo()
    assert "clean_case" in out and "outlier_case" in out
    assert out["outlier_case"]["reports"][0]["clean"]["triggered"] is True


def test_sample_json(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    sample = root / "examples" / "sample_problem.json"
    data = json.loads(sample.read_text(encoding="utf-8"))
    result = score_problem_dict(data)
    assert result["tau"] > 0
    assert result["relative"]["T_grade"] == 1.0


def test_cli_demo(capsys):
    assert main(["--demo"]) == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert "set_tau" in payload


def test_outlier_payload_triggers_ai_clean():
    result = score_problem_dict(demo_with_outlier())
    ai_report = next(r for r in result["reports"] if r["name"] == "ai")
    assert ai_report["clean"]["triggered"] is True
