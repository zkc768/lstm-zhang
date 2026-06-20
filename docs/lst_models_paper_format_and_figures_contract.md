# lst_models 论文格式与图表合同 (文档 A — 稳定规则)
<!-- CONTRACT_VERSION: v1.2 / 2026-06-20 -->
<!-- v1.2 变更: Table 2 来源对齐 claims ledger v1.12: Stage 05 本地派生核验优先,
     upstream raw v2_1_decision_record.json 仍为 Drive-only provenance。 -->
<!-- CONTRACT_VERSION: v1.1 / 2026-06-20 -->
<!-- v1.1 变更: 统一引用流为 paper/references.bib, 加入 claim_id/estimand/source
     数字门, 修正双盲 grep checklist, 并要求图表数字绑定 exact artifact root/run id;
     §3 图表映射同步 Doc B v1.2: Fig 3=校准+风险覆盖, Fig 4=跨期条件图谱。 -->
<!-- 状态: 已用户确认 (2026-06-11)。任何图表制作、LaTeX 排版、投稿前检查任务
     必须先读本合同。叙事与章节内容规则见文档 B
     (lst_models_paper_narrative_and_template_papers_guide.md),
     语言与翻译规则见翻译防漂移指南。 -->

适用范围: 论文的 LaTeX 工程、图、表、caption、双盲合规、投稿打包。
本合同记录的是"格式怎么做"的稳定规则; "内容写什么"在文档 B。

## 1. 目标格式 (按 ICAIF 真实规则锁定)

目标 venue: ACM ICAIF (AI in Finance) 风格的 ACM 会议投稿。
ICAIF '25/'26 官方规则 (两届一致, 已核实):

- **8 页总长上限, 双栏 sigconf 格式, 图表和参考文献全部计入**。
  超长直接拒稿不送审。
- **不接受任何附录或补充材料**, 论文必须自含。
- 双盲评审: 不得以任何方式暴露作者身份, 包括引用自己旧工作的方式。
- LaTeX 优先, 使用 ACM 模板 sigconf 文档类 + anonymous 选项。
- 经 CMT 提交, PDF 格式。
- ICAIF '26 (米兰) 截稿: 2026-08-02。
- 同一作者最多 6 篇投稿; 不接受一稿多投/已发表工作。

若最终改投其他 ACM venue, 只调本节参数 (页数/截稿), 其余规则不变。

## 2. LaTeX 工程规范

```latex
% 投稿版 (双盲, 双栏)
\documentclass[sigconf,review,anonymous]{acmart}
% 录用后终稿
\documentclass[sigconf]{acmart}
```

- 写作介质: 中间稿 Markdown (按翻译指南三遍流程产出), 终稿 LaTeX。
  用户提供的 ACM Word 模板仅作为"必备件清单"参照, 不用 Word 写作。
- 必备件 (从 ACM 官方模板提取): Title / ShortTitle (页眉用) /
  Abstract / CCS Concepts / Keywords / ACM Reference Format (模板
  自动生成) / 正文 / 致谢 (投稿版删除) / GenAI 使用声明 / References。
- 宏包白名单: booktabs, graphicx, siunitx (数字对齐), amsmath。
  自定义宏 ≤ 10 个, 集中放导言区并加注释; 不引入 tikz 内联画图
  (图一律外部 PDF)。
- 引用: BibTeX + acmart 默认 ACM-Reference-Format 样式;
  论文唯一 BibTeX 入口是 `paper/references.bib`。新增条目必须先进入
  `paper/references.bib`, 且带 KB、用户批准或 publisher/source provenance;
  不得从 skill 输出、网页搜索结果或模型记忆直接写 `\cite{}`。
- 交叉引用一律 `\ref`/`\autoref`, 禁止手写 "Figure 3" 字面量。
- LaTeX 源码遵守 Leey21 规则: 正文不用加粗/斜体强调, 特殊字符转义,
  公式 $ 包围, 不用 \item 列表化论证段。
- 论文工程目录 (本地, 不进 GitHub):

```text
paper/
├── main.tex            ← sigconf 主文件
├── sections/*.tex      ← 每节一个文件
├── figures/*.pdf       ← 最终矢量图
├── scripts/            ← 图表生成脚本 (读 artifacts/, 输出 figures/)
├── references.bib
└── outline_and_claims.md (claims ledger, 文档 B 管辖)
```

  说明: paper/ 是本地论文工作区, 加入 .gitignore; AGENTS.md 的
  src/ 代码放置门不适用于 paper/scripts/ (它们是论文资产, 不是
  项目研究代码), 但研究安全规则 (不碰 holdout、不伪造数字) 仍适用。

