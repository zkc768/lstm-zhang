# lst_models 论文叙事与范文指南 (文档 B — 随写作演进)
<!-- GUIDE_VERSION: v1.2 / 2026-06-20 -->
<!-- v1.2: 按本地合同主控 + ARS 辅助编排修复:
     (1) 优先级改为 AGENTS.md > claims ledger > 翻译保真;
     (2) 开工条件加入 claim_id/evidence_domain/estimand/weight_unit/source_artifact;
     (3) skill 名称对齐当前 routing doc; (4) references.bib 明确为单一引用入口;
     (5) Doc A §3 图表映射已同步到 Tier-G/Stage 05 artifact 方案。 -->
<!-- PREVIOUS_GUIDE_VERSION: v1.1 / 2026-06-19 -->
<!-- v1.1 (REWRITE; 触发: claims ledger v1.10 + 第三轮对抗审查 2026-06-19 +
     limitation register 2026-06-17 + 本次 Doc B v1.1 升级前 Phase-1 对抗审查
     [docs/v2_1_docb_v11_phase1_review_20260619.md, 14 条 change-list]):
     v1.0 (2026-06-11) 写于实验中途, 现材料性陈旧且作为起草计划不安全。本次重写
     §0/§1/§2/§3/§4/§5/§7/§8:
     (1) §1 故事线改 "guarded 评估纪律为主"; 立论换 register verbatim; 贡献改
         C1/C2/C4/C3 四块, 加 C4 guarded 读出为实证脊柱; 模型名册改
         {TCN(主), standard-DLinear, MS-DLinear+TCN, LightGBM}, 删不存在的 LSTM;
         新增"投稿红线块"(8 条) + 标题方向 + 反攻击子节。
     (2) §3 8 页蓝图重排: 加 Guarded Walk-Forward Readout 行 + Diagnostics &
         Robustness 列全 + validation-budget 表行; 行和与表头对齐; 源映射改 Stage 05
         canonical 产物 (+ 五个 addenda 目录), 不再指 ian_email tables/01-13。
     (3) §4 Tier 改三证据域 (V / control / G); Tier-G 为本路线最高可达; 删 Tier-F
         升级触发与 "(pending)" 占位机制 (Tier-F 仅 D4(b)/(c) 新数据解锁, 本稿不可达)。
     (4) §0 新增优先级声明: ledger v1.10 + register 高于本文档叙事 (CL-09 治理倒置);
        §8 加 stub/main.tex 联动 + 跨合同依赖 flag (Doc A 图表映射 / 第 8 道红线 grep 门)。
     数字未改 (全部以 ledger v1.10 为准); 纯文档。-->
<!-- 状态: agent 重写, 待用户确认。任何论文 prose 起草/修改任务必须先读:
     翻译防漂移指南 + 本文档。格式与图表规则见文档 A
     (lst_models_paper_format_and_figures_contract.md)。事实/数字/证据域以
     claims ledger (paper/outline_and_claims.md, 现 v1.10) 为最终来源。 -->

适用范围: 论文写什么、按什么顺序、各节怎么组织、向哪些范文学什么。
本文档随写作进度更新 (版本 +0.1); 格式合同 (文档 A) 保持稳定。

## 0. 优先级与事实来源 (v1.1 新增)

冲突时优先级 (高 → 低):

```text
研究安全 (AGENTS.md)
> claims ledger (paper/outline_and_claims.md, 现 v1.10) + limitation register
  (docs/v2_1_limitation_claim_register_20260617.md) —— 数字/主张/证据域/措辞红线的最终事实
> 翻译保真 (翻译指南第 3 节)
> 本文档 (叙事与章节计划)
> 文档 A (格式)
> skill 默认行为
```

- **ledger 是数字与主张的唯一事实来源**; 本文档是"写什么、什么顺序"的计划,
  不得覆盖 ledger 的数字或红线。正文每个数字必须能在 ledger 找到行 + artifact 出处。
- **register 是措辞红线的最终来源** (见本文档 §1 红线块, 但以 register 为准, 本文档只引不复制
  versioned 串, 防与 live ledger 漂移)。
