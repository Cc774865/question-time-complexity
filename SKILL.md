---
name: question-time-complexity
description: Extracts every elementary-math question from a Word (.docx) file and estimates per-question time complexity without using document order. Use whenever the user sends a Word question paper and asks for calculation time, estimated time, complexity, difficulty time, or three-factor time scoring.
---

# 题目时间复杂度

将 `.docx` 里的每一道数学题做成可复核的时间估计。题目顺序不是特征；同一题面结构必须得到相同结果。

项目实现位于 `problem-time-model/`。先读 `problem-time-model/README.md`，运行模型时使用 `PYTHONPATH=src`。

## 先做题目清单，后计算

1. 运行 `scripts/extract_docx.py <文件.docx>`，保存原始段落、表格、图片数。
2. 从“题目/答案/解析/解题方法”分段和题号抽取**题干**；答案、解析不能作为遗漏题目的理由。
3. 建立题目清单。每题必须有：
   - `source_index`：它在原文件中的位置，只作追溯；
   - `content_hash`：规范化题干的 SHA-256 前 16 位；
   - 完整题干或能唯一定位的转写；
   - 题型、结构特征、是否已计分。
4. 计分前核对：`detected_question_count == ledger_count == scored_count + blocked_count`。
   - 任何未识别、图中关键信息不可读、题干不完整的题均为 `blocked`，说明原因；**不得臆补题目或给它虚假分数**。
   - 有图片的题应逐张检查图片是否携带题干信息；仅提取 Word 段落不算完成。
5. 最终结果按 `content_hash` 或规范化题干排序，不按 Word 出现顺序排序。对清单打乱后重算一次，逐题结果与整套结果必须相同。

## 题面结构与基准时间

没有实测耗时时，结果必须标 `derived_from_question_structure`，不能写成实测或“准确耗时”。

### 竖式执行题

对每个一位数乘法逐位模拟进位，记总进位次数为 `c`、小题数为 `n`：

\[
t_g = 15n + 3c \quad \text{seconds}
\]

其中 \(g\) 是本题年级。必须把每个算式及进位数写入审计记录。

### 竖式填空 / 数字谜

从题面而非答案解析记录：

- `p`：必须推定的竖位或数字位数；
- `k`：应用所有可见约束后仍须检验的候选数；
- `r`：部分积行数。

\[
t_g=20+14p+8k+24\max(r-1,0)+12 \quad \text{seconds}
\]

20 秒为读题，14 秒/位为逆推，8 秒/候选为检验，第二行部分积加 24 秒，最后 12 秒为验证。候选数必须以代码穷举或显式算式支持，不能只照抄解析的答案。

未知题型不可套用上述公式；保留 `blocked` 或先新增并验证专用结构公式。

## 三因子与十组样本

对结构类型选固定比例（AI / 本题年级，低一年级 / 本题年级）：

| 类型 | AI | 低一年级 |
|---|---:|---:|
| 纯竖式执行 `exec` | 0.16 | 1.35 |
| 一位数填空或汉字竖式 `search1` | 0.18 | 1.45 |
| 两位数乘数、两行部分积 `search2` | 0.22 | 1.55 |

由同一题的 \(t_g\) 得：

\[
t_{\rm AI}=r_{\rm AI}t_g,\qquad
t_{g-1}=r_{g-1}t_g
\]

十组**估算**样本必须由同一组确定性倍率产生，并让倍率的几何平均归一为 1；不得用随机扰动，也不得因题号或出现顺序改变样本。

对每一因子：

\[
\tilde t=\exp\left(\frac1n\sum_{j=1}^n\ln t_j\right)
\]

同时报中位数。相对偏差 \(\left|\tilde t-\operatorname{median}\right|/\operatorname{median}\ge25\%\) 时，剔除最高、最低各一个后再取几何平均，并写入报告。

## 最终指标

\[
T_{\rm AI}=\frac{\tilde t_{\rm AI}}{\tilde t_g},\qquad
T_{g-1}=\frac{\tilde t_{g-1}}{\tilde t_g},\qquad
T_g=1
\]

\[
w_{\rm AI}=\frac13,\quad
w_g=\frac{1-w_{\rm AI}}{2.1},\quad
w_{g-1}=1.1w_g
\]

\[
\tau=w_{\rm AI}T_{\rm AI}+w_{g-1}T_{g-1}+w_g
\]

`τ` 是相对指标，不能单独作为跨题绝对耗时排名。另报：

\[
\text{grade-equivalent seconds}=\tau\tilde t_g
\]

按该值排序并给出整套总和；整套 \(\tau\) 则是题级权重的算术加权平均。

## 交付与核验

每次必须输出：

1. 题目清单、`detected / scored / blocked` 三个数量；
2. 每题：题干、结构证据、\(t_{\rm AI},t_{g-1},t_g,T_{\rm AI},T_{g-1},\tau\)、年级等效秒数、样本来源；
3. `blocked` 项及原因（若有）；禁止静默遗漏；
4. JSON 审计产物：输入题干 hash、结构特征、十组样本、结果；
5. 题序打乱的等价性检查结论。

真实的学生或模型耗时一旦可得，替换对应十组数组，保留题面特征与原估算，输出实测版和估算版的差异；不要混写。

