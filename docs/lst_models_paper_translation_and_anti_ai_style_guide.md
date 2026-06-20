# lst_models 论文英文写作与翻译防漂移指南
<!-- GUIDE_VERSION: v1.2 / 2026-06-20 -->
<!-- v1.1 变更: 词表扩充 (Kobak 学术超额词/avoid-ai-writing/anti-slop/llm-cliches),
     新增中译英 Chinglish 专项清单, 新增工作流绑定章节, grep 门拆为 7 道。 -->
<!-- v1.2 变更: 绑定 claims ledger / Tier-G guarded readout / references.bib 单一引用源,
     明确 ARS 只能辅助编排, 新增 Windows PowerShell prose gate 等价命令,
     补第 8 道项目 claims 红线门。 -->
<!-- 状态: 已用户确认 (2026-06-11, 随 paper 工作区审查轮确认)。
     本文档是论文写作/翻译任务的强制前置阅读。 -->

适用范围: 本项目所有 中文→英文 论文翻译、英文初稿撰写、英文润色任务
(Stage 05 thesis synthesis 及之后的论文工作)。

本文档是"工作合同", 不是参考建议。每次写作/翻译任务开始时, agent 必须
重读本文档并执行第 8 节的反漂移协议。本指南优先级高于任何已安装 skill
(academic-paper / ml-paper-writing / academic-paper-reviewer / academic-pipeline /
nature-polishing / quality-editor) 的内部默认风格。

来源依据: Leey21/awesome-ai-research-writing 提示词库、Wikipedia "Signs of
AI writing" 清单、当前路由文档中的 `ml-paper-writing` / `academic-paper`
使用边界、项目 paper 工作区审查经验、document-level MT 研究
(Karpinska & Iyyer 2023, WMT)。

---

## 1. 翻译单位决策: 段落为单位翻译, 句子为单位核对

决策: **以段落为翻译单位, 以句子为核对单位。** 不采用逐句翻译。

理由 (有研究支持):

- LLM 段落级翻译在连贯性、代词指代、术语一致性上显著优于逐句翻译;
  逐句翻译产生镜像中文句式结构的"翻译腔" (Karpinska & Iyyer 2023)。
- 但段落级翻译会偶发"关键错误": 漏译限定词、合并两个主张、强度漂移。
  所以必须用句级回核兜底。

### 三遍流程 (每个段落)

```text
Pass A 段落翻译: 读整段中文 + 所在 subsection 的上下文, 翻译为英文段落。
        目标是译意, 不是译字; 句子边界允许重组 (拆句/并句)。
Pass B 句级保真核对: 把英文段落逐句对照中文原文, 检查 6 项:
        数字与单位 / 否定与因果方向 / 限定词(可能,仅,在验证集上) /
        主张强度未被放大或缩小 / 术语符合第 7 节术语表 / 无添油加醋。
Pass C 风格审计: 跑第 4 节词汇黑名单 + 第 5 节句长规则 + 第 6 节结构特征,
        用 grep 做机械检查 (命令见第 8 节)。
```

### 任务分块上限

- 一次任务 (一轮对话回合) 最多处理 **1 个 subsection 或 5 个段落**, 取小者。
- 超过上限必须分多轮, 每轮重新执行反漂移协议。原因: 上下文越长,
  风格规则的遵守率越低 (漂移), 这是用户明确要防的问题。
- 每轮输出后附"中文直译回核" (见第 9 节输出格式), 供用户核对逻辑。

---

## 2. 词汇规则: 三级清单

总原则 (来自 Leey21 去AI味 prompt): 用朴实、精准、常见的学术词。
只有在表达特定技术含义时才用术语, 不为"高级感"堆砌辞藻。
专业术语 (第 7 节术语表) 永远不在替换范围内。

### Tier 1 — 禁用 (装饰性 AI 标志词, 出现 = 不合格)

合并来源: Leey21 词表 + Wikipedia AI 词汇 + anti-slop 禁用表 + llm-cliches。

