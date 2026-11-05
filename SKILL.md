---
name: question-time-complexity
description: Extracts every math question from a Word (.docx) file and estimates per-question time complexity τ without using document order. Uses the four calibration dimensions (prereq, reasoning, compute, error) plus three-factor relative-time weighting. Use whenever the user sends a Word question paper and asks for calculation time, estimated time, time complexity τ, or difficulty calibration.
---

# 题目时间复杂度（四维结构校准 × 三因子加权）

把每一道数学题做成可复核的时间复杂度 τ。题目顺序不是特征；解析文字长短不是特征；星级标签不是特征；同一题面数学结构必须得到相同结果。

计分前先读本仓库的 `docs/计算方法.md`（推导、权重、手算例）。题目文件的版式见 `docs/题目导入模板.md`，原件在 `templates/题目导入模板.docx`。甄别细则与对照表在 `spec/type-rules.md`，样本索引在 `docs/样本参考.md`。知识块名称查 `knowledge/`。运行代码时 `PYTHONPATH=src`。

## 先做全量题目清单，后计算

1. 题目文件按 `docs/题目导入模板.md` 来认：课头是周次、使用年级、课次；题目分成正课（`N星-例` / `N星-练`）、作业（`B-作业题`、`N-作业题`、`N作业题`）和晋级题。模板 docx 里的算式只是版式示范，不拿来计分。标题里的 `N` 和晋级题的「星级」栏都不读。
2. 运行 `python scripts/extract_docx.py <文件.docx>`，保存原始段落、表格、图片数。
   - 若文档含 Word 公式（`<m:oMath>`）、MathType OLE（`word/embeddings/oleObject*.bin`）或题干图片，必须一并解码或读图。参考 `examples/W9-zkcc-18/build_calibration_input.py`。只读纯文本会漏掉分数、根号、角符号或整道题干。
3. 建立题目清单。每题必须有：
   - `source_index`：原文件位置，只作追溯，不参与计分；
   - `content_hash`：规范化题干 SHA-256 前 16 位；
   - 完整题干转写、四维计数 `(P, R, C, E)` 和一句结构证据。
4. 核对 `detected = scored + blocked`。题干缺失或图中关键数字不可读则记 `blocked` 并写明原因，不得臆造分数。
5. 结果按 `content_hash` 或规范化题干排序。打乱清单重算，逐题 τ 与整套 τ 必须相同。

## 计数与公式

只数题面和必经数学结构。不数解析句号，推理链不在 6 步封顶。知识块对照 `knowledge/topics.json`，先修链不要重复加进 \(P\)。

| 维度 | 符号 | 上限 | 权重 |
|---|---|---:|---:|
| 前置深度 | \(P\) | 6 | 0.18 |
| 推理链 | \(R\) | 12 | 0.31 |
| 计算复杂度 | \(C\) | 10 | 0.25 |
| 易错点 | \(E\) | 6 | 0.26 |

\[
D=100\times(0.18\,d_P+0.31\,d_R+0.25\,d_C+0.26\,d_E)
\]

\[
t_g=18+8P+12R+8C+10E
\]

\[
r_{\mathrm{AI}}=\min(0.13+0.0027D,\,0.95),\qquad
r_{g-1}=\min(1.28+0.0072D,\,3)
\]

十组倍率 `SAMPLE_FACTORS` 的几何平均为 1。几何平均相对中位数偏差 ≥ 25% 时去掉最低、最高各一个。权重 \(w_{\mathrm{AI}}=1/3\)，\(w_{g-1}=1.1\,w_g\)。确定性样本上

\[
\tau=\frac13 r_{\mathrm{AI}}+\frac{22}{63}r_{g-1}+\frac{20}{63}
\]

调用 `problem_time.calibration.score_calibrated_problem`。不要把星级写进 `FourDimCounts`。

## 交付

1. 题目清单与 `detected / scored / blocked`。
2. 每题的 \((P,R,C,E)\)、\(D\)、\(t_g\)、\(r_{\mathrm{AI}}\)、\(r_{g-1}\)、τ 和结构证据。来源写 `derived_from_question_structure`。
3. 题序打乱后的等价性结论。
4. 正课例题和练题的星级。每一对先合成 \(\tau_{\text{套}}\)：差小于 0.03 取平均，差达到 0.03 取较高的 τ。再按 \(\tau_{\text{套}}\) 从小到大依次标 2 到 8 星。调用 `problem_time.stars.assign_stars`。
5. 2–8 星分配完成之后，才判断作业题和晋级赛。先把每道题与各星例题、练题比内容相似度，最像哪一星就归那一星所在的班：2 或 3→B，4→A，5→AA，6→AAA，7 或 8→S。班的窗口写死为 B(2,3)、A(3,4)、AA(4,5)、AAA(5,6)、S(7,8)。共用星归把它当作上沿的班。晋级赛没有 S，最像 7 星或 8 星时不改判。分配完成之前禁止调用 `assign_levels`，禁止用 τ 选择等级。

以后拿到的题目模板不再带星级。τ 的计算只依赖题面结构和知识库，不需要、也不接受星级作为输入。星级只在 τ 算完后按上一款写回。
