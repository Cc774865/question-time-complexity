---
name: question-time-complexity
description: Installs this repository into Cursor and opens the 题目分档 UI, then scores math question files into one docx. Use when the user pastes https://github.com/Cc774865/question-time-complexity.git, asks to copy or install this repository into Cursor, asks to open the UI, or sends a Word paper for time complexity τ, 星级, 作业题, or 晋级赛.
---

# 题目时间复杂度（四维结构校准 × 三因子加权）

把每一道数学题做成可复核的时间复杂度 τ。题目顺序不是特征；解析文字长短不是特征；星级标签不是特征；同一题面数学结构必须得到相同结果。

## 打开界面

用户要求安装本仓库、粘贴仓库地址，或要使用题目分档界面时，先做完下面几步，再做别的：

1. 仓库放在 Cursor 个人技能目录的 `question-time-complexity`。Windows 是 `%USERPROFILE%\.cursor\skills\question-time-complexity`，macOS 和 Linux 是 `~/.cursor/skills/question-time-complexity`。不在那里就执行 `git clone https://github.com/Cc774865/question-time-complexity.git` 到这个路径。已经在那里就 `git pull`。
2. 在该目录执行 `python -m pip install -r requirements.txt`。
3. 界面没在跑时，于该目录后台执行 `python scripts/serve_ui.py`。脚本会打开浏览器。已经在跑时再执行一次，只打开浏览器。
4. 把脚本打印的地址告诉用户。界面只有输入、输出、人工审核，不要把计算方法写上去。输入区有「开始工作」。用户点下去之后，页面自己调用 `problem_time.run_paper.run_started` 计算 2–8 星，并立刻写出 `inbox/preview.docx`。2–8 星显示在输出下面。拖拽只改顺序。输出区的提交每点一次写出 `预览(n).docx`，n 是这个按钮的点击次数。人工审核只选班型。点人工审核的提交才把生产文档写到 `inbox/output.docx`，下载名是 `{周次}-{年级}-{课次}-生产.docx`。给人看的步骤在 `docs/使用说明.md`。

输出 docx 从输入原件复制。题目、答案、解析里的文字和图片原样保留。能改的只有星级标题、班级标题和题目顺序。题干数字若在图片里，用输入区保存的 DeepSeek API 调用 `deepseek-flash` 只做转写，转写只进入计分，不写进 docx。图或公式图片读不出数字时，改读这道题的解析，按 `docs/图形题按解析计分.md` 计四个维度，再按原来的排序写 2–8 星；还原出来的式子只进入计分，不写进 docx。用 `problem_time.arrange_docx.arrange_docx` 写到 `inbox/output.docx`，再写 `inbox/result.json`（`filename`、`copied: true`、`bytes`、`source`、`base`、`review`）。不要自己重写解析。

输出模块先给出预览文档。它下面是正课 2–8 星，按系统排出的顺序从上到下排列。拖拽改变顺序，最上面是 2 星，往下依次加 1，这一步不写新文件。输出区的提交按当前顺序写出下一份预览，文件名是 `{周次}-{年级}-{课次}-预览(n).docx`，n 从 1 起，等于这个按钮点过的次数。预览里的作业题和晋级题标题保持原稿。人工审核不收审核意见，也不排星级。每题只有一个班型：B、A、AA、AAA、S。点人工审核的提交才生成生产文档，下载名是 `{周次}-{年级}-{课次}-生产.docx`。作业题标题只写成 `{班型}-作业题`，晋级题标题写成 `{班型}-晋级题`，不另改星级。`review` 每项写 `kind`、`group`（`homework` 或 `promotion`）、`block`、`level`、`text`。

工作时把进度写到 `inbox/progress.json`：`running`、`percent`（0–100）、`label`（当前这一步的短句）。界面上的进度条读这个文件。写完 `result.json` 时把 `percent` 设为 100、`running` 设为 false。