```text
比喻装饰名词: tapestry, testament, beacon, symphony, odyssey, nexus,
  journey (figurative), landscape (抽象义), realm, pinnacle, epitome,
  apogee, cornerstone (figurative), watershed moment,
  paradigm (figurative; "training paradigm" 等技术用法除外)
营销形容词: vibrant, bustling, breathtaking, stunning, captivating,
  exquisite, esteemed, iconic, renowned, groundbreaking, game-changing,
  cutting-edge, revolutionary, transformative, trailblazing, visionary,
  pioneering (自我描述), seamless, holistic, unparalleled, unrivaled,
  unmatched, unprecedented, ever-evolving, multifaceted, meticulous(ly),
  quintessential, paramount, formidable, profound, indelible,
  enduring / lasting (figurative)
戏剧化动词: delve (into), unveil, transcend, traverse, rekindle,
  reimagine, galvanize, unleash, unlock (figurative), usher in,
  embark on, empower (figurative), spearhead, navigate (figurative),
  nurture, cherish, adore, ponder, permeate, perpetuate
空壳商务词: synergy, thought leadership, myriad, plethora,
  aforementioned, nestled, in the heart of
直接改写: serves as / stands as → is; a testament to → shows;
  paving the way for → 删或写出具体后续; marks a significant → 陈述事实
```

### Tier 2 — 默认替换 (膨胀词 → 平实词)

| 不要写 | 改写为 |
|---|---|
| leverage, utilize, harness | use |
| elucidate | explain, clarify |
| ameliorate | improve |
| alleviate | reduce, ease |
| bolster, fortify | support, strengthen |
| endeavor (v.) | try, attempt |
| expedite | speed up |
| foster, cultivate | (重写句子, 或 encourage) |
| facilitate | enable, allow, help |
| pivotal, crucial (堆叠时) | central, key (限频), important |
| underscore, accentuate | show, indicate |
| highlight (v., 滥用时) | show, point out |
| showcase, depict | show, present, compare |
| demonstrate (滥用时) | show |
| ascertain | determine, find |
| amass | collect, gather |
| amplify | increase |
| articulate (v.) | state, describe |
| conceptualize | define, frame |
| conjecture (v.) | hypothesize, suspect |
| consolidate | combine, merge |
| convey | show, indicate, express |
| culminate in | end in, result in |
| decipher | interpret, identify |
| delineate | describe, outline |
| devise | design, develop |
| disseminate | distribute, share |
| diverge | differ |
| enumerate | list |
| envision | expect, plan |
| exacerbate | worsen |
| harmonize | align, make consistent |
| hone | refine |
| innovate (v.) | (重写为具体动作) |
| intricate, nuanced | complex, detailed |
| manifest (v.) | appear, show |
| mediate | (用具体机制动词) |
| obscure (v.) | hide, mask |
| opt for | choose |
| originates from | comes from |
| perceive | see, view |
| prescribe | specify, require |
| prevailing | common, dominant |
| recapitulate | summarize |
| reconcile | resolve |
| rectify | fix, correct |
| scrutinize | examine, inspect |
| substantiate | support, confirm |
| tailor (v.) | adapt, adjust |
| interpolate (非数学义) | insert |
| harness | use |
| navigate (figurative) | handle, work through |
| augment (非数据增强义) | extend, add to |
| cultivate | build, develop |
| illuminate | clarify, show |
| juxtapose | compare |
| underpin | support |
| encompass | include, cover |
| boasts | has |
| commence | start, begin |
| poised to | ready to, likely to |
| nascent | new, early-stage |
| burgeoning | growing |
| instrumental | important (写明具体作用) |
| streamline | simplify |
| elevate | improve, raise |
| garner | receive, attract |
| deep dive | detailed analysis |
| unpack | explain, break down |
| employ (滥用时) | use |
| conduct an analysis of | analyze (动词直接化) |

注: 数学/统计技术义不受限 — interpolate (插值)、integrate (积分)、
converge/diverge (收敛/发散)、amplify (信号放大)、augment (data
augmentation)、trajectory (loss/training trajectory)、spectrum (频谱)、
robust (robustness check) 等按术语使用, grep 命中后人工确认即可。

### Tier 3 — 限频 (正当学术词, 但 AI 高频堆叠)

依据 Kobak et al. 学术超额词研究 (1500 万 PubMed 摘要, 407 个超额
风格词) 的高信号子集; 完整 407 词中含大量正常功能词, 不照单全禁。

```text
demonstrate, integrate, evaluate, comprehensive, significant(ly),
robust, novel, effectively, efficiently, additionally, moreover,
furthermore, crucial, key (adj.), enhance, valuable, align with,
interplay, notably, noteworthy, thereby, consequently, subsequently,
ultimately, predominantly, promising / holds promise, avenue(s),
foundational, groundwork, insights, capabilities, advancement(s),
exploration, exhibit, state-of-the-art, remarkable, exceptional,
compelling, sophisticated, innovative
```

规则:
- 同一个 Tier 3 词在一页 (约 500 词) 内最多出现 1 次; 同段不重复。
- "significant(ly)" 只允许在有统计检验支持时使用 (显著性的本义);
  日常强调一律删掉或改 "substantial/large" 并给出数值。
