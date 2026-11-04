"""Score W3-L5L6-4-stem (14 questions) with the 4-dimension τ formula.

Counts come strictly from each question's mathematical structure in the stem.
Star labels are NOT used as input. Order is shuffled to prove invariance.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from problem_time.calibration import FourDimCounts, score_calibrated_problem
from problem_time.score import aggregate_set

# (label, star_for_display_only, role, stem, FourDimCounts)
# star is kept ONLY for display; it does not enter the formula.
ITEMS = [
    ("2星-例", 2, "例",
     "看图填一填：图示同分母分数 5/9、3/9、2/9",
     FourDimCounts(1.5, 3.0, 1.0, 0.5,
                   "看图数份数写3个同分母分数，直接执行无运算")),
    ("2星-练", 2, "练",
     "看图选算式：5/8-2/8，四选一",
     FourDimCounts(2.0, 4.0, 1.5, 1.0,
                   "数总份数定分母+数涂色格+判断减法动态+四选项匹配")),
    ("3星-例", 3, "例",
     "求最小公倍数再通分：4组异分母分数",
     FourDimCounts(2.5, 4.0, 4.8, 1.0,
                   "4组各求LCM(含倍数/互质/一般关系)+扩分通分")),
    ("3星-练", 3, "练",
     "求最小公倍数再通分：3组异分母分数",
     FourDimCounts(2.5, 4.5, 3.6, 1.0,
                   "3组各求LCM(倍数/互质/质因数分解)+扩分通分")),
    ("4星-例", 4, "例",
     "分数尺选尺子：1/4+1/3，四选一",
     FourDimCounts(3.5, 5.0, 3.0, 2.0,
                   "求LCM(3,4)=12+四选项逐一核对等分份数排除4/3/7份迷惑项")),
    ("4星-练", 4, "练",
     "分数尺选尺子：4/5+1/2，四选一",
     FourDimCounts(3.5, 5.0, 3.0, 2.0,
                   "求LCM(5,2)=10+四选项逐一核对等分份数")),
    ("5星-例", 5, "例",
     "直接写出得数：4道异分母分数加减",
     FourDimCounts(2.5, 5.0, 6.0, 1.5,
                   "4题各通分加减约分，含2/3+3/2假分数处理")),
    ("5星-练", 5, "练",
     "直接写出得数：3道异分母分数加减",
     FourDimCounts(2.5, 4.5, 4.5, 1.5,
                   "3题各通分加减约分")),
    ("6星-例", 6, "例",
     "脱式计算4题：含加法交换律、减法性质、括号",
     FourDimCounts(4.0, 7.0, 6.0, 2.5,
                   "4题含通分+交换律凑整+减法性质添括号+括号内先算，需选择简算路径")),
    ("6星-练", 6, "练",
     "脱式计算2题：括号内通分+加法交换结合律",
     FourDimCounts(3.5, 6.0, 4.0, 2.0,
                   "2题含括号内通分减法+四项交换结合律分组凑整")),
    ("7星-例", 7, "例",
     "选能用1/5+1/3解决的问题：四选一，辨析分率与具体量",
     FourDimCounts(5.0, 8.0, 3.0, 3.5,
                   "4选项逐一列式辨析：含分率vs吨单位不可加、剩余×1/3动态基准、单位1直接分率相加")),
    ("7星-练", 7, "练",
     "选不能用2/5+3/7的问题：三选一，辨析面积用乘法",
     FourDimCounts(4.5, 6.0, 2.5, 3.0,
                   "3选项辨析：面积用乘法非加法、分率相加、具体量相加")),
    ("8星-例", 8, "例",
     "水渠第一天修3/8第二天修1/8，求还剩几分之几",
     FourDimCounts(3.5, 3.0, 2.0, 1.5,
                   "单位1减两个同分母分率，同分母直接减法无通分")),
    ("8星-练", 8, "练",
     "蛋糕妈妈吃1/7爸爸吃2/7，求还剩几分之几",
     FourDimCounts(3.5, 3.0, 2.0, 1.5,
                   "单位1减两个同分母分率，同分母直接减法无通分")),
]


def main() -> None:
    scored = [
        score_calibrated_problem(pid, stem, counts, role=role)
        for pid, star, role, stem, counts in ITEMS
    ]
    results = [r.pop("_result") for r in scored]

    forward_tau = aggregate_set(results)

    # shuffle to prove order invariance
    shuffled_items = list(ITEMS)
    random.seed(2026)
    random.shuffle(shuffled_items)
    shuffled_scored = [
        score_calibrated_problem(pid, stem, counts, role=role)
        for pid, star, role, stem, counts in shuffled_items
    ]
    shuffled_results = [r["_result"] for r in shuffled_scored]
    shuffled_tau = aggregate_set(shuffled_results)

    out = {
        "source": "W3-L5L6-4-stem",
        "grade": "L5L6",
        "formula": "type-rules-v3-four-dimension",
        "question_count": len(scored),
        "set_tau": round(forward_tau, 6),
        "shuffled_set_tau": round(shuffled_tau, 6),
        "order_invariant": abs(forward_tau - shuffled_tau) < 1e-12,
        "problems": scored,
    }
    dest = Path(__file__).resolve().parents[2] / "examples" / "W3-L5L6-4-stem-summary.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"整套 τ = {forward_tau:.6f}  (打乱后 {shuffled_tau:.6f}, 不变={abs(forward_tau-shuffled_tau)<1e-12})")
    print(f"{'题目':<10} {'P':>4} {'R':>4} {'C':>4} {'E':>4} {'D':>6} {'t_g':>6} {'τ':>8}")
    for r in scored:
        c = r["counts"]
        print(f"{r['problem_id']:<10} {c['prereq']:4.1f} {c['reasoning']:4.1f} {c['compute']:4.1f} {c['error']:4.1f} {r['composite_D']:6.2f} {r['t_g']:6.1f} {r['tau']:8.6f}")


if __name__ == "__main__":
    main()