- **合同主控规则**: 外部 ARS / academic-research-skills 只能作为
  human-in-the-loop、integrity gate、read-only reviewer、claim/citation
  verification 的辅助编排; 不得覆盖 AGENTS.md、claims ledger、
  artifact checksum、run manifest、no-holdout/test 或本三合同。

## 1. 故事线 (v1.1: guarded 评估纪律为主)

**定位 (主→次): guarded (历史接触) 评估纪律为主贡献; 模型家族对比降级为
strong-baseline 子结果; 条件可预测性为诊断局限。**

一句话立论 (英文成稿用此 verbatim, 出 register lines 372-376; 中文工作版见下):

> We present a guarded chronological evaluation of weak intraday stock-direction
> signals, showing that several standard neural, linear, and tree-based models
> retain small edges over same-row dummy baselines under strict temporal controls,
> while the evidence remains historically contacted and does not support
> clean-test, final-model, or trading-alpha claims.

中文工作版: 我们给出对盘中股票方向弱信号的**guarded (历史接触) 时序评估**;
在严格时序控制下, 若干标准神经/线性/树模型相对 same-row dummy 基线保留**薄边际**,
但证据仍是历史接触的, **不支持干净外测、最终选模、或交易 alpha 主张**。

四条贡献声明 (每条挂 ledger 行 + artifact; 数字以 ledger v1.10 为准):

```text
C1 协议/纪律 [主贡献]: 面向日内方向分类的 guarded 评估纪律 —— no-trade band 标签
   + 按交易日对齐的 purged 切分 + same-row 分层 dummy 地板 + validation-budget 账本
   + 已验证防泄漏 (含 label-shuffle 哨兵)。 [ledger C1.1-C1.3 + F11; artifacts 05_validation_budget_ledger / 05_label_shuffle_sentinel]
C2 实证/strong-baseline [子结果]: 对 {TCN(预登记主候选), standard-DLinear,
   MS-DLinear+TCN, LightGBM} 的受控读出, 多种子 + 逐 ticker; 四家族均过 dummy 地板;
   复杂/神经模型未明显胜过树/简单模型; LightGBM 数值最高但**不选最终模型**
   (no_final_model_selected=true)。 [ledger C2.1-C2.5 + C4.3]
C4 guarded 读出 [实证脊柱]: 预登记 TCN 主候选在历史接触 walk-forward 读出中通过
   预登记稳定性判据; 绑定 row-pooled +0.636pp / 等权 companion +0.550pp; 门槛 bar
   = positive_period_count ≥ 2/7 AND pooled_delta>0 (刻意宽松 ~94% 掷硬币通过下限;
   5/7 仅 descriptive); 56 events; 边际薄且在 **descriptive 多重性折扣**下脆弱
   (PBO 0.51, 仅 TCN period-LCB 过零 +0.05pp, 最差家族 LCB -0.46pp)。 [ledger C4.1-C4.4]
C3 诊断 [边界/局限, 非卖点]: 校准 (ECE ≈0.010 但分辨率近零 —— 非 "well-calibrated")
   + 选择性 autopsy; 条件可预测图谱 (薄边际集中在低活跃/平静切片, 最高活跃切片低于随机)
   **跨期复现于 2017-2024 guarded 域** (ledger C4.5); 一律作诊断边界呈现, 绝不作卖点。
   [ledger C3.1-C3.4 + C4.5; artifacts 05_guarded_activity_tercile / 05_guarded_base_rates]
```

新颖性天花板 (写贡献时的校准): 本文贡献是 **guarded 评估纪律**, 不是模型/架构新颖性;
novelty ceiling LOW-to-MODERATE。任何架构或条件图谱都不得写 "novel" (条件图谱仅可写
"as a diagnostic on this estimand"); register 内部的 NOVEL triage 标签是项目内部用, 不是
manuscript 主张。

### 投稿红线块 (写任何 prose / caption / 标题前必须满足; 最终以 register 为准)

