# 论文主张台账 (claims ledger)
<!-- LEDGER_NOTE: 2026-06-26 (contact-basis re-base, 纯措辞, 未训练, 未改任何 canonical 数字):
     作者确认 post-2017 段在 V2.1 walk-forward 之前从未被任何更早工作 (V1 route 或任何 out-of-pipeline
     探索) 接触。故撤回 "V1 route / earlier exploratory work 历史接触 post-2017" 这一事实前提。
     guarded / not-a-clean-test 状态不变, 改 grounding 为两项与"先前接触"无关的事实:
     (1) 读出为对 validation-frozen 主候选的 NON-INDEPENDENT 确认 (expanding-window 跨期共享行;
     固定 5-ticker 幸存者宇宙; 未选最终模型); (2) V2 内 post-2017 holdout 被多次消费
     (run 20260617_051047 早于 bound re-run 20260618_063559_889276) — spent holdout 的二次消费
     (Dwork 2015)。预登记 tier 标签 `guarded_historically_contacted` 与所有冻结产物不变;
     仅更正"为何 guarded"的事实归因。不作 clean-test/out-of-sample 升级。 -->
<!-- LEDGER_VERSION: v1.13 / 2026-06-19 -->
<!-- v1.13: 第四轮对抗审查 (68-agent 工作流, 裁定 GO_WITH_CONDITIONS, 全 LOW) 收口; 纯措辞,
     未训练, 未改任何 canonical 数字:
     [功效更正] 开口事项 E (line ~298): 删去 "Roll 已被哨兵清零分布大幅降权" —— 日内 label-shuffle
     哨兵对 Roll(1984) 买卖价反弹**零功效** (close[t] 同为特征分子 features.py:28 与标签分母 labels.py:28,
     反弹是真行级对齐, 置换只破坏 shuffle 不破坏 observed; 纯反弹世界可通过该哨兵), 故 Roll 仅被
     "dummy floor 跨三分位近恒定" 部分降权, 结算控制 (原始 5min half-spread vs 3bps band) 跑完前保持
     完全 open; 正文 (01_intro.tex:54-56 / C4.5 / 09 limitations) 本已正确, 仅修本行台账括号。
     [措辞] C4.5 (line 214) 与开口事项 #5 (line ~291) 的 up_rate "近恒定" 如实改: dummy floor (~0.500)
     近恒定 → 非类别不平衡; 但 up_rate low0.523>mid0.515>high0.502 是 ~2.1pp 小幅单调梯度 (非恒定)。
     [偏离登记] 预登记 §3 三切片轴 (activity_tercile/time_of_day_hour/calendar_quarter, 两期并列) 中
     guarded 期仅复现 activity_tercile; 另两轴留 validation-only, 已在
     docs/protocols/v2_1_conditional_predictability_preregistration.md 补 dated §9 偏离说明 (论文跨期断言
     本已只限 activity-tercile, 未越界)。
     [文献待办] references.bib 加 Ferrer et al. 2023 (JEF) 作代理级同向先例; related.tex 补 per-foil delta。 -->
<!-- LEDGER_VERSION: v1.12 / 2026-06-20 -->
<!-- v1.12: 证据卫生修复: C1.3 不再引用尚不存在的 Stage 06 run manifest;
     C4.1/C4.2 明确区分本地 Stage 05 派生核验 (report/CSV/manifest) 与 upstream raw
     v2_1_decision_record.json 仍为 Drive-only provenance。纯文档, 未训练, 未改数字。 -->
<!-- LEDGER_VERSION: v1.11 / 2026-06-20 -->
<!-- v1.11: 论文合同治理修复: 本台账确认为数字/主张/证据域最终事实源;
     清理旧 deferred 句 (row-pooled multiplicity/LOO 已由本地 measure-only 镜像覆盖);
     统一 references.bib 残缺条目处理规则。纯文档, 未训练, 未改数字。 -->
<!-- LEDGER_VERSION: v1.10 / 2026-06-19 -->
<!-- v1.10: 第三轮 D 后的 drift/closure 修复 (用户 4-agent 自审发现, 已逐条对源核实):
     [F3 改正错误] label-shuffle 摘要原写"观测 +0.006~+0.041"漏掉 high tercile = -0.0210
     (高于其 shuffle null 但仍为负/低于随机); 已改逐三分位如实 (all +0.006/low +0.041/mid
     +0.006/high -0.021), 哨兵对 high 的含义是"低于随机亦真实、非置换伪影"非"正边际"。
     [F4 拆域] guarded-era 跨期复现 + 伪影排查从 C3.4 (validation 域) 抽出, 新增 C4.5
     (guarded 域) 独立承载, C3.4 仅留交叉引用 — 守"证据域不混写"红线。
     [F5a 合同] v2_1 config outputs 补声明 baseline_predictions: v2_1_baseline_predictions.csv
     (代码确产出且被 Stage05 addenda 消费, 原 outputs 未声明)。
     [F2/F5b/c/F6 对账, 不手改冻结产物] 新增 artifacts/05_thesis_synthesis/RECONCILIATION.md
     做 deferred->closed 对账 + 三 manifest 宇宙(9/10/11)scope 说明 + drive-id/README 已知缺口
     标注; v2_1 协议 line 776 "≤3 periods" 加 Amendment A1(k=7) erratum; Stage05 协议加 dated 闭合注。
     [F1 待办] Stage06 config/notebook + configs/lst_models_pipeline.yaml 仍缺 (优先级 2)。
     纯文档, 未训练。 -->
