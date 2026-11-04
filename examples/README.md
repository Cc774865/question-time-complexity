# 例子

计分结果索引见 [`docs/样本参考.md`](../docs/样本参考.md)。

- `benchmark_7papers_2to8star.json`：7 套 98 题的刻度对照。星级均值严格递增，新题不拿它当拟合目标。
- `W3-L5L6-4-stem-summary.json`、`W3-L7L8L9-4-stem-summary.json`：不看星级算出的两套应用卷。
- `W5-L3L4-7/`、`W9-zkcc-18/`：早期提取稿，以及按解析句号数步的校准报告，用来对照旧计数为何失真。
- `sample_problem.json`：三因子原始秒数的演示输入，与四维计数无关。
- `W5-L3L4-7.docx`：竖式卷原件，供 `scripts/extract_docx.py` 试抽。