## 3. 浮动体配额 (由 8 页硬上限倒推)

8 页含参考文献 → 正文约 7.0 页 + 文献约 1.0 页。
浮动体 (图+表) 总占页预算 **≤ 1.8 页**, 数量预算:

- **图 ≤ 4 张** (多面板图算 1 张, 优先用多面板省配额)
- **表 ≤ 4 张**
- 合计目标 7 个浮动体, 硬上限 8 个。

### 论文图的取舍映射 (与 Doc B v1.2 对齐)

| 现有产物 | 处理 | 进论文形态 |
|---|---|---|
| (无) | 新制 | Fig 1: 评估协议/管线示意图 (主贡献节配图, 必须有) |
| fig_06_model_metric_comparison + V2.1 guarded comparison artifacts | 重制为双面板 | Fig 2: 主结果 vs same-row stratified dummy (validation / guarded 分面; 各面板各自 dummy 地板线; 不跨域并置) |
| fig_03_reliability_equal_mass_10bin + fig_04_selective_risk_coverage | 合并重制为双面板 | Fig 3: 校准 + 风险-覆盖诊断; caption 必写 risk-coverage is accuracy-based, no cost model, no operating point selected |
| fig_05_activity_tercile_delta + `artifacts/05_guarded_activity_tercile/` | 重制为跨期双面板 | Fig 4: 条件图谱 (validation / guarded activity-tercile delta); caption 必写 activity = eligible-row-count / no-trade-band proxy, not volume/liquidity/volatility; high<random is limitation |
| fig_01_validation_delta_by_ticker | 降级 | 并入 Fig 2 小面板/正文, 或超配额时砍 |
| fig_02_train_inner_ablation_delta | 转表/正文 | 并入 Table 3 子块或正文; control-row only, non full-family |

### 表配额分配

| 表 | 内容 | 数据来源 |
|---|---|---|
| Table 1 | 数据集与切分统计 (ticker 数/样本量/时间边界/标签分布) | stage00 manifests |
| Table 2 | 主结果: official-validation 与 guarded 域分块标注, mean ± std (n seeds), 含 stratified dummy 行 | `artifacts/05_thesis_synthesis/20260619_090454_562658/05_thesis_synthesis_report.json` + `05_estimand_contrast.csv` + `05_validation_budget_ledger.csv`; upstream raw `v2_1_decision_record.json` remains Drive-only provenance |
| Table 3 | 稳健性/折扣合并: 多重性 per-family mean+period-LCB+PBO+min_family_lcb, 四估计量对照, LOO, 基率 | `artifacts/05_thesis_synthesis/20260619_090454_562658/` + `artifacts/05_row_pooled_multiplicity/` + `artifacts/05_row_pooled_loo/` + `artifacts/05_guarded_base_rates/` |
| Table 4 | 条件/选择性摘要: 活跃度三分位 delta, e-AURC/AUGRC/ECE/Brier-resolution, label-shuffle sentinel pass; 空间紧时并入 Fig 4 图注/正文 | `artifacts/05_guarded_activity_tercile/` + `artifacts/05_guarded_base_rates/` + `artifacts/05_label_shuffle_sentinel/` + ledger-bound `artifacts/05_thesis_synthesis/20260619_090454_562658/` selective/autopsy outputs |

超配额裁剪顺序 (没有附录可塞, 砍 = 真删):
① fig_01 per-ticker 面板 → ② train-inner ablation 压到正文 →
③ Table 4 并入 Fig 4 图注/正文 →
④ 仍超额时, Fig 3/Fig 4 才可合成一张四面板 diagnostics figure, 但必须保留各自 caption 红线。

图 3/4 红线: Fig 3 不得写 "well-calibrated"; calibration 只能写 small ECE with near-zero
resolution, risk-coverage 只能写 accuracy-based diagnostic, no cost model, no operating point.
Fig 4 的 activity 是 eligible-row-count / no-trade-band proxy, 不是 volume/liquidity/volatility;
validation 与 guarded 必须分面/分域标注; high<random 是限定和风险, 不是正边际。

## 4. 图规范 (matplotlib 统一)