<!-- LEDGER_VERSION: v1.9 / 2026-06-19 -->
<!-- v1.9: D 收尾 (本会话, measure-only, 关 calm-bar 边际的伪影排查): #5 逐期/逐三分位
     基率 + E 日内 label-shuffle 哨兵 shipped+tested+跑完。#5 (artifacts/05_guarded_base_rates/):
     逐期 delta 仅两个结构断裂期为负 (wf_p4 COVID -0.26pp / wf_p6 bear -0.13pp), 其余 5 期
     +0.6~+1.2pp; 逐三分位 up_rate(low0.523/mid0.515/high0.502) 与 dummy floor(~0.500-0.501)
     近恒定 → calm-bar 边际**非类别不平衡伪影**。E (artifacts/05_label_shuffle_sentinel/):
     日内(ticker,trading_day)置换 50 次, 所有三分位 observed_exceeds_shuffle_max=True (各三分位观测 delta
     all +0.006 / low +0.041 / mid +0.006 / **high -0.021** 均高于各自 shuffle null ~-0.037; high 仍为负
     即低于随机, 仅高于更负的 null — 哨兵对 high 的含义是"低于随机这一结果亦真实、非置换伪影", 非"high 有
     正边际"; null 低于 dummy floor 因候选预测更不平衡, 故判据为"观测清零分布"非"shuffled delta=0") → calm-bar 边际**需真行级标签对齐, 非日内泄漏/日基率伪影**。
     残余: Roll(1984) 买卖价反弹微结构伪影需原始 5min bar (predictions-dump 不可及), 记 limitation。
     两包 sha256sum -c 过; commit f2753dc(feat)/b176f42(evidence)。 -->
<!-- LEDGER_VERSION: v1.8 / 2026-06-19 -->
<!-- v1.8: 第三轮对抗评审 wording 修复 (用户授权, 数字未变, 仅补诚实限定):
     [#3 门槛诚实] C4.1/C4 措辞补注 — 预登记 guarded 门槛实为 positive_period_count
     >= 2/7 AND pooled_delta > 0 (config positive_period_count_minimum:2 + guarded_walkforward.py
     decision 逻辑), 是刻意宽松的稳定性下限 (零假设独立掷硬币下 >=2/7 通过概率 ≈94%);
     5/7 为观测值 (descriptive) 非门槛, "met criteria" 认证的是 >=2/7 bar, force 来自
     pre-registration+方向一致而非门槛严苛; 禁用 5/7 撑 certification 修辞。
     [#4 relabel] C2.3 spread 的 4 行实为 train-inner CONTROL 行 (13_*.csv table_row_id:
     tcn_only / last_step_lightgbm_control / dlinear_only / last_step_mlp, 2/4 为 last-step 退化
     控制), 故 0.66pp 是 control-row spread 非干净 full-family spread, 不得与 full-family
     +1.69pp 验证边际并置成 apples-to-apples; canonical 句式与故事脊柱同步改。
     [shipped, 待跑] 两个 measure-only addendum 已 shipped+tested (synthesis.build_guarded_
     activity_tercile / build_row_pooled_multiplicity_discount; tests/contracts/
     test_synthesis_guarded_addenda.py 4 passed) — 关 #1 跨期条件图谱 / #2 row-pooled 多重性,
     本会话已在冻结 dump (sha256 6481f79/cd6925e 核过) 上跑完 → #1 条件可预测图谱**跨期复现**
     (guarded era low +4.08pp / mid +0.56pp / high -2.10pp, high macro-F1 0.480<0.5, 与 validation
     同向); #2 row-pooled 多重性**结论对估计量稳健** (仅 TCN period-LCB>0 +0.047pp, PBO 0.514 与等权同,
     TCN 中心精确复现 0.006362)。镜像 artifacts/05_guarded_activity_tercile/ +
     artifacts/05_row_pooled_multiplicity/ (sha256sum -c 过)。详见 §3。 -->
<!-- LEDGER_VERSION: v1.7 / 2026-06-19 -->
<!-- v1.7: 绑定 row-pooled LOO 收尾 (最后一个 deferred 项) — 从 raw v2_1_predictions.csv
     行并集本地 measure-only 重算 (shipped+tested synthesis.build_row_pooled_loo, code
     commit ba77d3b; macro-F1 跨行非线性故必须用行级 dump)。baseline 复现 native
     pooled_delta_row_pooled 0.006362; LOO-period 7 扫 (最差 +0.54pp 去 wf_p2) +
     LOO-ticker 5 扫 (最差 +0.51pp 去 CSCO) 两扫 loo_sign_flip=False -> **绑定**估计量
     (非仅等权 companion) 亦不依赖任一期/ticker。镜像 artifacts/05_row_pooled_loo/
     (csv + manifest + README + SHA256SUMS, commit 8f8246c); provenance 由 sha256 链保证
     (input dump sha256 6481f79/cd6925e 经 v2_1 run inventory + 本地副本核验, code sha256
     记于 manifest), 非 Colab run id。C4.4 更新, §3 row-pooled LOO 开口关闭。纯文档
     measure-only, 未训练; paper/ 本地不提交 (Doc A)。 -->
<!-- v1.6: B4 收尾 — Stage 05 重绑到读取 B4 Stage 04 run (20260619_082125_765984,
     含 per-activity-tercile block-bootstrap) 的 run 20260619_090454_562658
     (code commit e2bfba4), 取代 071800_720100。**C3.4 关上**: per-tercile MDE
     (delta - bootstrap_lcb) 现已填: low delta +5.43pp / lcb +4.59pp -> clears;
     mid +1.91pp / lcb +1.10pp -> clears; high -1.54pp 整条 CI 在 0 以下 -> 稳健低于
     随机 (非噪声)。新 run 为 071800 的 clean superset (B6/B8 输出逐字节一致; budget/claim
     仅 Stage 04 run_id 引用更新; selective autopsy 新增 per-tercile MDE)。13 件已镜像
     + sha256sum -c 全过; code_sha256 与仓内 e2bfba4 相符。修了 notebook STAGE04_RUN_ID
     覆盖 config 的 footgun (加 guard test)。纯文档 measure-only, 未训练 (Stage 04 仅
     重算 train-inner 诊断 control, 零 validation/guarded 接触); paper/ 本地不提交 (Doc A)。 -->
<!-- v1.5: 重绑到 Stage 05 B8 re-run 20260619_071800_720100 (code commit 7198df1),
     取代 053750_244288 (新 run 为 clean superset: 5 件 B5/B6/B7 输出与旧镜像逐字节
     一致, 另加 2 件 B8 产物; manifest stage05_synthesis_code_sha256=3bb2abe 与仓内
     7198df1 计算值相符)。13 件已镜像进仓 artifacts/05_thesis_synthesis/20260619_071800_720100/
     (+ SHA256SUMS.txt + README.md, sha256sum -c 全过)。新增 C4.4 (B8): 四估计量并列
     (guarded row-pooled +0.636 / 等权 +0.550pp; validation row-pooled +1.689 / 等权
     terciles +1.935pp; weight_unit 逐行标注, 跨域不可比) + 等权 LOO 两扫均 loo_sign_flip=False
     (period 最差 +0.44pp 去 wf_p2 / ticker 最差 +0.41pp 去 CSCO); 当时 row-pooled LOO
     尚需 raw v2_1_predictions.csv, 已在 v1.7 关闭。既有 C2.1/C3.2/C3.4/C4 数字逐一确认无变。纯文档
     measure-only, 未训练; paper/ 本地不提交 (Doc A)。 -->
<!-- v1.4: 绑定已验证 Stage 05 thesis-synthesis run 20260619_053750_244288 (code commit
     96e91ab)。9 件合成产物已镜像进仓 artifacts/05_thesis_synthesis/20260619_053750_244288/
     + SHA256SUMS.txt (sha256sum -c 全过), 故 C2.1/C3.2/C3.4/C4 的合成数字现仓内可独立核验
     (大文件 03_validation_predictions.csv ~44MB / v2_1_predictions.csv 仍仅 Drive)。既有数字
     经此 run 逐一确认无变: validation macro-F1 0.5170 / Δ +1.69pp; e-AURC 0.330(seed-mean);
     tercile low +5.43 / mid +1.91 / high -1.54 pp, high macro-F1 0.483; guarded row-pooled
     +0.64pp / 等权 +0.55pp / 5-7 / 56 events。新增 C4.3 多重性折扣 (B6): PBO 0.514,
     min_family_lcb -0.46pp, 仅 TCN 主候选 period-LCB 过零。C3.2 补 AUGRC 0.237。纯文档
     measure-only, 未训练; paper/ 本地不提交 (Doc A)。 -->
<!-- LEDGER_VERSION: v1.3 / 2026-06-18 -->
<!-- v1.3: 绑定 C4 (guarded walk-forward 读出) 到已完成 run 20260618_063559_889276:
     decision=met_predeclared_guarded_stability_criteria, pooled_delta (row-pooled,
     协议§8 行并集) = +0.64pp (0.006362), 等权 companion +0.55pp (0.005495),
     positive_period_count=5/7, guarded_scoring_events=56; 状态 Tier-F 占位 -> Tier-G。
     FIX-1 已修 (原 run 20260617 仅报等权)。C3.4 补 tercile 无 bootstrap CI 之 descriptive
     注; 开口事项: 关闭 line "需重训" 占位 (walk-forward 早已运行, 无需重训), 新增阈值/视界
     敏感性 limitation 与 Drive dump 镜像项。本次为纯文档 measure-only 更新, 未触发任何训练。 -->
<!-- v1.2: 按 docs/v2_1_limitation_claim_register_20260617.md (F1) 修正 C3.4
     与故事脊柱措辞: "活跃度"= 每(ticker,trading_day)合格行计数代理(no-trade
     band 代理), 非成交量/流动性; 信号集中在低波动/平静切片, high 切片低于
     随机先验(≈0.483<0.498), 改写为限定条件/局限(非卖点)。数字不变。 -->
<!-- v1.1: 按 multi-perspective review 修复: C2.3 加 train-inner 证据域,
     C3.4 填入实数, stage00 开口事项以 config 出处关闭, 故事脊柱改为
     审稿安全版。 -->
<!-- 规则: 正文每个主张和每个数字必须能在本台账找到行; 本台账是数字、
     主张、证据域、估计量、权重单位的最终事实源。状态=待补 的
     主张只能以文档 B 第 4 节占位策略出现, 但文档 B 不能覆盖本台账事实。数字来源 = artifacts 确切
     文件+字段, 禁止手敲无来源数字。 -->

## 0. 故事脊柱 (审稿安全版)

在 frozen validation split 上, TCN 主候选相对 same-row stratified
dummy 有 +1.69pp macro-F1 的薄提升; 同时 train-inner 控制实验中四个
控制行 (含 2 个 last-step 消融控制) 的 macro-F1 spread 仅 0.66pp (control-row
spread, 非 full-family; 与上句 full-family 验证边际不可 apples-to-apples 并置)。这支持的不是"某模型显著优越",
而是"在防泄漏协议下, 模型家族选择带来的差异小于基线门槛附近的薄信号"。
诊断进一步定位薄信号的兑现条件: 提升集中在低活跃度切片 (+5.43pp),
高活跃切片转负 (-1.54pp, 该切片 macro-F1 ≈ 0.483 低于均衡随机先验
≈ 0.498)。此处"活跃度"= 每 (ticker,trading_day) 合格行计数代理 (no-trade
band 代理), 非成交量/流动性; 低计数由 ±3bps no-trade band 剔除近平样本
所致, 即追踪低波动/平静日。因此薄信号恰恰只在最平静切片兑现, 而在最活跃
(directional call 最需跑赢成本) 切片低于随机 — 这是限定条件/局限, 非卖点。
概率读出 pooled ECE ≈ 0.010 但 Brier resolution ≈ 0.00047 — 校准误差小
不等于置信度排序有用。

证据域纪律 (全文措辞红线): official validation readout (Stage 03,
n=2 seeds) 与 train-inner control comparison (Stage 02/04 diagnostics)
是两个证据域, 任何句子不得混写; 每个对比必须点名其证据域。

**仓内已验证证据包 (canonical, in-repo)**: `artifacts/05_thesis_synthesis/`
`20260619_090454_562658/` (Stage 05 measure-only 合成 run, code commit `e2bfba4`,
读取 B4 Stage 04 run `20260619_082125_765984`,13 件 + sha256 见 `SHA256SUMS.txt`,
`sha256sum -c` 通过)。下文 C2.1 / C3.2 / C3.4 / C4 的
合成数字均可在此包内 `05_*.csv` / `05_thesis_synthesis_report.json` 复核 (字段级出处见各
主张行)。Drive 为 canonical 存储, 此包为小体量 paper-facing 输出镜像; upstream raw
`v2_1_decision_record.json` 本身未作为独立文件镜像入仓, 其 C4 paper-facing 字段由 Stage 05
report/CSV/manifest 重发射; 行级大 dump (`03_validation_predictions.csv` ~44MB,
`v2_1_predictions.csv`) 仍仅 Drive (route guide §11)。

## 1. 数据事实登记 (Setup/§5 用)

| 事实 | 值 | 来源 |
|---|---|---|
| 标的 | CSCO, JPM, KO, MSFT, WMT (5 只美股大盘股) | 05_decision_record per_ticker |
| 频率 | 5 分钟K线 (1 分钟原始数据重采样) | stage00 协议 + 数据指南 |
| 标签 | 二分类方向; band 内行作废剔除 (invalid_no_trade_band) | protocol 00 §标签 (151-160 行) |
| 标签视界与 band | horizon_k = 9 (5分钟bar); no_trade_band_bps = 3.0 | configs/stages/00_data_split_label_freeze.yaml (32-33 行) + protocol 00 |
| 训练样本数 | 736,685 | 04_same_row_dummy_baselines n_train_samples |
| 官方验证样本数 | 151,064 (per-ticker ≈ 29.9k–30.8k) | 04 n_eval_samples + 03 per-ticker |
| holdout 边界 | 2017-01-25 起封闭, 验证阶段零接触 | protocol 00 (124-132 行); stage03 manifest holdout_test_contact=false |
| 训练/验证日期区间 | train 1998-01-02 → 2013-09-16 (end exclusive); validation 2013-09-16 → 2017-01-25 (end exclusive) | configs/stages/00_data_split_label_freeze.yaml (23-27 行) + protocol 00。注: stage00 run_manifest.json 实体不在本地 packet, 仅被 stage03/04 manifest 引用; 如需 manifest 级 provenance 需取回 stage00 run 20260610_051705_347450 |
| 特征集 | price_volume_time (主) / price_action_core (fallback) | 05_decision_record |
| 窗口 | w=20 | 05_decision_record window_size |
| 官方验证种子 | n=2 (101, 202) — 论文必须如实写 n=2 | 05 per_seed_outcomes |
| 设备 | CUDA (refit_records resolved_device) | 05_decision_record |

## 2. 主张清单

### C1 协议 (贡献 1) — 状态: 已有 (Tier-V 可写)

| ID | 主张 (中文工作版) | 证据 | 状态 |
|---|---|---|---|
| C1.1 | 协议组件全部在模型评估前冻结: 标签公式/h/band、切分边界、特征窗口、HPO 空间、预登记判据 | docs/protocols/00–03 + frozen_params | 已有 |
| C1.2 | 预登记判据: Δ(macro-F1) vs stratified dummy > 0 且 vs majority > 0 且 正delta ticker ≥ 3 | 05 predeclared_criteria | 已有 |
| C1.3 | 验证读出不用于模型选择 (official_validation_for_selection=false; no_final_model_selected=true) | `artifacts/05_thesis_synthesis/20260619_090454_562658/run_manifest.json` + `configs/stages/05_thesis_synthesis.yaml`; Stage 06 仅有 config/progress-record contract (`configs/stages/06_ian_final_progress_record.yaml`), 尚无 Stage 06 run manifest | 已有 |

### C2 实证读出 (贡献 2) — 状态: 验证集已有 (Tier-V)

| ID | 主张 | 数字 (canonical) | 证据 |
|---|---|---|---|
| C2.1 | 主候选通过全部预登记判据 | macro-F1 0.5170 ± 0.0009 (n=2); Δ vs stratified dummy 均值 +1.69pp, 最小 +1.63pp; Δ vs majority +18.8pp; 5/5 ticker 正 | 01_seed_summary; 05 |
| C2.2 | dummy 地板量级 | stratified dummy macro-F1 ≈ 0.499–0.501; majority 0.329 | 04 (seeds 101/202) |
| C2.3 | **[证据域: train-inner; 限定: control-row spread, 非 full-family]** train-inner **控制行**的 macro-F1 spread (0.66pp) 小于官方验证的薄边际 (+1.69pp); ⚠️ 这 4 行是 train-inner 控制/消融行 (其中 2 行为 last-step 退化控制), **非** guarded roster 的 full families, 故为 control-row spread, **不得**与 full-family +1.69pp 当 apples-to-apples | train-inner control comparison (n_trials=6/家族, 行=table_row_id): tcn_only 0.5115±0.0026, last_step_lightgbm_control 0.5100±0.0034, dlinear_only 0.5098±0.0070, last_step_mlp 0.5049±0.0050; spread = 0.656pp (跨控制行, min=last_step_mlp 即 last-step 退化控制) | 13_train_inner_model_metric_comparison.csv |
| C2.4 | 主候选身份 | TCN (tcn_tiny, channels [16,16], k=2, lr 1e-3), price_volume_time, w20; fallback LightGBM 未激活 | 05 primary_candidate |
| C2.5 | per-ticker delta 全正但分布不均 | CSCO +2.21pp 最大, JPM +1.00pp 最小 (跨种子均值) | 05 per_ticker_mean_delta |

措辞约束 (Tier-V): 一律 "on the frozen validation split"; 禁
generalize/out-of-sample; n=2 seeds 必须明示; "通过预登记判据"
是事实陈述, 不写成 "证明了有效性"。

C2.3 专用 canonical 句式 (防 scope mixing, 审查轮确定):
"train-inner control comparisons across four control rows (two of
them last-step ablation controls) show a 0.66pp spread, smaller than
the +1.69pp official-validation margin of the TCN primary over the
same-row stratified dummy." 禁止写成 "在 official validation 上
四个模型家族差距小"。

