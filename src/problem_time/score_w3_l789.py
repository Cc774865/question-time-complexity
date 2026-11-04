"""Score W3-L7L8L9-4-stem (14 questions) with the 4-dimension τ formula.

Counts come from each stem's mathematical structure. Star labels are display-only.
Order is shuffled to prove the set τ does not depend on document order.
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

from problem_time.calibration import FourDimCounts, score_calibrated_problem
from problem_time.score import aggregate_set

# (source_index, label, star_for_display_only, role, stem, FourDimCounts)
ITEMS = [
    (1, "2星-例", 2, "例",
     "声音速度 v=331+0.6t，求 t=2 与 t=30 时的速度",
     FourDimCounts(1.5, 2.0, 3.2, 0.5,
                   "代数式求值直接代入两次；0.6×2 与 0.6×30 各一次小数乘加；小数点一位")),
    (2, "2星-练", 2, "练",
     "烤制时间 t=10x+10，x=5.5，求 t",
     FourDimCounts(1.5, 1.0, 2.0, 0.5,
                   "同一求值结构只代入一次；10×5.5+10 两步，含一位小数")),
    (3, "3星-例", 3, "例",
     "a、b 互为相反数，c、d 互为倒数，|m|=2，求 (a+b)^2+2m-3cd",
     FourDimCounts(4.0, 4.5, 3.2, 2.0,
                   "相反数、倒数、绝对值三块+分类；平方与两支代入；漏负支和 -3cd 变号")),
    (4, "3星-练", 3, "练",
     "a、b 互为相反数，c、d 互为倒数，|m|=3，求 m+2(a+b)-cd",
     FourDimCounts(4.0, 4.0, 2.4, 1.5,
                   "同上三块+绝对值两支，式子无平方，负支仍须保留")),
    (5, "4星-例", 4, "例",
     "2x-y-1=0，求 3ky-6kx+3k（四选一，含与 k 有关）",
     FourDimCounts(4.0, 4.5, 2.0, 2.5,
                   "移项得 2x-y=1，逆向提公因式成 -3k(2x-y)+3k 再整体代入；k 消去，D 项是干扰")),
    (6, "4星-练", 4, "练",
     "x^2+x+3=7，求 -2x^2-2x+2026",
     FourDimCounts(3.0, 3.5, 2.5, 1.5,
                   "移出 x^2+x=4，提 -2 后整体代入；四位数减 8；勿解出 x")),
    (7, "5星-例", 5, "例",
     "由 2^2-1^2=3 等归纳第 n 式，求 1+3+5+…+2017",
     FourDimCounts(4.5, 7.5, 1.5, 2.5,
                   "归纳 (n+1)^2-n^2=2n+1，裂项成平方；下标错一位与末项 1008^2/1009^2 两处陷阱")),
    (8, "5星-练", 5, "练",
     "由 3^2-1^2=8 等归纳第 n 式，求 8+16+…+800",
     FourDimCounts(4.5, 8.0, 2.5, 2.5,
                   "通项 (2n+1)^2-(2n-1)^2=8n，再按 1..100 求和；下标、系数 4n、100^2 三个选项陷阱")),
    (9, "6星-例", 6, "例",
     "三角点阵：6、10、15 个点，求第 7 个图的点数",
     FourDimCounts(3.0, 5.5, 1.5, 1.5,
                   "图中行数=序号+2，点数为 1+…+(n+2)；n=7 时 1..9 求和；少计一行得 36")),
    (10, "6星-练", 6, "练",
     "正方形点阵：4、9、16，求第 7 个图的正方形数",
     FourDimCounts(3.0, 4.0, 1.0, 1.5,
                   "观察为 (n+1)^2，n=7 得 64；下标偏成 n^2 或 (n+2)^2")),
    (11, "7星-例", 7, "例",
     "x-3/2025=(4/2025)x+(3/2025)b 的解为 x=-2，求另一关于 y 的方程的解",
     FourDimCounts(4.5, 7.5, 2.0, 3.0,
                   "把 y 方程收成 (1-y) 再乘 -1，使 y-1 对齐 x；勿解 b；变号与整体差 1")),
    (12, "7星-练", 7, "练",
     "2x-3/2023=(5/2023)x+(3/2023)b 的解为 x=4，求另一关于 y 的方程的解",
     FourDimCounts(4.5, 8.0, 2.0, 3.0,
                   "同例，且须先把 2-2y 收成 2(1-y) 才能与 2x 对齐")),
    (13, "8星-例", 8, "例",
     "(1+1/2+…+1/2014)(1/2+…+1/2015)-(1/2+…+1/2014)(1+1/2+…+1/2015)",
     FourDimCounts(5.0, 7.0, 1.0, 3.0,
                   "设两段和 a、b，展开相消得 a-b=1/2015；逐项通分不可行，端点切错则消不掉")),
    (14, "8星-练", 8, "练",
     "(1+1/2+1/3)(1/2+1/3+1/4)-(1/2+1/3)(1+1/2+1/3+1/4)",
     FourDimCounts(4.5, 6.0, 1.0, 2.0,
                   "同一换元相消，项短，硬算仍可行，端点设反的代价更小")),
]


def _hash(stem: str) -> str:
    return hashlib.sha256(stem.encode("utf-8")).hexdigest()[:16]


def _score(rows: list[tuple]) -> list[dict]:
    return [
        score_calibrated_problem(label, stem, counts, star=star, role=role)
        for _idx, label, star, role, stem, counts in rows
    ]


def main() -> None:
    scored = _score(ITEMS)
    for row, record in zip(ITEMS, scored):
        record["source_index"] = row[0]
        record["content_hash"] = _hash(row[4])
    results = [record.pop("_result") for record in scored]
    forward_tau = aggregate_set(results)

    shuffled = list(ITEMS)
    random.seed(2026)
    random.shuffle(shuffled)
    shuffled_scored = _score(shuffled)
    shuffled_tau = aggregate_set([record.pop("_result") for record in shuffled_scored])
    by_id = {record["problem_id"]: record["tau"] for record in scored}
    shuffled_match = all(abs(by_id[record["problem_id"]] - record["tau"]) < 1e-12 for record in shuffled_scored)

    by_star: dict[int, list[float]] = {}
    for record in scored:
        by_star.setdefault(record["star"], []).append(record["tau"])
    star_means = {star: sum(vals) / len(vals) for star, vals in sorted(by_star.items())}
    stars = list(star_means)
    mono = all(star_means[stars[i]] < star_means[stars[i + 1]] for i in range(len(stars) - 1))

    out = {
        "source": "W3-L7L8L9-4-stem",
        "grade": "L7L8L9",
        "formula": "type-rules-v3-four-dimension",
        "detected_question_count": len(ITEMS),
        "scored_count": len(scored),
        "blocked_count": 0,
        "question_count": len(scored),
        "set_tau": round(forward_tau, 6),
        "shuffled_set_tau": round(shuffled_tau, 6),
        "order_invariant": abs(forward_tau - shuffled_tau) < 1e-12 and shuffled_match,
        "shuffled_order": [row[1] for row in shuffled],
        "star_mean_tau": {str(k): round(v, 6) for k, v in star_means.items()},
        "star_mean_monotonic": mono,
        "problems": scored,
    }
    dest = Path(__file__).resolve().parents[2] / "examples" / "W3-L7L8L9-4-stem-summary.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"detected={len(ITEMS)} scored={len(scored)} blocked=0")
    print(f"整套 τ = {forward_tau:.6f}  (打乱后 {shuffled_tau:.6f}, 单题也一致={shuffled_match})")
    print("打乱顺序:", " → ".join(row[1] for row in shuffled))
    print(f"{'题目':<10} {'P':>4} {'R':>4} {'C':>4} {'E':>4} {'D':>6} {'t_g':>7} {'rAI':>7} {'r低':>7} {'τ':>8}")
    for record in scored:
        counts = record["counts"]
        print(
            f"{record['problem_id']:<10} {counts['prereq']:4.1f} {counts['reasoning']:4.1f} "
            f"{counts['compute']:4.1f} {counts['error']:4.1f} {record['composite_D']:6.2f} "
            f"{record['t_g']:7.1f} {record['r_AI']:7.4f} {record['r_lower']:7.4f} {record['tau']:8.6f}"
        )
    print("星级均值 τ:", {k: round(v, 4) for k, v in star_means.items()}, "单调=" + str(mono))


if __name__ == "__main__":
    main()