用户在界面里选的文件存在仓库的 `inbox/`。处理这些文件时按下面的步骤。算完后把一个 JSON 写到 `inbox/result.json`，界面会自己出现一个 docx 下载。页面只自动判定正课的 2–8 星。作业题和晋级题不自动归班，全部进 `review`。人选完班型并点提交之后，才写 `inbox/output.docx`。提交之前不要出这个文件。JSON 形如：`header`（`week`、`grade`、`lesson`）、`lessons`（`star`、`role`、`prompt`、`answer`、`analysis`、`steps`、`method`）。输入 docx 里有作业题才写 `homework`（`level`、`star`、`prompt`、`answer`、`analysis`），有晋级题才写 `promotion`（`star`、`type`、`prompt`、`answer`、`analysis`）。没有的那一块不要写进 JSON，也不要写进 docx。`review`（`kind`、`text`）只在有题被抽出时才写。

计分前先读本仓库的 `docs/计算方法.md`（推导、权重、手算例）。题目文件的版式见 `docs/题目导入模板.md`，原件在 `templates/题目导入模板.docx`。甄别细则与对照表在 `spec/type-rules.md`，样本索引在 `docs/样本参考.md`。知识块名称查 `knowledge/`。运行代码时 `PYTHONPATH=src`。

## 先做全量题目清单，后计算

1. 读题之前先认「使用年级」。输入文件只在这一栏标明适用对象，调用 `problem_time.grade_use.read_grade_use`。`L3L4` 是 3年级、4年级共同使用，`L3` 是 3年级使用，`L5` 是 5年级使用，`L7L8L9` 是 7年级、8年级、9年级共同使用；几个 `L` 加数字连写就是这些年级共同使用。`ZKCC` 是中考冲刺，`GKCC` 是高考冲刺。认不出来就停，不开始读题。
2. 题目文件按 `docs/题目导入模板.md` 来认：课头是周次、使用年级、课次；正课是 `N星-例` / `N星-练`。作业题和晋级题只在同一份输入 docx 里出现时才读，调用 `problem_time.paper_sections.paper_sections`。没有作业题标题就不读作业题，没有「晋级题」就不读晋级题，输出里也不写缺的那一块。模板 docx 里的算式只是版式示范，不拿来计分。标题里的 `N` 和晋级题的「星级」栏都不读。
3. 运行 `python scripts/extract_docx.py <文件.docx>`，保存原始段落、表格、图片数。
   - 若文档含 Word 公式（`<m:oMath>`）、MathType OLE（`word/embeddings/oleObject*.bin`）或题干图片，必须一并解码或读图。参考 `examples/W9-zkcc-18/build_calibration_input.py`。只读纯文本会漏掉分数、根号、角符号或整道题干。
4. 建立题目清单。每题必须有：
   - `source_index`：原文件位置，只作追溯，不参与计分；
   - `content_hash`：规范化题干 SHA-256 前 16 位；
   - 完整题干转写、四维计数 `(P, R, C, E)` 和一句结构证据。
5. 核对 `detected = scored + blocked`。题干缺失则记 `blocked`。图里读不出数字时按 `docs/图形题按解析计分.md` 用解析计分；解析也读不出来则记 `blocked` 并写明原因，不得臆造分数。
6. 结果按 `content_hash` 或规范化题干排序。打乱清单重算，逐题 τ 与整套 τ 必须相同。

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
4. 正课例题和练题的星级。每一对先合成 \(\tau_{\text{套}}\)：差小于 0.03 取平均，差达到 0.03 取较高的 τ。全卷 τ 最低的那一道题，不论例题还是练题，所在的一套标 2 星。其余各套按 \(\tau_{\text{套}}\) 从小到大标 3 到 8 星。调用 `problem_time.stars.assign_stars`。
5. 输入 docx 里有作业题或晋级题时，才在 2–8 星分配完成之后判断它们。没有的那一块不读、不调用 `assign_levels`、不写进 `inbox/result.json` 和输出 docx。有的那一块先与各星例题、练题比内容相似度，最像哪一星就归那一星所在的班：2 或 3→B，4→A，5→AA，6→AAA，7 或 8→S。班的窗口写死为 B(2,3)、A(3,4)、AA(4,5)、AAA(5,6)、S(7,8)。共用星归把它当作上沿的班。作业题和晋级题不自动归班，全部交给人工审核。人选完班型并提交后才写输出文件。晋级赛没有 S，最像 7 星或 8 星时不改判。分配完成之前禁止调用 `assign_levels`，禁止用 τ 选择等级。

以后拿到的题目模板不再带星级。τ 的计算只依赖题面结构和知识库，不需要、也不接受星级作为输入。星级只在 τ 算完后按上一款写回。