### C3 诊断 (贡献 3) — 状态: 已有 (Tier-V)

| ID | 主张 | 数字 (canonical) | 证据 |
|---|---|---|---|
| C3.1 | 校准误差小但分辨率极低 — 措辞必须带限定: "pooled p_up, equal-mass 10-bin ECE ≈ 0.010", 禁无条件 well-calibrated | pooled ECE (equal-mass, 10 bins) ≈ 0.010; Brier 0.2496, 其中 uncertainty 0.2499 主导, resolution ≈ 4.7e-4 | 08_calibration (seeds 101/202) |
| C3.2 | 置信度排序的选择性增益有限 (诊断, accuracy-based, 无成本/收益; 非操作点) | AURC 0.4717/0.4697 vs oracle 0.1404/0.1406; e-AURC ≈ 0.330 (seed-mean, 两种子 0.3313/0.3291); AUGRC 0.237 (Traub 2024); **fig_risk_coverage 本会话重生成 (trading-day cluster/block bootstrap, 846 days/seed, 1000 reps)**: ΔAURC vs random −0.010 (95% CI [−0.014, −0.006]); gap closed 3.0% (95% CI [1.9, 4.0]%); relAURC 0.970 (95% CI [0.960, 0.982]); partial Δ vs random (high-coverage 受限段) 80–100%=0.25pp / 90–100%=0.14pp / 95–100%=0.07pp; full-coverage errors/seed ≈72.6k (101=72,620 / 202=72,649); n@coverage0.05 = 7,553 | 05_selective_autopsy.csv (activity_tercile=all) @ artifacts/05_thesis_synthesis/20260619_090454_562658 (亦见 09_selective_summary); **CI/partial/cluster-bootstrap 出 paper/figures/fig_risk_coverage_provenance.md (dump sha256 62aeb0c9…, per-seed AURC 对账 ≤5e-4)** |
| C3.3 | **[证据域: train-inner]** 消融: 各家族 gap_to_reference 在 ±0.7pp 内 | tcn_only +0.03pp, dlinear_only -0.14pp, lightgbm -0.12pp, mlp -0.63pp | 07_ablation_summary |
| C3.4 | **关键诊断 (限定条件/局限, 非卖点)**: 薄信号仅在低活跃度(低波动/平静)切片兑现, 在最高活跃度切片低于均衡随机先验。"活跃度"= 每 (ticker,trading_day) 合格行计数代理 (no-trade band 代理), 非成交量/流动性; 低计数由 ±3bps no-trade band 剔除近平样本 → 追踪平静日; 5 只均为大盘股仍流动。high 切片为模型最需跑赢成本的状态却低于随机, 故该集中度是隐忧而非优势 | 活跃度三分位 Δ vs stratified dummy (两种子均值): low +5.43pp (+5.30/+5.57), mid +1.91pp (+1.86/+1.97), high -1.54pp (-1.53/-1.54); high 切片 macro-F1 ≈ 0.483 (0.4823/0.4837) < 随机先验 ≈ 0.498 | 10_robustness_slices (slice_axis=activity_tercile, 计数代理见 src/lst_models/diagnostics.py:113-126) + fig_05。注: 10 还含 calendar_year/quarter/time_of_day_hour 轴可作 §7 补充。**CI (descriptive 呈现, B4 已补)**: tercile delta 现有 per-trading-day block-bootstrap CI (B4 Stage 04 run 20260619_082125_765984 把 activity_tercile 加入 bootstrap 轴); activity_tercile LOO sign-flip=False (跨 LOO 不翻号)。仍按 descriptive 呈现 (bootstrap CI 为不确定带, 非显著性检验)。**B4 已关上 (Stage 05, run 090454)**: `05_selective_autopsy.csv` per-tercile MDE (delta − bootstrap_lcb) 现已填: low delta +5.43pp / lcb +4.59pp → clears; mid +1.91pp / lcb +1.10pp → clears; high −1.54pp 整条 CI 在 0 以下 → **稳健低于随机 (非噪声)**; `delta_clears_mde` = low/mid **True**, high **False** (不再 null); pooled +1.69pp 过其 MDE 0.48pp。即低活跃(平静)边际经 bootstrap 仍过零, 高活跃稳健低于随机 — 条件可预测性两端都有 bootstrap 支撑 (per-tercile MDE 见 `05_selective_autopsy.csv` @ artifacts/05_thesis_synthesis/20260619_090454_562658)。**跨期复现 + 伪影排查属 guarded 证据域 → 见 C4.5** (本 C3.4 行限 official-validation/train-inner 域, 不与 guarded 混写)。 |