- state-of-the-art 仅在给出基准引用时使用; novel 全文最多 1 次
  (贡献声明处)。
- remarkable / exceptional / compelling / sophisticated 必须跟具体
  数字或机制, 否则删除。
- 正常科研动词 (show, examine, investigate, reveal, exhibit, employ,
  conduct) 不禁用, 但同段不堆叠; 优先 use 替代 employ, 优先动词
  直接化替代 conduct an X。
- 段首连接词链 (Additionally → Moreover → Furthermore) 禁止;
  段内句子靠逻辑递进自然衔接, 不靠机械连接词 (Leey21 规则)。

### 句首评注词限频 (anti-slop 句首词表, 学术适配)

```text
Moreover, / Furthermore, / Additionally, / Notably, / Importantly, /
Interestingly, / Indeed, / Overall,
```

- 上述句首词每节合计最多 2 次, 不许连续两段同词开头。
- In conclusion / To summarize 禁用 (结论节的标题已表意)。
- Firstly / Secondly / Thirdly 禁用; 贡献列举可用 First, / Second,。
- AI 高频词随模型代际漂移 (2023 代: delve, tapestry, pivotal →
  2025 代: emphasizing, enhance, highlighting, showcasing),
  词表刷新规则见第 11 节。

### 短语黑名单 (直接删除或重写)

```text
It is worth noting that ... / It should be noted that ...
plays a crucial/pivotal/vital role in ...
In recent years, ... has garnered/gained significant/increasing attention
not only ... but also ...        (每节最多 1 次)
a wide range of / various / numerous   (给出具体数量或删除)
sheds light on / holds great promise/potential
In the rapidly evolving field/landscape of ...
This highlights/underscores the importance of ...
At its core, ... / In the realm of ... / When it comes to ...
In today's ... (开场) / at the end of the day / in a nutshell
This is where X comes in / cannot be overstated
it goes without saying / needless to say
serves as a foundation/cornerstone for ...
offers/provides valuable insights into ...
opens (up) new avenues for ...
bridge the gap   (例外: Intro 中 "To bridge this gap" 最多 1 次)
In order to → To;  Due to the fact that → Because
has the ability to → can;  At this point in time → Now
It is important to note that the data shows → The data show
```

---

## 3. 学术保真规则 (翻译不许改变科学内容)

这是比风格更高优先级的红线, 与 AGENTS.md 第 6 节 (不得伪造指标) 同级:

1. **主张强度逐字守恒**: 中文"提升" → "improves", 不许加 significantly /
   substantially / dramatically。中文"显著提升"且原文有统计支持时才可用
   "significantly improves"。反向同理, 不许弱化原文确定的结论。
2. **限定词必须存活**: "在本验证集上"→"on this validation set";
   "可能"→"may"; "初步"→"preliminary"; "仅"→"only"。翻译丢失 scope
   限定词 = 保真失败, 不是风格问题。
3. **数字、指标名、表/图编号、ticker、stage 名逐字核对**, 以
   artifacts 表格与 run manifest 为准, 不从记忆中复述数值。
4. **不添加原文没有的内容**: 不补例子、不补解释、不补引用。
   需要补充时单独提出, 由用户决定, 不混入译文。
5. **时态**: 方法、模型结构、图表所示事实用一般现在时
   (the model takes ... as input; Table 3 shows ...);
   已执行的实验动作用过去时 (we trained ...; we selected ...)。
6. **引用红线**: 论文唯一 BibTeX 入口是 `paper/references.bib`。
   新引用进入正文前, 必须先进入该文件, 且每个新增条目必须带
   KB 登记来源、用户批准来源或 publisher/source provenance 注释。
   不得从 `hf_stock_ml_references2/papers/README.md`、网页搜索结果、
   skill 输出或模型记忆直接写 `\cite{}`。AI 不得自行生成新引用条目
   (社区统计 AI 生成引用错误率 ~40%)。

---

## 4. 句子规则 (长难句控制)

依据: 可读性研究 — 平均句长 20 词左右理解率最高, 超过 25 词理解率
陡降; 学术正文合理区间 18–24 词。

硬性规则:

1. **单句上限 35 词**。超过必须拆。唯一豁免: 带条件限定的统计陈述
   确实不可拆 — 豁免必须写进修改日志。
2. **目标平均句长 18–24 词**; 连续 3 句超过 25 词 → 必须插入一个短句。
   刻意保留长短节奏, 全段等长句是 AI 特征。
