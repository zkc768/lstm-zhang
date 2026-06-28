# Exemplar KB — design spec (in-design, grilled 2026-06-28)

Upgrades the section-only playbook into a multi-axis, atomic, retrieved-on-demand knowledge base.
Goal: human-written *standard* = matches the human exemplars' patterns + passes a different-model
(Codex) "reads as human academic prose?" audit + burstiness-as-diagnostic (ADR 0001). **Never** a
detector-score target (project rule: do not game detectors).

## DECIDED

### Unit definition (Q3, accepted)
One KB unit = **one atomic, self-contained move/rule**, paraphrased/abstracted. Fields:
- `id` · `statement` (the move, one line) · `why` (one line) · `illustration` (reworded; no
  verbatim lift; any quote <15 words + attributed) · `source` + `genre tag`
  (ICAIF-venue | craft-deflationary) · `axis tags` (logic | prose-rule | style) ·
  `section applicability` · optional `[RED-LINE]` override.
- **Granularity floors:** (1) copyright floor — never finer than an abstracted move; the smallest
  *safe* unit is a move/rule, never a surface sentence template. (2) attention floor — sized so any
  one writing task pulls **<=5 units**.

## PENDING (being grilled)
- Placement in the writing workflow (Q4).
- Axes/file layout + retrieval mechanism (Q5).
- Build sequence — venue exemplar as step 0 (Q6).