### C4 guarded walk-forward 读出 (贡献 2 的升级) — 状态: 已有 (Tier-G guarded readout)

证据域: **guarded non-independent walk-forward** (第三证据域, 区别于 Stage 03
official-validation [n=2] 与 Stage 02/04 train-inner; 任何句子不得与前两域混写)。
run_id `20260618_063559_889276` (v2.1 retrain, fresh single-pass, 56 events, fit 42/56 on cuda)。

| ID | 主张 (中文工作版) | 数字 (canonical) | 证据 |
|---|---|---|---|
| C4.1 | 预登记 TCN 主候选在 guarded 非独立 walk-forward 读出中通过预登记稳定性判据 | decision = met_predeclared_guarded_stability_criteria; **预登记门槛 (bar) = positive_period_count ≥ 2/7 AND pooled_delta > 0** (config positive_period_count_minimum:2 + guarded_walkforward.py decision 逻辑); 此为**刻意宽松的稳定性下限** (零假设独立掷硬币下 ≥2/7 通过概率 ≈94%), 故"met"认证的是 ≥2/7 bar, force 来自 pre-registration+方向一致而非门槛严苛; pooled_delta (row-pooled, 协议§8 行并集) = +0.64pp (0.006362); **positive_period_count = 5/7 为观测值 (descriptive), 非门槛, 禁用 5/7 撑 certification 修辞**; guarded_scoring_events = 56 (7期×4家族×2种子) | Local paper-facing核验: `05_thesis_synthesis_report.json::v2_1_decision/v2_1_pooled_delta_estimands` + `05_validation_budget_ledger.csv` v2_1 row (56 events) + Stage 05 `run_manifest.json::source_v2_1_run_id/input v2_1_decision_record.json`; predeclared bar: `configs/stages/v2_1_guarded_walkforward_readout.yaml::positive_period_count_minimum=2/pooled_delta_positive=true`; upstream raw `v2_1_decision_record.json` remains Drive-only provenance |
| C4.2 | 估计量透明 (FIX-1 已修): 判据 2 绑 row-pooled, 并列等权 companion | pooled_delta_estimand = row_pooled; pooled_delta_row_pooled_available = true; 等权 companion = +0.55pp (0.005495); 原 run 20260617 仅报等权, 本 run 原生算 row-pooled 并绑定 | `05_estimand_contrast.csv` + `05_thesis_synthesis_report.json::v2_1_pooled_delta_estimands` @ `artifacts/05_thesis_synthesis/20260619_090454_562658/`; upstream raw `v2_1_decision_record.json` remains Drive-only provenance |
| C4.3 | **[多重性折扣 B6, descriptive — 非显著性检验]** guarded 4家族×7期 delta 的多重比较折扣: CSCV PBO ≈ 0.51 (近掷硬币, 即"挑最佳家族"有实质 backtest-overfitting 概率); 仅预登记 TCN 主候选 period-LCB 过零, 最差/中位家族 LCB 为负 → 家族边际在多重性下脆弱 | PBO 0.514 (CSCV odd-block floor/ceil, 35 组合, 4 trials, 7 blocks); per-family mean Δ / period-LCB: LightGBM +0.70pp / -0.03pp, MS-DLinear+TCN +0.61pp / -0.02pp, **TCN-primary +0.55pp / +0.05pp (唯一过零)**, Std-DLinear +0.42pp / -0.46pp; min_family_lcb -0.46pp, median_family_lcb -0.03pp, max_family_mean +0.70pp | 05_multiplicity_discount.csv @ artifacts/05_thesis_synthesis/20260619_090454_562658 (Bailey et al. 2017 CSCV/PBO)。**估计量稳健性补 (第三轮, 本会话已跑)**: 上述 PBO/LCB 跑在**等权 companion** (TCN mean_delta 0.005495); 在**绑定 row-pooled** 估计量上重算 (`artifacts/05_row_pooled_multiplicity/`, sha256sum -c 过) 结论不变 — 仅 TCN-primary period-LCB 过零 (+0.047pp), PBO 0.514 (与等权同, CSCV 块结构对估计量不变), min_family_lcb -0.46pp, TCN 中心 mean_delta 精确复现 pooled_delta_row_pooled 0.006362 |
| C4.4 | **[估计量透明 + 稳健性 B8, descriptive]** 头条 macro-F1 Δ 同时随聚合方式与证据域而变, 四估计量并列呈现, 任一不得当作"那个数"; 且 guarded 边际 (等权 companion **与**绑定 row-pooled 两版) 对去任一期/任一 ticker 均不翻号 | **四估计量** (各注 weight_unit, 跨域不可比): guarded row-pooled +0.636pp (binding) / 等权(7期) +0.550pp; validation row-pooled(全行) +1.689pp / 等权(3 terciles, regime-balanced) +1.935pp。**等权 LOO** (主候选 TCN): LOO-period 7 扫 `loo_sign_flip=False` (最差 +0.44pp 去 wf_p2, 最敏感 wf_p4); LOO-ticker 5 扫 `loo_sign_flip=False` (最差 +0.41pp 去 CSCO, 最敏感 CSCO)。**绑定 row-pooled LOO 已补 (本地 measure-only 算 + 镜像)**: 从 raw v2_1_predictions.csv 行并集重算 (macro-F1 跨行非线性), baseline 复现 native pooled_delta_row_pooled 0.006362; LOO-period 7 扫最差 +0.54pp (去 wf_p2), LOO-ticker 5 扫最差 +0.51pp (去 CSCO), 两扫 `loo_sign_flip=False` | 05_estimand_contrast.csv + 05_loo_robustness.csv (等权) @ artifacts/05_thesis_synthesis/20260619_090454_562658; **绑定 row-pooled LOO** @ artifacts/05_row_pooled_loo/ (05_row_pooled_loo.csv + manifest, input dump sha256 经 v2_1 run inventory 核验; guarded 值出 v2_1_decision_record pooled_delta_row_pooled/equal_weight; validation 值出 05_selective_autopsy all/terciles seed_mean delta_vs_dummy) |
| C4.5 | **[证据域: guarded walk-forward; 条件可预测性跨期复现 + 伪影排查; descriptive 限定/局限, 非卖点]** C3.4 的条件可预测图谱 (平静切片有边际、最活跃切片低于随机) 在 2017-2024 guarded era 复现, 并经基率 + 日内置换哨兵排除两类伪影 (残余 1 项 deferred) | guarded-era 三分位 Δ vs same-row dummy (TCN primary, seed-mean): low +4.08pp / mid +0.56pp / high **-2.10pp** (high macro-F1 0.480 < 随机先验 0.5; 'all' +0.636pp 精确 = 绑定 row-pooled), 与 validation-era (low +5.43 / mid +1.91 / high -1.54) 同向。**伪影排查**: (a) 逐三分位 dummy floor (~0.500) 近恒定 → 非类别不平衡伪影; up_rate (low0.523>mid0.515>high0.502) 为 ~2.1pp 小幅单调梯度 (非恒定); (b) 日内 label-shuffle 50 置换所有三分位 observed_exceeds_shuffle_max=True (各观测高于各自 shuffle null ~-0.037; **high 仍 -0.021 即低于随机, 仅高于更负 null** → 哨兵证其"低于随机"亦非置换伪影, 非正边际) → 非日内泄漏/日基率伪影; (c) 逐期仅 wf_p4(COVID)/wf_p6(bear) 为负 | artifacts/05_guarded_activity_tercile/ + 05_guarded_base_rates/ + 05_label_shuffle_sentinel/ (各 sha256sum -c 过); guarded 三分位本地 measure-only 重算, input dump sha256 6481f79/cd6925e 经 v2_1 run inventory 核验。**残余 deferred**: Roll(1984) 买卖价反弹微结构伪影需原始 5min bar (predictions-dump 不可及), 写作记 limitation。措辞继承 C4 Tier-G guarded 红线 (no clean-test / no-final-model) |