3. **一句一个主张**。中文流水句 (逗号串联多个分句) 必须拆成多个英文
   句子, 禁止用分号或 and 链条镜像原文结构。
4. **主语和主动词尽早出现**: 句首从句最多 1 个; 禁止句首悬垂分词
   ("Leveraging the proposed framework, we ...")。
5. **嵌套从句最多 1 层**; 每句最多 1 组括号插入语。
6. **拒绝名词化堆叠**: "the implementation of the evaluation of X"
   → "evaluating X"。
7. **主动语态优先**, 第一人称 "we" 正常使用; 被动只用于动作者
   无关紧要的场合 (the data were resampled to 5-minute bars)。
8. 避免名词所有格 (the model's performance → the performance of
   the model 或 model performance) (Leey21 润色规则)。

### 中译英 Chinglish 专项清单 (Pass B 时逐句核对)

来源: Carl Gene Fordham 中译英 15 类错误 + Elsevier Chinglish 指南,
按本项目语境改编。

1. 冠词: 中文无冠词, 每个名词短语补判 a/an/the/零冠词;
   首次提及用 a, 复指用 the。
2. 单复数与主谓一致: 逐个可数名词检查; data are / evidence is
   类特殊词单独记。
3. 范畴词删除: "research work" → research; "the process of
   training" → training; "the problem of overfitting" → overfitting
   (范畴词无信息量时一律删)。
4. "进行/开展"填充: conduct an analysis of → analyze;
   perform an evaluation of → evaluate; carry out experiments →
   run experiments 或直接 we test。
5. "存在"句: There exist several problems → The method has several
   problems, 或改具体动词。
6. 越来越: 不写 more and more; 用 increasingly / a growing number of。
7. 等/等等: 不译 and so on / etc.; 用 such as / including 开放列举。
8. 众所周知: It is well known that → 给引用, 或删。
9. 显然: obviously 删除并给出推理; clearly 每节最多 1 次。
10. 我国/国内外: 不写 our country / at home and abroad; 写具体对象
    (本项目: the US equity market / the S&P 100 universe; prior work)。
11. 此外句首: 不写 Besides,; 用 In addition (限频) 或并入上句逻辑。
12. 话题句重组: "关于/对于 X, ..." 不译 As for X / Regarding X;
    把 X 改写为主语或宾语。
13. 无主语句: 补 we / the model / the pipeline; 检查分词悬垂
    (Using the proposed method, the accuracy improves 是错的 —
    分词的逻辑主语必须是主句主语)。
14. 程度词: 很/非常 → 删或给数字; "大幅显著提升" → 选一个表述
    并给数值。
15. respectively: 仅当两组元素一一对应且省略会歧义时使用。
16. can not only ... but also: 拆成两句 (叠加短语黑名单规则)。
17. 四字成语与比喻: 译功能义, 不直译意象。
18. 时态回查: 中文无形态时态, 译完按第 3 节规则 5 逐句指定。

---

## 5. 结构性 AI 特征 (25 模式精选, 逐项检查)

1. **-ing 尾巴**: 句尾挂 ", highlighting/ensuring/underscoring/
   reflecting ..." 的假深度从句 → 删除或改为独立句并给出具体依据。
