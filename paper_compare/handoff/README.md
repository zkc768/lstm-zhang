# handoff/ — the thin interface between Executor and Judge

This folder is the **only** channel between the two roles. Keeping it thin is what
preserves independence (the Judge never sees the Executor's working context) and
prevents conflict (the two roles never write the same file).

- **Executor = Claude Code (本地 CLI).** Owns the repo, runs every gate/compile/git/
  `codex exec`, edits `paper/` + `paper_compare/v2_skill_draft/`. Writes the OUTPUT
  side of this folder.
- **Judge = Cowork (or 网页版).** Fresh-eyes reviewer. Reads ONLY this folder.
  Writes the VERDICT side.

## 铁律 (the one rule that makes it work)

> **Judge 只读 `paper_compare/handoff/`，不读 repo 的其它任何东西。**
> 不读我的设计文档、agent transcript、`REVISION_R2_*`、ledger 的推理部分。
> 它只能看到"成品 + 合同 + 这轮改了啥"。独立性靠"文件夹里没放那些东西"来保证，
> 不靠它自觉。

## 文件清单 (who writes / who reads)

| 文件 | 写 | 读 | 作用 |
|---|---|---|---|
| `CONSTRAINT_CARD.md` | Executor | Judge | 合同：每一步都不可逾越的 presentation 边界 |
| `DESIGN_TO_REVIEW.md` | Executor | Judge | 待审的 workflow-fix 设计（**Mode A 用**） |
| `REVIEW_THIS.pdf` | Executor | Judge | 编译好的论文成品（**Mode B 用**，每轮 pass 后放入） |
| `WHAT_CHANGED.md` | Executor | Judge | 这一轮改了啥 + diff 摘要（**Mode B 用**） |
| `VERDICT.md` | Judge | Executor | 审查结论：pass / 哪几处在 file:line 偏离 |

> `REVIEW_THIS.pdf` 和 `WHAT_CHANGED.md` 现在还没有——它们在第一轮 acceptance pass
> 之后才由 Executor 放进来。现在文件夹里只有 CARD + DESIGN（Mode A）。

## 两种模式 (Judge 干两件不同的事)

- **Mode A — 设计审查（现在做一次）.** Judge red-team `DESIGN_TO_REVIEW.md`：这个
  workflow-fix 设计有没有漏洞？约束卡会不会误伤 floored caveat？结论写进 `VERDICT.md`。
  **这一步在任何 governance 改动之前。**
- **Mode B — 验收审查（以后每轮 pass 做）.** Judge 拿 `CONSTRAINT_CARD.md` 当 rubric，
  审 `REVIEW_THIS.pdf`（像审稿人一样冷读），列出违反约束卡的地方，写进 `VERDICT.md`。

## 日常操作 (从你的座位看，只需"指路"，不搬运内容)

1. 对 **Executor (我)** 说：「跑 §X 这一轮，更新 `paper_compare/handoff/`」。
2. 切到 **Judge (Cowork)** 说：「只读 `paper_compare/handoff/`，按 README 的 Mode A/B
   做，结论写进 `VERDICT.md`」。
3. 回到 **Executor (我)** 说：「读 `handoff/VERDICT.md`，处理里面的偏离」。

> 全程没有大段复制粘贴。若 Cowork 不能写本地文件，它就把 verdict 输出在对话里，你
> 小粘一次（只粘结论）回来给我。

## Judge 的工具边界 (重要 — 保持独立 + 不越界)

**允许**：读本地 md + 读 PDF；一个"审稿/批判"类 skill（见下）；写 `VERDICT.md`。

**禁止**：任何编辑/起草/重写（`prose-polisher`、`section-drafter` 之类）、跑 gate、动
git。**那些是 Executor 的活。** Judge 一旦动手改稿，(1) 独立性没了，(2) 绕过了我的
gate——两个都是红线。Judge 只"判"，不"改"。