措辞约束 (Tier-G, 投稿红线): 一律 "the predeclared TCN primary met the predeclared
guarded stability criteria in a non-independent walk-forward readout"; 必带
"guarded / non-independent"; no_final_model_selected=true 保持; LightGBM 在
walk-forward 数值最高但禁写 best/selected/superior; 禁 clean test / out-of-sample proof /
holdout-ready / 最终模型。此 walk-forward 即 Ian 邮件要求的 "2-3 额外 holdout 期稳定性
检验" 的落地 (实为 7 期), 但属 **guarded 非独立确认, 非 clean holdout** — C4 措辞不得暗示干净外测。
注 (复现): C4 的**合成数字/论文面字段** (row-pooled/等权/positive periods/56 events +
C4.3 PBO/min_family_lcb + C4.4 四估计量/等权 LOO/绑定 row-pooled LOO + C4.5 guarded 三分位)
现已由仓内 Stage 05 派生镜像覆盖: `artifacts/05_thesis_synthesis/20260619_090454_562658/`,
`artifacts/05_row_pooled_loo/`, `artifacts/05_row_pooled_multiplicity/`,
`artifacts/05_guarded_activity_tercile/`, `artifacts/05_guarded_base_rates/`,
`artifacts/05_label_shuffle_sentinel/` (各自 SHA256SUMS 或 manifest 记录)。upstream raw
`v2_1_decision_record.json` 与原始行级 dump (~569MB v2_1_predictions.csv + Stage 03 ~44MB 验证 dump) 仍仅 Drive, 但不再是
row-pooled LOO/multiplicity 写作依赖; 它只保留为可选的行级原始独立复现材料。措辞约束 (B6): PBO/LCB 为 descriptive 折扣,
非显著性检验; LightGBM 数值最高但禁 best/selected/superior; TCN period-LCB 唯一过零仅作
"预登记主候选更具周期稳健性"之事实陈述, 不写成择优。
**(第三轮补 #3 门槛诚实)** C4 任何 "met predeclared criteria / 5/7" 句必须同时可读到
门槛 bar = ≥2/7 正期 + 正均值 (弱稳定性下限, 零假设 ≈94% 通过); 5/7 仅 descriptive 观测值。
**(第三轮补 #2 估计量对齐)** 现仓内 `05_multiplicity_discount.csv` (PBO 0.514 / per-family LCB)
跑在**等权 companion** 估计量 (TCN mean_delta=0.005495), **非**绑定 row-pooled (+0.636pp);
引用多重性折扣时须注明其为等权 companion, 或优先改引已完成的 binding row-pooled
版 (`artifacts/05_row_pooled_multiplicity/`, `SHA256SUMS.txt` 已覆盖小派生表)。

## 3. 开口事项 (写作前/投稿前必须关闭)

```text
[x] h 与 no_trade_band_bps 确数 — 已关闭 (审查轮): horizon_k=9,
    band=3.0bps ← configs/stages/00_data_split_label_freeze.yaml
[x] 训练/验证日期区间确数 — 已关闭 (审查轮): 1998-01-02/2013-09-16/
    2017-01-25 ← 同上 config + protocol 00 (来源改为 config, 因
    stage00 run manifest 实体不在本地 packet)
[x] C3.4 活跃度三分位数字 — 已关闭 (审查轮): low +5.43 / mid +1.91 /
    high -1.54 pp ← tables/10
[ ] references.bib 投稿前 publisher-page 逐条核验: 年份/卷期/页码/
    DOI/publisher 补全 (When Alpha Disappears / FINSABER / Brier /
    Murphy 已登记; 多条 proceedings 仍可能缺 DOI/pages, 草稿可用, 投稿不可用)
[x] papers/README.md 中 zhu2022/hu2023/su2025 作者不完整 —
    已从 references.bib 移除; 如需引用, 必须先补全 publisher/source provenance 后重登
[ ] (可选) 取回 stage00 run 20260610_051705_347450 的
    run_manifest.json 到本地, 升级日期/标签出处为 manifest 级
[x] C4 walkforward 已运行并绑定 — 已关闭 (v1.3): run 20260618_063559_889276
    (row-pooled +0.64pp, 5/7 positive, 56 events, met); walk-forward 早已跑过且本轮
    已重训, **无需重训** (此前"需重训"为跑前占位, 已驳)
[x] Stage 05 合成产物镜像进仓 — 已关闭 (v1.6): artifacts/05_thesis_synthesis/
    20260619_090454_562658/ (13 件 + SHA256SUMS.txt + README.md, sha256sum -c 全过, code
    commit e2bfba4; 读 B4 Stage 04 run; 含 B6/B7/B8 + per-tercile MDE; 取代 071800 superset
    镜像); C2.1/C3.2/C3.4/C4 合成数字现仓内可独立核验
[x] B8 四估计量对照 + 等权 LOO-period/LOO-ticker — 已关闭 (v1.5, C4.4): 等权两扫
    loo_sign_flip=False; 原 v1.5 deferred 的绑定 row-pooled LOO 已由 v1.7 关闭 (见下条)
[x] B4 activity-tercile block-bootstrap — 已关闭 (v1.6, C3.4): Stage 04 run
    20260619_082125_765984 把 activity_tercile 加入 bootstrap 轴; per-tercile MDE 现已填,
    low/mid clears(lcb>0)、high 整条 CI<0(稳健低于随机); delta_clears_mde 不再 null。
    measure-only(Stage 04 仅重算 train-inner 诊断 control, 零 validation/guarded 接触)
[x] 绑定 row-pooled LOO — 已关闭 (v1.7, C4.4): 从 raw v2_1_predictions.csv 行并集
    本地 measure-only 重算 (shipped synthesis.build_row_pooled_loo, code commit ba77d3b),
    baseline 复现 0.006362, 两扫 loo_sign_flip=False; 镜像 artifacts/05_row_pooled_loo/
    (input dump sha256 经 v2_1 run inventory + 本地副本双重核验)
[ ] (复现, 投稿前, 已降级且非必需) 原始 656MB 行级 dump 本身仍仅 Drive
    (v2_1_predictions.csv ~569MB + baseline ~117MB + Stage 03 ~44MB); 设计上不入 git
    (route guide §11)。所有 C4 合成数字 + row-pooled LOO 已由小派生表镜像覆盖且 sha256
    可溯, 故此项仅为可选的行级原始独立核验, 投稿前按需
[x] (#1 跨期条件图谱, 第三轮 high) — 已关闭 (本会话已跑): guarded-era activity-tercile 图谱经
    synthesis.build_guarded_activity_tercile 在冻结 v2_1 dump (sha256 6481f79/cd6925e 核过) 上
    measure-only 算出 → **条件可预测性在 2017-2024 guarded era 复现**: low +4.08pp / mid +0.56pp /
    high -2.10pp (high macro-F1 0.480 < 随机先验 0.5), 与 validation-era (low +5.43 / mid +1.91 /
    high -1.54, macro 0.483) 同向; 'all' delta +0.636pp 精确 = 绑定 row-pooled。镜像
    artifacts/05_guarded_activity_tercile/ (csv+manifest+README+SHA256SUMS, sha256sum -c 过)。
    → 正文 condition-map 现可写成跨期成立, 不再受"validation-era only"限制 (但仍 descriptive, 活跃度=行计数代理非流动性)
[x] (#2 row-pooled 多重性, 第三轮 medium) — 已关闭 (本会话已跑): synthesis.build_row_pooled_
    multiplicity_discount 在**绑定 row-pooled** 估计量上重算 → 结论对估计量稳健: 仅 TCN-primary
    period-LCB 过零 (+0.047pp), PBO 0.514 (与等权版同, CSCV 块结构对估计量不变), min_family_lcb
    -0.46pp; TCN 中心 mean_delta 精确复现 pooled_delta_row_pooled 0.006362。镜像
    artifacts/05_row_pooled_multiplicity/ (sha256sum -c 过); 引用多重性折扣时可改引此 row-pooled 版
[x] (#5 基率/regime composition, 第三轮 D) — 已关闭 (本会话已跑): synthesis.build_guarded_base_rates
    → 逐期 delta 仅 wf_p4(COVID)-0.26pp / wf_p6(bear)-0.13pp 为负, 其余 5 期 +0.6~+1.2pp;
    逐三分位 dummy floor(~0.500)近恒定 → calm-bar 边际非类别不平衡伪影; up_rate(low0.523>
    mid0.515>high0.502)为 ~2.1pp 小幅单调梯度(非恒定)。镜像 artifacts/05_guarded_base_rates/ (sha256sum -c 过)
[x] (E calm-bar 真信号 vs 伪影哨兵, 第三轮 D) — 已关闭 (本会话已跑, 残余 1 项 deferred):
    synthesis.build_guarded_label_shuffle_sentinel (日内置换 50 次) → 所有三分位
    observed_exceeds_shuffle_max=True (观测边际清零分布) → 非日内泄漏/日基率伪影。镜像
    artifacts/05_label_shuffle_sentinel/ (sha256sum -c 过)。**残余 deferred**: Roll(1984) 买卖价
    反弹微结构伪影需原始 5min bar / half-spread vs 3bps band (predictions-dump 不可及), 写作时
    记为 limitation (不阻断)。**[v1.13 功效更正]** 日内 label-shuffle 哨兵只排除行级泄漏/边际(基率)
    伪影, 对 Roll 买卖价反弹**零功效** (close[t] 同为特征分子与标签分母, 反弹属真行级对齐, 置换只破坏
    shuffle 不破坏 observed; 纯反弹世界可通过该哨兵) → Roll 仅被 "dummy floor ~0.500 跨三分位近恒定"
    部分降权, **未**被哨兵降权, 结算控制 (原始 5min half-spread vs 3bps band) 跑完前保持完全 open
[x] (写作 limitation, 一句话) — 已写入 paper/sections/09_limitations_conclusion.tex (v1.13):
    单一 no-trade band=3.0bps / horizon h=9 (预注册冻结值), 未做阈值/视界敏感性扫描,
    诚实声明为预注册冻结导致的 limitation, **未作新实验**
[ ] 投稿前删除 main.tex 的 skeleton 痕迹检查 (titlenote 已移除,
    见文档 A §7 盲审门新增 grep)
```

## 4. 与文档体系的关系

- 本台账是数字、主张、证据域、估计量、权重单位、source artifact 的最终事实源。
  文档 B 第 4 节只管 prose 分级与占位策略, 不覆盖本台账事实。
- agent 可更新: 状态列、开口事项勾选、新增主张行 (需在修改日志
  列出); 删除或改写既有主张需用户同意。
- 数字修约规则按文档 A 第 9 节 (百分点 1 位小数; 表内 mean±std)。
