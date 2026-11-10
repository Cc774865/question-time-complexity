from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .score import ProblemSamples, ProblemTimeResult, aggregate_set, score_problem


def samples_from_dict(data: dict[str, Any]) -> ProblemSamples:
    """从 JSON 对象构造样本。支持 ai / lower_grade / grade 键。"""
    return ProblemSamples(
        ai=[float(x) for x in data["ai"]],
        lower_grade=[float(x) for x in data["lower_grade"]],
        grade=[float(x) for x in data["grade"]],
        problem_id=str(data.get("problem_id", data.get("id", ""))),
        weight=float(data.get("weight", 1.0)),
    )


def score_problem_dict(
    data: dict[str, Any],
    *,
    w_ai: float = 1.0 / 3.0,
    gap_threshold: float = 0.25,
) -> dict[str, Any]:
    result = score_problem(
        samples_from_dict(data),
        w_ai=w_ai,
        gap_threshold=gap_threshold,
    )
    return result.to_dict()


def load_problem_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def demo_payload() -> dict[str, Any]:
    """演示：四年级题，三类各约 10 个相对秒数样本。"""
    return {
        "problem_id": "demo-g4-01",
        "ai": [12.0, 11.5, 13.0, 12.2, 11.8, 12.5, 12.1, 11.9, 12.4, 12.0],
        "lower_grade": [28.0, 30.0, 27.5, 29.0, 31.0, 28.5, 29.5, 30.5, 27.0, 29.2],
        "grade": [20.0, 19.5, 21.0, 20.5, 19.8, 20.2, 20.0, 21.2, 19.6, 20.4],
        "weight": 1.0,
    }


def demo_with_outlier() -> dict[str, Any]:
    """故意掺一个量级错误，触发 geo vs median 清洗。"""
    base = demo_payload()
    base["problem_id"] = "demo-outlier"
    base["ai"] = [12.0, 11.5, 13.0, 12.2, 11.8, 12.5, 12.1, 11.9, 12.4, 1200.0]
    return base


def run_demo() -> dict[str, Any]:
    clean = score_problem_dict(demo_payload())
    dirty = score_problem_dict(demo_with_outlier())
    set_tau = aggregate_set(
        [
            score_problem(samples_from_dict(demo_payload())),
            score_problem(samples_from_dict(demo_with_outlier())),
        ],
        weights=[1.0, 1.0],
    )
    return {
        "clean_case": clean,
        "outlier_case": dirty,
        "set_tau": set_tau,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="做题时间模型：几何平均 + 三因子加权")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="跑内置干净样本与含异常样本对照",
    )
    parser.add_argument(
        "--json",
        type=Path,
        help="单题 JSON（含 ai / lower_grade / grade 数组）",
    )
    parser.add_argument(
        "--w-ai",
        type=float,
        default=1.0 / 3.0,
        help="AI 权重（默认 1/3）",
    )
    args = parser.parse_args(argv)

    if args.demo:
        out = run_demo()
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    if args.json:
        data = load_problem_json(args.json)
        out = score_problem_dict(data, w_ai=args.w_ai)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