所有论文图由 paper/scripts/ 下脚本从 artifacts/ 数据重新生成,
禁止手工截图或复用旧 notebook 输出 (可复现性 + 风格统一)。
每个图表脚本在运行前必须记录 exact artifact root/run id, 输入文件名,
输入字段, sha256 或对应 `SHA256SUMS.txt` 行, 以及 claims ledger
`claim_id`。禁止从 `artifacts/` 或 Drive 父目录扫描 "latest"。

统一 rcParams (写进共享的 paper/scripts/style.py):

```python
FIG_WIDTH_1COL = 3.33   # inch, sigconf \columnwidth
FIG_WIDTH_2COL = 7.00   # inch, sigconf \textwidth
rcParams.update({
    "figure.dpi": 300, "savefig.format": "pdf",
    "font.size": 8, "axes.labelsize": 8, "axes.titlesize": 8,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.3, "grid.linewidth": 0.4,
    "lines.linewidth": 1.2, "pdf.fonttype": 42,  # 嵌入 TrueType
})
```

- 色板: Okabe-Ito 色盲安全色板, 模型→颜色全文固定映射
  (同一模型在所有图中同色); 灰度打印仍可区分 (线型/标记辅助区分)。
- 最终排版尺寸下文字 ≥ 7pt; 图内不放标题 (信息进 caption);
  图内不用阴影、渐变、3D 效果。
- 模型/指标名称与术语表 (翻译指南第 7 节) 完全一致,
  图例顺序 = 表格行顺序 = 正文首次提及顺序。
- 输出 PDF 矢量; 位图仅限热力图类, ≥300 dpi。
- 每图 LaTeX 侧必填 `\Description{一句话纯文本描述}` (ACM 无障碍
  硬性要求, 缺失视为格式不合格)。

## 5. 表规范

- booktabs 三线表 (\toprule \midrule \bottomrule), **无竖线**。
- 数字右对齐 (siunitx S 列), 文本左对齐; 同列同精度。
- 指标精度统一: 比率类指标 (accuracy/F1/coverage) 一律百分数
  1 位小数 (如 41.7); 差值用百分点 (pp); 不混用小数/百分比两种写法。
- 多种子结果一律 mean ± std 并在表注写明 n (seeds);
  禁止报裸均值 (AGENTS.md dummy 基线与多种子文化)。
- **每张模型指标表必须含 stratified dummy baseline 行** (同一目标行,
  同一指标), 这是项目红线在论文里的投影。
- 最优结果加粗; 加粗判定写在表注 (如 "best per column in bold");
  若差异在 std 内不加粗, 注明。
- 表头单位放列名 (如 BAcc (%)), 不在单元格里重复。
- 表内数字必须能追溯到 claims ledger 的 `claim_id`, `evidence_domain`,
  `estimand`, `weight_unit`, exact artifact root/run id, 以及 artifacts/
  的确切 CSV/JSON 字段; 禁止手敲无来源数字。

## 6. Caption 写法 (图表通用)

- 第一句: 现在时陈述图/表显示什么 (Table 2 reports validation
  balanced accuracy per model family ...)。
- 第二句起: 读法或关键 takeaway (一条即可), 不复述正文论证。
- caption 自含: 不看正文能看懂缩写与设置 (首次缩写在 caption 内
  展开或避免)。
- 图 caption 末尾不写 "see text for details"。
- 语言规则 (词汇/句长) 与正文同标准, 过翻译指南 grep 门。

## 7. 双盲合规门 (投稿前强制 grep)

门语义分两类:

- 门 1/2 (身份泄露): **任何时点**都必须零命中, 包括源码注释
  (注释虽不进 PDF, 但身份串不允许存在于论文工程内)。
- 门 3/4 (致谢与 skeleton 痕迹): 投稿构建门, 在**去注释副本**上
  运行 (PDF 泄露才是风险, 草稿期注释里的工作标记是合法状态)。

```bash
# 门 1/2: 全源文件, 含注释 (期望: 永远零命中)
grep -rniE "zkc768|lstm-zhang|kevinzhang|gmail|154SlcH3nViUcvPXFBM|google drive|colab" paper/ --include="*.tex" --include="*.bib"
grep -rniE "our (previous|prior|earlier) (work|paper|study)" paper/ --include="*.tex"

# 门 3/4: 去注释后检查会打进 PDF 的内容 (投稿构建时期望零命中)
for f in paper/main.tex paper/sections/*.tex; do
  sed 's/\([^\\]\)%.*/\1/; s/^%.*//' "$f" | grep -niE "acknowledg|funded by|thanks to|\\\\titlenote|\\\\thanks|outline_and_claims|Tier-V|working title" && echo "HIT in $f"
done
```