```text
[1] no_final_model_selected=true; 禁 "final model selected"。
[2] LightGBM 数值最高但禁 best / selected / superior / SOTA。
[3] 条件/calm-bar 边际 = 限定条件/局限, 非卖点; 必带 Roll(1984) 微结构 caveat。
[4] "活跃度" = 每 (ticker,trading_day) 合格行计数代理 (no-trade band 代理),
    禁写成 volume / liquidity / volatility。
[5] PBO / LCB / min_family_lcb = DESCRIPTIVE 折扣, 禁 statistically significant
    (除非新增检验并辩护其假设)。
[6] guarded 门槛 bar = ≥2/7 + 正均值; 5/7 仅 descriptive 观测值, 禁用 5/7 撑 certification。
[7] 禁 tradeability / profitable / PnL / Sharpe / alpha 主张 (本文零经济读出)。
[8] train-inner 0.66pp 是 control-row spread (含 last-step 消融控制), 禁与 full-family
    +1.69pp 验证边际并置成 apples-to-apples。
[9] 三证据域 (validation n=2 / train-inner control / guarded 历史接触) 任何一句不得混写;
    每个对比点名其域。禁 clean test / out-of-sample / untouched holdout / final readout。
```

### 标题方向

- 推荐: "Guarded Chronological Evaluation of Weak Intraday Directional Signals";
  备选 "Small Edges, Strict Boundaries: Guarded Evaluation for Intraday Direction Classification"。
- 禁: "协议即产品" 式 / "A New TCN Model…" / "Deep Learning Beats Baselines…" /
  "Profitable Intraday Forecasting…" / 任何 SOTA 暗示。
- ⚠️ `paper/main.tex:21-23` 现有标题是陈旧 skeleton (协议即产品框), 起草时**替换**。

### 反攻击子节 (写 Intro/Conclusion 时必须主动中和)

第三轮敌意审稿人最强一击 (third review): **"两根支柱从不相触, 护栏指向错误的量"** ——
最新颖的条件图谱只在 validation 域、从未在 guarded 域复验; 多重性折扣跑在非绑定估计量上;
预登记门槛近掷硬币。**项目已用证据回答, 起草必须显式用这 5 个 ledger-pointer 答案:**

```text
1. 条件图谱已跨期复现 (ledger C4.5: guarded low +4.08 / high -2.10pp, high<0.5; artifacts/05_guarded_activity_tercile/)
2. 多重性折扣已在绑定 row-pooled 估计量重算, 结论不变 (ledger C4.3 补注; artifacts/05_row_pooled_multiplicity/)
3. 门槛如实写 ≥2/7 (ledger C4.1; 5/7 仅 descriptive)
4. 0.66pp 已 relabel 为 control-row spread (ledger C2.3)
5. calm-bar 边际非类别不平衡/日内泄漏伪影 (ledger C4.5: 基率近恒定 + label-shuffle 哨兵清零分布;
   残余 Roll(1984) 微结构需原始 bar, 记 limitation; artifacts/05_guarded_base_rates / 05_label_shuffle_sentinel)
```

## 2. 范文库与纪律锚点

四篇范文 (**仅借结构/表达模式, 不借句式; 模型新颖性叙事不借**):

| 范文 | 借 | 不借 |
|---|---|---|
| Gu, Kelly & Xiu 2020 (RFS) | Results 按研究问题组织而非逐模型; 共享同一评估协议; 统计与经济意义并报纪律 | 期刊篇幅; 资产定价术语 |
| Fischer & Krauss 2018 (EJOR) | 数据/切分/训练协议的可复现描述精度; "打开黑箱"诊断节 | 收益消失叙事; 策略回测 (本文不做) |
| Zhang, Zohren & Roberts 2019 DeepLOB (IEEE TSP) | 实验分层递进; 模型结构图画法 | 重模型主角叙事 (本文协议主角); LOB 特征 |
| Zeng et al. 2023 DLinear (AAAI) | 质疑-验证式 Intro; 极简模型描述; 消融克制呈现 | 挑衅式标题; forecasting 指标体系 |

