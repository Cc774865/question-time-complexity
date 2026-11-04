# 题目时间复杂度 τ

独立项目：按题面数学结构估计一道数学题的相对时间指标 τ。小学、初中、高中都能计。文档顺序、解析字数都不进入公式。星级标签也不进入公式——以后拿到的模板不再带星级。

计算过程的正本是 [`docs/计算方法.md`](docs/计算方法.md)。甄别细则与对照表在 [`spec/type-rules.md`](spec/type-rules.md)。样本索引在 [`docs/样本参考.md`](docs/样本参考.md)。

## 指标

1. 四维结构计数 \((P, R, C, E)\)：前置深度、推理链、计算复杂度、易错点。
2. 综合分 \(D\in[0,100]\)，本题年级中心秒数 \(t_g=18+8P+12R+8C+10E\)。
3. 相对倍率随 \(D\) 升高：AI 没那么快，低一年级更慢。
4. 十组确定性样本取几何平均，中位数相对偏差 ≥ 25% 时去掉最低和最高各一个。
5. 三因子权重 \(w_{\mathrm{AI}}=1/3\)，\(w_{g-1}=1.1\,w_g\)，三者之和为 1。
6. \(\tau=w_{\mathrm{AI}}T_{\mathrm{AI}}+w_{g-1}T_{g-1}+w_g\)。整套 τ 是各题 τ 的算术平均，与题目顺序无关。

在确定性样本上可以手算：

\[
\tau=\frac13 r_{\mathrm{AI}}(D)+\frac{22}{63}r_{g-1}(D)+\frac{20}{63}
\]

## 目录

```text
├── SKILL.md                 # Cursor 技能入口
├── docs/计算方法.md          # 公式、计数规则、手算例
├── docs/样本参考.md
├── spec/type-rules.md
├── scripts/extract_docx.py  # Word 段落 / 表格 / 图片清单
├── src/problem_time/        # 聚合、清洗、四维计分
├── knowledge/               # 870 知识点、1459 条先修、752 条课标
├── references/cmath/        # CMATH 题面参考（无耗时）
├── examples/                # 7 套刻度卷 + 两套不看星级的应用卷
└── tests/
```

## 运行

```bash
python -m venv .venv
pip install -r requirements.txt
# Windows PowerShell:
$env:PYTHONPATH = "src"
python -m pytest -q
python -m problem_time.pipeline --demo
python -m problem_time.benchmark_2to8
```

给一道题计分：

```python
from problem_time.calibration import FourDimCounts, score_calibrated_problem

record = score_calibrated_problem(
    "题号",
    "题干",
    FourDimCounts(1.5, 1.0, 2.0, 0.5, "公式已给，代入一次"),
)
print(record["tau"])
```

Word 里若有 OMML 或 MathType 公式，先看 `examples/W9-zkcc-18/build_calibration_input.py`，不要只读纯文本段落。

## 知识库与样本

- `knowledge/`：给前置深度命名。先修链不重复加进 \(P\)。来源说明见 `knowledge/README.md`。
- `references/cmath/`：1–6 年级题面，CC BY 4.0，没有作答秒数。
- `examples/benchmark_7papers_2to8star.json`：98 题结构计数结果。
- `examples/W3-L5L6-4-stem-summary.json`、`examples/W3-L7L8L9-4-stem-summary.json`：两套应用卷的结构计数结果。