- 自引规则: 引用自己相关工作时用第三人称 ("X et al. proposed"),
  禁止 "we previously showed"。
- 投稿版删除致谢节; 资金/感谢信息录用后再加。
- PDF 元数据清理: 检查编译产物的 author 字段为空
  (anonymous 选项处理, 但要人工核 PDF 属性)。
- 数据声明措辞: 描述数据来源时不暴露个人 Drive/仓库路径,
  写 "minute-level bars for S&P 100 constituents" 级别的中性描述。

## 8. GenAI 使用声明 (ACM 2026 强制)

ACM 自 2026 年起要求在 Endmatter 含生成式 AI 使用声明; AI 不得
署名作者。本项目工作流大量使用 AI 辅助, 必须如实声明。模板:

```text
Generative AI Usage Statement. Generative AI tools were used to
assist with literature search, drafting and translating prose from
the authors' Chinese notes, editing for style, and generating
figure-plotting code. All experimental design, code execution,
results, and claims were produced and verified by the authors.
All AI-assisted text was reviewed, fact-checked against the
project's experiment artifacts, and revised by the authors, who
take full responsibility for the content.
```

- 该声明随论文进度如实更新 (用了什么就写什么, 不夸大不隐瞒)。
- 投稿版声明措辞保持匿名 (不暴露作者数量/机构线索)。

## 9. 数字呈现一致性

- 正文引用的每个数字与表格同源同精度 (claims ledger 给出处)。
- 每个结果数字必须绑定 `claim_id`, `evidence_domain`, `estimand`,
  `weight_unit`, `source_artifact`, exact artifact root/run id。裸写
  "the result", "the delta", "the PBO" 不合格。
- C4/C4.5 或 V2.1 结果必须标明 guarded row-pooled binding estimand
  或 guarded equal-weight companion; 不得把两者混成一个 headline。
- 百分点变化写 pp (improves balanced accuracy by 1.2 pp),
  不写含糊的 "improves by 1.2%"。
- 样本量/种子数/ticker 数首次出现给确数。
- 统计显著性: 只有做过检验才用 significant (翻译指南 Tier 3 规则);
  报告检验名与 p 值或 CI。
- 所有时间边界 (train/val/holdout 日期) 与 stage00 manifest 逐字一致。

## 10. 投稿前格式自查清单

```text
[ ] 8 页内 (含图表与文献), 无附录
[ ] sigconf + anonymous 编译通过, 无 overfull hbox 警告遗留
[ ] 图 ≤4 / 表 ≤4; 每图有 \Description; 每浮动体正文有引用
[ ] 图字号最终尺寸 ≥7pt; 色盲安全; 模型颜色全文一致
[ ] 每张指标表含 dummy 基线行; mean ± std + n seeds
[ ] caption 第一句现在时陈述内容; 自含
[ ] 双盲门 1/2 永远零命中; 门 3/4 在投稿构建去注释副本上零命中; PDF 元数据无作者
[ ] GenAI 声明在 Endmatter 且如实
[ ] CCS Concepts + Keywords 已填
[ ] 文献条目全部来自 `paper/references.bib`, 且新增条目有 provenance, 无 AI 生造引用
[ ] 数字抽查 10 个: 正文 vs 表格 vs claims ledger vs artifacts CSV/JSON 四方一致
```

## 11. 维护

- 本合同与文档 B、翻译指南构成论文三合同; 路由入口在
  docs/agent_capabilities_and_skill_routing.md。
- venue 改变时只改第 1 节参数并 +0.1 版本; 其余节是格式通则。
- 图表任务、LaTeX 任务、投稿打包任务开始前必须重读本合同
  并在工作笔记复述: "8页含全部/图≤4表≤4/dummy行必在/
  \Description必填/双盲grep零命中"。

## 参考来源

- ICAIF '25/'26 Call for Papers (8 页含图表文献、无附录、双盲、
  sigconf+anonymous、CMT、2026-08-02 截稿)
- ACM Primary Article Template (用户提供的 Word 版, 必备件与样式
  标签清单已提取) 与 ACM proceedings-template 页
- ACM 2026 开放获取与 GenAI 声明政策
- Okabe & Ito 色盲安全色板; ACM 无障碍指南 (figure description)