**叙事/positioning 模板锚点 (v1.1 新增, 这两篇是本文真正的范式来源):**
- **Kapoor & Narayanan 2023** (leakage/reproducibility): Intro/positioning 的 thesis 模板
  ("评估泄漏 → 收益虚高 → 受控评估下还剩什么"); 本文的纪律主角叙事即此范式的金融日内落地。
- **Chalkidis & Savani 2021 (ICAIF)**: 选择性分类在金融的诚实呈现范式 (foil)。

使用规则: 范文用于结构与表达模式, **不抄句式短语**; 语言一律走翻译指南。写某节前重读对应范文
同名节, 记 3 条结构观察再动笔。BibTeX 唯一入口是 `paper/references.bib`;
新增条目必须带 KB、用户批准或 publisher-source provenance。GKX/DeepLOB/F&K/DLinear
**均已在本地 references.bib 登记**, v1.0 "需补登记" 已过时; 投稿前仍做 publisher-page 复核。

## 3. 章节蓝图 (8 页含图表文献; v1.1 重排, 行和必须等于表头)

总预算: 正文 ≈ 7.0 页 + References ≈ 1.0 页 (28–34 条)。浮动体 ≤1.8 页 (配额见文档 A §3)。

| # | 节 | 页预算 | 必须回答 | 素材来源 (Stage 05 canonical) |
|---|---|---|---|---|
| 0 | Abstract | **≈200–220 词** | 任务/协议缺口/guarded 方法/数据规模/核心数字 (guarded headline + 验证边际)/**两条限制内联** (弱信号 + 历史接触非干净外测)/结论一句 | ledger §0 故事脊柱 |
| 1 | Introduction | 0.9 | 评估为何高估; 缺口; 我们做什么; C1/C2/C4/C3; **反攻击子节的 5 答案融入** | 本文档 §1 + Kapoor-Narayanan 范式 |
| 2 | Related Work | 0.35 | 6 线索 (见 §2 下方); backtest-overfitting 与微结构两条**不可砍** | references.bib (6 线索 citekey 已齐) |
| 3 | Task & Evaluation Protocol | 1.1 | 任务; 标签+band; 切分+purging/embargo; dummy 地板; 读出指标; **validation-budget 账本表**; Fig 1 | docs/protocols/00,01 + v2_1 协议 + 05_validation_budget_ledger.csv |
| 4 | Models | 0.6 | 四家族结构各一段: **TCN(主)/standard-DLinear/MS-DLinear+TCN/LightGBM** (无 LSTM); 共享训练框架; 搜索空间引用 | docs/protocols/02 + configs/models/ |
| 5 | Experimental Setup | 0.45 | 数据范围+统计 (Table 1); HPO; n=2 seeds; frozen params 选择规则; 设备一句 | stage00/02 manifests |
| 6 | Validation Results [Tier-V] | 1.0 | 主表 (Table 2, validation 块) 谁过 dummy 地板; 模型间差距 vs 种子方差; per-ticker; **C2.3 control-row spread 仅作受控对比, 不与验证边际 apples-to-apples** | 05_thesis_synthesis report + ian tables/01-04,13 |
| 7 | Guarded Walk-Forward Readout [Tier-G] | 0.7 | C4.1-C4.4: met 判据 (门槛 ≥2/7 诚实); 四估计量对照; 绑定 row-pooled +0.636pp; 多重性折扣 (descriptive); LightGBM 数值最高但不选 | 05_estimand_contrast / 05_multiplicity_discount / 05_row_pooled_* + v2_1_decision_record |
| 8 | Diagnostics & Robustness [边界] | 0.95 | 跨期条件图谱 (C4.5, 限定框) + 选择性/校准 autopsy + 逐期/逐三分位基率 + label-shuffle 哨兵; 哪些提升在何条件消失 | 05_guarded_activity_tercile / 05_selective_autopsy / 05_guarded_base_rates / 05_label_shuffle_sentinel |
| 9 | Limitations & Conclusion | 0.35 | **强制限制清单**: n=2 seeds / 单市场 / band=3bps·h=9 无扫描 / macro-F1≠经济价值 / Roll(1984) 微结构残余 / guarded≠干净外测; 协议回答了什么; 不展望空话 | register limitations |
| — | Endmatter | 0.1 | GenAI 声明 (文档 A §8) | — |

行和 ≈ 6.5 页正文 + 文献 1.0 = 7.5; 浮动体占位含在各节内。⚠️ **逐节 pp 精确分配超出维护规则的 ±0.2pp
微调权限, 属 re-architecture, 待用户签字** (上表为建议值, 可整体微调)。

裁剪规则 (无附录, 砍=真删): **先砍架构谱系相关 (§2 线索 3 的深度模型史)**, 再压 Models, 再 Table 4 并入图注;
**§2 线索 (2) 泄漏/时序验证、(5) backtest-overfitting、(6) 微结构 三条不可砍** (它们是纪律主角的脊柱)。

### 浮动体配额 (图≤4 / 表≤4, 多面板压缩; 与 Doc A §3 联动)

```text
Fig 1  评估协议/管线示意 (主贡献节必配)
Fig 2  主结果 vs dummy —— 双面板 (validation / guarded), 各面板**各自的 dummy 地板线** (非跨域并置)
Fig 3  校准 + 风险-覆盖 双面板 (风险-覆盖 caption: accuracy-based; 无成本模型; 未选 operating point)
Fig 4  跨期条件图谱 双面板 (validation / guarded 三分位); caption: 活跃度=行计数代理非流动性; high<随机=限定
Table 1  数据集与切分统计
Table 2  主结果 (validation + guarded **分域块标注**, n=2, 含 dummy 行)
Table 3  稳健性/折扣合并表 (多重性 per-family mean+period-LCB+PBO+min_family_lcb + 四估计量对照 + 逐期/逐三分位基率; 全标 DESCRIPTIVE)
Table 4  条件/选择性摘要 (三分位 delta + e-AURC/AUGRC/ECE/Brier-resolution + 哨兵 pass) 或并入 Fig 4 图注
```

train-inner 消融 → 并入 Table 3 子块或正文 (control-row, 非 full-family)。
✅ **Doc A §3 联动依赖已同步**: Doc A v1.1 的表格映射已改为上表的
Tier-G/Stage 05 artifact 方案, 不再使用旧的 pending 表行。

## 4. 措辞分级: 三证据域 (v1.1: 删 Tier-V/F 二元, 改三域 + Tier-G)

所有实验已完成。证据是**三个不可混写的域**, 各有 canonical 句式; **不存在 "完成实验即升 Tier-F" 这回事**。

| 域 | 标签 | canonical 写法 | 红线 |
|---|---|---|---|
| 官方验证 (n=2) | **V** | "On the frozen validation split, X exceeds the stratified dummy floor by … pp (mean ± std, n=2 seeds)." | 禁 generalize / out-of-sample |
| train-inner 控制 | **control** | C2.3 canonical (见 ledger): "train-inner control comparisons across four control rows (two last-step ablation controls) show a 0.66pp spread, smaller than the +1.69pp official-validation margin of the TCN primary…" | 禁与 full-family / 验证边际 apples-to-apples |
| guarded 历史接触 walk-forward [**已完成, 本路线最高可达**] | **G** | "The predeclared TCN primary met the predeclared guarded stability criteria in a historically-contacted walk-forward readout." 必带 guarded / historically-contacted | 禁 clean test / final model / best; 门槛诚实 (≥2/7); 多重性 descriptive |

**Tier-F (干净外测 / 最终模型 / holdout) = 本路线不可达**: 仅 D4(b) 新数据 future-blind 或 D4(c) 外部 ticker
预注册可解锁 (route roadmap lines 265-267, 630), 本稿**永不使用**。删除 v1.0 的完成后升格叙事
和所有 pending 表行/占位策略机制。

门槛诚实 footnote (C4 节必写): guarded 判据 bar = positive_period_count ≥ 2/7 AND pooled_delta>0
(零假设独立掷硬币下 ≥2/7 通过 ≈94%); 5/7 为观测值, force 来自 pre-registration + 方向一致, 非门槛严苛。

**反融合规则**: validation 域 (+1.69pp, n=2, 2013-2017) 与 guarded 域 (+0.636pp, 2017-2024) 是不同时代+不同
接触层级, 任何句子不得融成一个 thesis; 条件图谱必须分 validation/guarded 两域写 (ledger C3.4 留 validation,
C4.5 承载 guarded)。

## 5. 各节起草顺序与开工条件 (v1.1: 全完成态)

实验全部完成, 不再有 "等最终数字" 的 gating; 按稳定度排序:

```text
1. §3 Protocol [V/control/G 三域纪律 + budget 账本]  ← 协议冻结, 最稳, 主贡献节
2. §5 Setup                                          ← manifests 已有
3. §2 Related [6 线索, Kapoor-Narayanan 范式]         ← citekey 已齐, 仅补 When-Alpha/FINSABER
4. §4 Models [四家族, 无 LSTM]                        ← configs + protocol 02
5. §6 Validation Results [Tier-V]                     ← 05 report + tables
6. §7 Guarded Walk-Forward Readout [Tier-G]           ← 05_estimand/multiplicity/row_pooled + decision_record
7. §8 Diagnostics & Robustness [跨期条件图谱 + 选择性/校准 + 基率 + 哨兵, 限定框]
8. §9 Limitations (专门节, 强制清单) + §1 Intro (贡献句 + 反攻击 5 答案对齐 ledger)
9. Abstract (最后; guarded headline + 两限制内联; 不再 "等 Tier-F")
```

每节开工条件: 素材文件路径存在且可读; `paper/outline_and_claims.md` 可读;
本节将使用的每个结果句已记录 `claim_id`, `evidence_domain`, `allowed_tier`,
`estimand`, `weight_unit`, `source_artifact`, `forbidden_wording`; exact artifact
root/run id 已明确; 对应范文同名节重读完成; chunk ≤5 段 (翻译指南 §1)
逐块推进。每 chunk 收尾过翻译指南 grep 门 **+ 本文档 §1 红线块自查**。

## 6. Skills 绑定 (本阶段)

| 任务 | skill | 约束 |
|---|---|---|
| 节结构与段落规划 | academic-paper / ml-paper-writing / academic-pipeline | 结构听 skill, 语言听翻译指南, 数字/红线听 ledger |
| 文献补充检索 | deep-research / arxiv / firecrawl-research-papers / nature-academic-search | 新引用先登记 `paper/references.bib` 并记录 provenance |
| 图表脚本 | figure-generation | 风格参数以文档 A §4 rcParams 为准; 图从 artifacts 重生成 |
| 章节审稿 | academic-paper-reviewer / ara-rigor-reviewer | 默认只读; 修改后重过 ledger 绑定 + 翻译 Pass B/C + grep 门 + 红线块 |
| 终稿打磨 | quality-editor / nature-polishing | 只做 Pass C, 不碰强度/术语/红线 |

阅读链 (论文 prose 任务): AGENTS.md → 路由文档 → 翻译指南 → 本文档
→ ledger (核数字/红线) → 目标 paper section → 所用 skill。
图表/排版任务读文档 A 替代本文档。

## 7. 反漂移 (本文档专属项)

每个写作任务开始时, 工作笔记复述一行:
"纪律主角/C1-C2-C4-C3挂台账/三证据域不混写/Tier-G最高(无Tier-F)/8条红线/8页倒推/范文借结构不借句式"。

chunk 完成自查 (叠加翻译指南 §8 清单):

```text
[ ] 本 chunk 主张全部能在 ledger v1.10 找到行 + artifact 出处
[ ] 每个结果句记录 claim_id / evidence_domain / estimand / weight_unit / source_artifact
[ ] 证据域正确且未混写 (每对比点名 V / control / G; 无 clean-test/out-of-sample)
[ ] §1 红线块 8/9 条逐条不违 (no-final-model / LightGBM-非best / calm-bar=限定 / activity=行计数 /
    PBO-descriptive / ≥2/7门槛 / no-PnL / control-row-spread / 三域不混)
[ ] 节页预算未超 (双栏一页 ≈ 950–1050 词)
[ ] 范文同名节结构观察 3 条已记录
[ ] 新引用已登记 `paper/references.bib` 且有 provenance
```

✅ **强制门结构性洞 (CL-12, 已补)**: 翻译指南 v1.2 已新增第 8 道项目 claims 红线门。
该门不机械删除所有命中, 而是要求逐项确认是否处于否定/限定语境; 未限定命中不合格。
典型串集:
`clean test|out-of-sample|untouched holdout|final model|best model|state-of-the-art|profitable|tradable|alpha|well-calibrated|statistically significant`
(命中逐个人工确认是否在否定/限定语境)。

## 8. 维护与联动

- 写作推进中允许 agent 更新: §3 预算微调 (±0.2 页内)、§5 顺序完成态标注、ledger 状态; 其余 (含本次
  re-architecture 的逐节 pp) 需用户同意。
- **claim → run → artifact 溯源** (v1.1: 证据跨 4+ run, 非单 run_id): 每条主张在 ledger 记其 run_id +
  artifact 路径 + sha256; C2/C3 ← Stage 03 run; C4 ← v2_1 run 20260618_063559_889276; C4.3/C4.4/C4.5 ←
  Stage 05 run 20260619_090454_562658 + 五个 addenda 目录。
- **派生联动目标 (CL-11)**: 本文档陈旧已扩散进脚手架, 改本文档须同步修以下派生件 (它们将被 prose 替换,
  但当前注释含错误名册, 起草前先正):
  ```text
  paper/main.tex (标题: 协议即产品 → guarded 标题方向)
  paper/sections/04_models.tex (注释 "MLP; LSTM context" 双错 → 四家族正确名册)
  paper/sections/06_results.tex / 07_diagnostics.tex (旧 Tier-V-only 注释 → 三域 + Tier-G)
  paper/sections/08_conclusion.tex (限制清单缺 macro-F1≠value / 微结构 / band-horizon → 强制清单)
  paper/sections/02_related.tex (硬编码 Q1-Q4 → 6 线索)
  ```
- **跨合同依赖 flag (本文档只 flag, 不改稳定合同/ledger)**:
  - Doc A §3 图表映射已同步; 后续写图/表时仍需继续对齐本文档 §3 浮动体配额。
  - 第 8 道项目专属红线 grep 门已落翻译指南 v1.2, 见本文 §7。
  - ledger 治理倒置已在本轮修为 "claims ledger 事实优先, 本文只管 prose"。
  - references.bib 需补 When-Alpha-Disappears / FINSABER (并发工作区分句用)。
- 与文档 A、翻译指南构成论文三合同; 优先级见 §0。ARS/外部 agent
  workflow 只能辅助执行 §0, 不得成为更高优先级事实源。

## 参考来源

- 范文: Gu, Kelly & Xiu 2020 (RFS); Fischer & Krauss 2018 (EJOR); Zhang, Zohren & Roberts 2019 DeepLOB
  (IEEE TSP); Zeng et al. 2023 DLinear (AAAI)。叙事范式锚点: Kapoor & Narayanan 2023; Chalkidis & Savani 2021。
- ICAIF '25/'26 CFP (8 页含图表文献、无附录、双盲、sigconf+anonymous、2026-08-02 截稿) — 页预算依据。
- 本项目事实来源: paper/outline_and_claims.md (claims ledger v1.10);
  paper/references.bib; docs/v2_1_limitation_claim_register_20260617.md;
  docs/v2_1_third_adversarial_review_20260619.md; docs/v2_1_docb_v11_phase1_review_20260619.md (本次升级触发);
  artifacts/05_thesis_synthesis/20260619_090454_562658/ + 05_row_pooled_loo / 05_guarded_activity_tercile /
  05_row_pooled_multiplicity / 05_guarded_base_rates / 05_label_shuffle_sentinel; docs/protocols/00-05 + v2_1 协议。