2. **Rule of three 滥用**: 强行三项并列 ("efficient, scalable, and
   robust") → 只保留有证据的项。
3. **Negative parallelism**: "It is not just X, it is Y" / "rather than
   X, we Y" 滥用 → 直接陈述 Y。
4. **False range**: "from X to Y" 而 X、Y 不在同一量纲 → 改为明确列举。
5. **Copula 回避**: serves as / stands as / represents → is。
6. **同义词轮换 (synonym cycling)**: AI 为避免重复换说法。学术写作
   相反 — **同一概念全篇必须用同一个词** (见第 7 节术语表)。
7. **破折号 (—) 滥用**: 正文尽量不用, 改从句、逗号或括号 (Leey21)。
8. **加粗/斜体强调**: 正文禁止, 重点靠句式体现 (Leey21)。
9. **正文列表化**: 论证必须是连贯段落, 不用 \item / bullet
   (方法步骤、贡献列表等结构性内容除外, 须用户同意)。
10. **空洞收尾**: 段尾 "... with promising implications for future
    research" 类万金油句 → 删除。
11. **过度 hedging 堆叠**: "could potentially possibly" → "may"。
12. **直引号**: 用 " ", 不用弯引号 " "; LaTeX 用 `` ''。

---

## 6. 排版与 LaTeX 规则 (Leey21 翻译 prompt 规范)

1. 输出 LaTeX 时: 转义特殊字符 (95\% / model\_v1 / R\&D);
   数学公式原样保留 ($ 包围); 保留 \cite{} \ref{} \label{}。
2. 输出 Word 纯文本时: 禁一切 Markdown 符号 (** * # > ```)。
3. 不展开领域通用缩写 (LSTM、HPO 保持原样, 首次出现按论文惯例定义)。
4. 标题用 sentence case, 不用 Title Case (除非 ACM 模板要求)。
5. 正文不使用 emoji (论文场景无条件禁止)。

---

## 7. 项目术语表 (单一事实来源, 持续登记)

规则: 同一概念全篇唯一英文名。新术语先登记到本表再使用。
禁止的变体写出来是为了 grep 排查。

| 中文 | 固定英文 | 禁止的变体 |
|---|---|---|
| 日内股票方向分类 | intraday stock direction classification | stock movement prediction (仅文献综述引用他人工作时可用) |
| 时序划分 / 按时间切分 | chronological split | temporal split, time-based split |
| 时序验证 | chronological validation | walk-forward (另一概念, 见下) |
| 滚动前推验证 | walk-forward validation | rolling validation |
| 冻结验证读出 | frozen validation readout | (不缩写为 readout 单用, 首次出现用全称) |
| 留出集/测试集 | holdout/test set | hold-out (拼写统一不带连字符) |
| 无交易带 | no-trade band | neutral zone, flat band (引用他人工作时按原文) |
| 标签视界 | label horizon | prediction horizon |
| 清除与禁运 | purging and embargo | (不译为 purge/embargoing 动名词混用) |
| 分层虚拟基线 | stratified dummy baseline | random baseline, naive baseline |
| 选择性分类 | selective classification | rejection option (引用他人时可用) |
| 覆盖率 | coverage | (selective 场景固定用 coverage) |
| 风险-覆盖曲线 | risk-coverage curve | coverage-risk curve |
| 校准 | calibration | (reliability diagram = 校准图, 固定) |
| 等质量分箱 | equal-mass binning | equal-frequency binning |
| 消融实验 | ablation | ablation study (二者取一, 全篇统一用 ablation) |
| 超参数优化 | hyperparameter optimization (HPO) | hyperparameter tuning |
| 训练内层 | train-inner | inner-train |
| 5 分钟K线 | 5-minute bars | 5-min candles, 5-minute candlesticks |
| 股票代码 | ticker | symbol, stock code |
| 活跃度三分位 | activity terciles | activity tertiles |
| 逐代码读出 | per-ticker readout | per-stock |
| 多种子 | multi-seed | multiple seeds (名词性合成词统一) |
| guarded 历史接触 walk-forward 读出 | guarded, historically-contacted walk-forward readout | clean test, clean holdout, final model, out-of-sample proof |
| 绑定行池估计量 | binding row-pooled estimand | headline number (裸称), the result |
| 等权 companion | equal-weight companion | alternate main result, replacement estimand |

(写作过程中遇到新术语 → 同一任务内把它加进本表。)

---

## 8. 反漂移协议 (每次任务强制执行)

### 任务开始时

1. 重读本文档 (全文, 不是节选)。
2. 在工作笔记或回复开头复述本行核心规则 (一行):
   "段落翻译+句级核对; claim_id 绑定; Tier1 零容忍;
   单句≤35词均值18–24; 主张强度守恒; 术语表唯一;
   引用只用 paper/references.bib。"
3. 任何经验结果句、数字句、表图 caption、贡献句或 abstract 结果句,
   必须先绑定 `paper/outline_and_claims.md` 中的一个 `claim_id`。
   工作笔记需记录: `claim_id`, `evidence_domain`, `allowed_tier`,
   `estimand`, `weight_unit`, `source_artifact`, `forbidden_wording`。
   如果 claims ledger 没有对应行, 只能写占位或向用户报告缺口。
4. 确认本轮范围 ≤ 1 subsection 或 ≤ 5 段。

### Tier-G guarded readout 句式硬门

当句子引用 C4/C4.5 或任何 V2.1 guarded walk-forward 结果时, 必须使用
Tier-G 约束, 不得沿用旧 Tier-F 泛化措辞。推荐基准句:

```text
In a guarded, historically-contacted walk-forward readout, the
predeclared TCN primary met the predeclared guarded stability criteria.
This readout is not a clean holdout/test, did not select a final model,
and all family-rank language is descriptive.
```

任何 C4 句必须同时说明: `guarded / historically-contacted`,
`no_final_model_selected=true`, 不写 clean test / out-of-sample proof /
best / selected / superior / final model。涉及 delta、PBO、LCB、LOO 时,
必须标明 official-validation、guarded row-pooled binding estimand,
或 guarded equal-weight companion。

### 每个 chunk 完成后 — 自查清单

```text
[ ] Pass B 句级核对完成 (数字/否定/限定词/强度/术语/无添加)
[ ] Chinglish 专项 18 项核对完成 (第 4 节)
[ ] grep 门 1-8 已运行: 门 1/3/6 零命中; 门 2/4/5/8 命中已逐项处理
[ ] 超 35 词句子 = 0 (或修改日志记录豁免)
[ ] rule of three / serves as / 句首评注词密度已排查
[ ] 术语与第 7 节一致; 新术语已登记
[ ] 数字与 claims ledger + artifacts 表格逐项核对
[ ] 每个结果句记录 claim_id / evidence_domain / estimand / weight_unit / source_artifact
[ ] C4/C4.5 句子通过 Tier-G guarded readout 句式硬门
[ ] 输出含中文直译回核 + 修改日志
```

### 机械检查命令 — 8 道 grep 门 (对输出的 .tex / .md 文件运行)

#### Colab / bash 版本

```bash
# 门 1 Tier 1 禁用词 (期望: 无输出; 命中 = 不合格)
grep -niE "delve|tapestry|testament|beacon|symphony|odyssey|nexus|pinnacle|epitome|apogee|watershed|vibrant|bustling|captivating|exquisite|esteemed|iconic|groundbreaking|game.?chang|cutting.?edge|trailblaz|visionary|seamless|holistic|unparalleled|unrivaled|unmatched|unprecedented|ever.?evolving|multifaceted|meticulous|quintessential|paramount|formidable|indelible|unveil|transcend|traverse|rekindle|reimagine|galvanize|unleash|usher in|embark|spearhead|nestled|synergy|myriad|plethora|aforementioned" draft.tex

# 门 2 Tier 2 默认替换词 (命中 = 逐个确认是否技术义, 否则替换)
grep -niE "leverag|utiliz|elucidat|amelior|bolster|endeavor|expedit|foster|facilitat|pivotal|underscore|showcas|harness|cultivat|illuminat|juxtapos|underpin|encompass|boasts|commence|ascertain|poised to|nascent|burgeoning|streamlin|empower|garner" draft.tex

# 门 3 短语黑名单 (期望: 无输出; bridge the gap 人工确认 Intro 限 1)
grep -niE "worth noting|important to note|(crucial|vital|pivotal) role|in recent years|sheds light|paving the way|not only|wide range of|holds great (promise|potential)|rapidly evolving|in the realm|at its core|when it comes to|bridge the gap|cannot be overstated|valuable insights|new avenues|in conclusion|in today's" draft.tex

# 门 4 句首评注词密度 (人工确认每节合计 <= 2, 不连续)
grep -nE "(^|\. )(Moreover|Furthermore|Additionally|Notably|Importantly|Interestingly|Indeed|Overall), " draft.tex

# 门 5 -ing 尾巴 (人工复核命中行)
grep -nE ", (highlighting|underscoring|ensuring|reflecting|showcasing|demonstrating|emphasizing|fostering|enabling|signifying|contributing) " draft.tex

# 门 6 Chinglish 高频残留 (期望: 无输出)
grep -niE "more and more|and so on| etc\.|there (exist|exists)|it is well known|obviously|our country|at home and abroad|(^|\. )(As for|Regarding) |conduct(ed|ing)? an? (analysis|evaluation|investigation)|carr(y|ied|ying) out|make an? (improvement|comparison|analysis)" draft.tex

# 门 7 长句审计 (>35 词, 人工拆句或登记豁免)
awk 'BEGIN{RS="[.!?]"} {n=split($0,w,/[ \t\n]+/); if(n>35) print "LONG("n"): " substr($0,1,90)"..."}' draft.tex

# 门 8 项目 claims 红线 (命中 = 人工确认是否否定/限定语境; 否则不合格)
grep -niE "clean test|out-of-sample|untouched holdout|final model|best model|state-of-the-art|profitable|tradable|alpha|well-calibrated|statistically significant" draft.tex
```

#### Windows PowerShell 版本

```powershell
$Draft = "draft.tex"

# 门 1 Tier 1 禁用词 (期望: 无输出; 命中 = 不合格)
Select-String -Path $Draft -Pattern "delve|tapestry|testament|beacon|symphony|odyssey|nexus|pinnacle|epitome|apogee|watershed|vibrant|bustling|captivating|exquisite|esteemed|iconic|groundbreaking|game.?chang|cutting.?edge|trailblaz|visionary|seamless|holistic|unparalleled|unrivaled|unmatched|unprecedented|ever.?evolving|multifaceted|meticulous|quintessential|paramount|formidable|indelible|unveil|transcend|traverse|rekindle|reimagine|galvanize|unleash|usher in|embark|spearhead|nestled|synergy|myriad|plethora|aforementioned"

# 门 2 Tier 2 默认替换词 (命中 = 逐个确认是否技术义, 否则替换)
Select-String -Path $Draft -Pattern "leverag|utiliz|elucidat|amelior|bolster|endeavor|expedit|foster|facilitat|pivotal|underscore|showcas|harness|cultivat|illuminat|juxtapos|underpin|encompass|boasts|commence|ascertain|poised to|nascent|burgeoning|streamlin|empower|garner"

# 门 3 短语黑名单 (期望: 无输出; bridge the gap 人工确认 Intro 限 1)
Select-String -Path $Draft -Pattern "worth noting|important to note|(crucial|vital|pivotal) role|in recent years|sheds light|paving the way|not only|wide range of|holds great (promise|potential)|rapidly evolving|in the realm|at its core|when it comes to|bridge the gap|cannot be overstated|valuable insights|new avenues|in conclusion|in today's"

# 门 4 句首评注词密度 (人工确认每节合计 <= 2, 不连续)
Select-String -Path $Draft -Pattern "(^|\. )(Moreover|Furthermore|Additionally|Notably|Importantly|Interestingly|Indeed|Overall), "

# 门 5 -ing 尾巴 (人工复核命中行)
Select-String -Path $Draft -Pattern ", (highlighting|underscoring|ensuring|reflecting|showcasing|demonstrating|emphasizing|fostering|enabling|signifying|contributing) "

# 门 6 Chinglish 高频残留 (期望: 无输出)
Select-String -Path $Draft -Pattern "more and more|and so on| etc\.|there (exist|exists)|it is well known|obviously|our country|at home and abroad|(^|\. )(As for|Regarding) |conduct(ed|ing)? an? (analysis|evaluation|investigation)|carr(y|ied|ying) out|make an? (improvement|comparison|analysis)"

# 门 7 长句审计 (>35 词, 人工拆句或登记豁免)
(Get-Content -LiteralPath $Draft -Raw) -split "[.!?]" | ForEach-Object {
  $words = ($_ -split "\s+" | Where-Object { $_ }).Count
  if ($words -gt 35) {
    "LONG($words): " + $_.Substring(0, [Math]::Min(90, $_.Length)) + "..."
  }
}

# 门 8 项目 claims 红线 (命中 = 人工确认是否否定/限定语境; 否则不合格)
Select-String -Path $Draft -Pattern "clean test|out-of-sample|untouched holdout|final model|best model|state-of-the-art|profitable|tradable|alpha|well-calibrated|statistically significant"
```

### 漂移处置

- 自查发现 ≥3 项不合格 → 本 chunk 判定漂移, 整段重写, 不做逐词补丁。
- 用户指出漂移 → 从最近一个合格 chunk 重新开始, 并在修改日志记录
  漂移原因 (通常是 chunk 过大或未重读本指南)。

---

## 9. 输出格式 (每个 chunk, 沿用 Leey21 三段式)

```text
Part 1 [English]      译文/英文稿本身 (LaTeX 或纯文本, 按目标载体)
Part 2 [中文直译回核]  对 Part 1 的逐句中文直译, 用于用户核对逻辑与强度
Part 3 [修改日志]      中文简述: 拆了哪些长句、替换了哪些词、
                      豁免了哪句及理由、新登记了哪些术语
```

宁缺毋滥原则 (Leey21): 若某段原文/旧译已自然合格, 保留原样并在
Part 3 写明 "[检测通过] 无需修改", 不为改而改。

---

## 10. 与论文工作流的结合 (绑定点)

论文工作流五阶段 (见 docs/agent_capabilities_and_skill_routing.md
第 2、5 节) 与本指南的绑定关系:

| 阶段 | 主导 skills | 本指南绑定点 |
|---|---|---|
| P1 文献与综述 | deep-research, arxiv, firecrawl-research-papers, nature-academic-search | 文献笔记与综述草稿使用第 7 节术语表; 新引用先进入 `paper/references.bib` 且带 provenance |
| P2 结构与初稿 | academic-pipeline, ml-paper-writing, academic-paper | 章节结构与段落逻辑听 skill; 每个经验句先绑定 claims ledger; 每个英文段落走第 1 节三遍流程; 分块上限生效 |
| P3 润色与引用 | quality-editor, nature-polishing | 润色只执行 Pass C, 不碰主张强度与术语; 任何 skill 改写之后必须重跑 grep 门 |
| P4 多视角审稿 | academic-paper-reviewer, ara-rigor-reviewer | 审稿默认只读; 落实审稿意见 = 文本变更 = 重新过 claims ledger 绑定 + Pass B + Pass C + grep 门 |
| P5 图表与成稿 | figure-generation, LaTeX/ACM 模板 | 图注/表注/caption 受相同词汇与句长规则; ACM 模板的格式要求优先于第 6 节 |

核心机制 — prose 静态门 (与 AGENTS.md 的 notebook static gates 同构):
任何 agent 或 skill 产生/修改论文文本后, 按固定顺序过门:

```text
claims ledger 绑定 → 结构 (skill) → 保真 (第 3 节) →
风格 (第 2/4/5 节) → grep 门 (第 8 节) →
不通过: 修复并重检 → 通过: 输出三段式 (第 9 节) 交用户核对
```

skill 输出不豁免: 润色类 skill 自身也会引入 AI 词, 因此 grep 门
始终对最终文本运行, 而不是对 skill 的输入运行。

写作任务的固定阅读链: AGENTS.md → docs/agent_capabilities_and_skill_routing.md
→ 本指南 → paper/outline_and_claims.md → 文档 B/文档 A(按任务需要)
→ 目标 paper section → 所用 skill 的 SKILL.md。

ARS / academic-research-skills 只作为辅助编排模式: 可借鉴
human-in-the-loop、integrity gate、read-only reviewer、claim/citation
verification, 但不得覆盖 AGENTS.md、本地 claims ledger、artifact checksum、
run manifest、no-holdout/test 或本指南的保真规则。

---

## 11. 文档维护

- 本文档是 repo-visible paper contract; 若 `.gitignore` 或远端状态导致
  本文件不可见, agent 必须报告精确路径与 git ignore 规则, 不得假设
  GitHub/Colab 已能读取它。`paper/` 仍是本地论文工作区。
- 修改本文档需用户同意; agent 可在任务中追加第 7 节术语表条目,
  并在修改日志中列出。
- 版本号在文件头注释, 每次实质修改 +0.1。
- 词表代际刷新: AI 高频词随模型代际漂移 (anti-slop 分代统计:
  2023 GPT-4 代 delve/tapestry/pivotal → 2025 代 emphasizing/
  enhance/highlighting/showcasing)。更换主力写作模型或间隔约
  6 个月时, 对照 berenslab excess-words 与社区清单刷新第 2 节
  词表和第 8 节 grep 门。
- 定位声明: 本指南的目标是写作质量 (清晰、平实、可信、保真),
  不是规避 AI 检测器。检测器对非母语作者误报率很高 (Liang et al.
  2023, 报告 >60% 假阳性), 不以任何检测器分数作为验收标准;
  验收标准只有本指南的清单与用户核对。

## 参考来源

- Leey21/awesome-ai-research-writing (中转英/去AI味/润色/逻辑检查 prompts)
- Wikipedia "Signs of AI writing" 风格清单 (25 模式)
- 本地 `ml-paper-writing` / `academic-paper` 工作流 (一段一信息、首句立论、反向大纲)
- Karpinska & Iyyer 2023 (WMT): LLM 段落级翻译优于逐句, 但关键错误
  需句级核对 (arXiv:2304.03245)
- 可读性研究: 平均句长 15–24 词, >25 词理解率陡降 (Oxford Guide to
  Plain English; American Press Institute 数据)
- berenslab/chatgpt-excess-words — Kobak et al., "Delving into
  ChatGPT usage in academic writing through excess vocabulary"
  (1500 万 PubMed 摘要统计, 407 个超额风格词; Tier 3 高信号子集来源)
- conorbronsdon/avoid-ai-writing v3.10 (109 条替换表; 检测器误报
  caveat 引 Liang et al. 2023, Patterns)
- jalaalrd/anti-ai-slop-writing (禁用短语 35+/句首词 16/分代词表)
- nanxstats/llm-cliches (形容词/名词/动词三表, 77 词)
- lguz/humanize-writing-skill (三级分层与 3-pass 编辑结构的交叉验证)
- Carl Gene Fordham "15 Common Mistakes in Chinese-English
  Translation"; Elsevier "Navigating Chinglish Errors in Academic
  English Writing" (中译英专项清单来源)
