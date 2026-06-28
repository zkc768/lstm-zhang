# Reference workflows & external ideas

Found via browser search (the WebSearch/WebFetch tool is down this session; Chrome was used).
Identifiers are from search-result snippets — verify exact arXiv IDs / authors on the source
page before citing any of these in the paper itself.

## What already maps to our workflow (we independently reinvented much of this)

| Our piece | External reference | What it is | What we can borrow |
|---|---|---|---|
| Per-section draft -> review -> fix loop | **Self-Refine** (Madaan et al., arXiv:2303.17651, NeurIPS 2023); **Reflexion** (Shinn et al. 2023) | the canonical "LLM critiques and revises its own output" method | the name for our loop; its KNOWN limit (below) |
| Multi-agent orchestration (`academic-writing-agents`) | **PaperOrchestra** (Google, arXiv:2604.05018, 2026); **AI Scientist v1/v2** (Sakana, arXiv:2408.06292; Nature 2026) | specialized-agent pipelines: pre-writing materials -> LaTeX manuscript with literature synthesis + generated figures; AI Scientist adds an automated reviewer and v2 passed a real workshop peer review | calibrated automated reviewer; deeper literature-synthesis; conceptual-figure generation |
| De-AI / anti-AI gates | **blader/humanizer** (~16.8k stars, 24 patterns) | Claude Code skill that removes AI-writing signs | already installed; cross-check our gate against its 24-pattern list |
| Anti-homogenization (your #1 worry) | **Perplexity + Burstiness** AI-detection literature | the two core stylometric signals: low perplexity (predictable wording) + low burstiness (uniform sentence rhythm) = "AI-like" | measure these as INTERNAL quality signals (burstiness check now in `check_integrity.py`) |

## NEW ideas worth adopting (the "problems we hadn't fully raised")

1. **Burstiness + perplexity as measurable homogenization signals.** Burstiness (sentence-length
   variance) is now in `check_integrity.py`. Perplexity-variation (how much per-sentence
   predictability varies) is the *other half* — it needs a small language model to compute, so
   it's a future add, not a quick one. Together they turn "is it getting more AI?" from a feeling
   into two numbers we can track across passes.
2. **Different-model critic (now externally validated).** Self-Refine's documented weakness: a
   model critiquing *itself* shares its own blind spots, so gains plateau and it can introduce
   errors. This validates using **Codex (a different model)** for the adversarial review — and
   suggests occasionally running even a per-section writing-review with a different model.
3. **Calibrated reviewer (from AI Scientist).** Their automated reviewer was calibrated against
   human reviewers, and v2 passed a real workshop review. Borrow: calibrate our adversarial
   reviewer to the actual ICAIF rubric, and treat "would this pass review?" as the explicit bar.
4. **Do NOT game detectors (our stance is confirmed correct).** The perplexity/burstiness sources
   note that lowering detector scores can backfire and that detectors false-positive on
   non-native authors. Our existing rule (write well; never target a detector score) is the right
   one — use burstiness/perplexity as internal signals, never as targets.
5. **Provenance / watermark awareness (minor).** 2026 detection also uses C2PA provenance and
   SynthID-style text watermarks. Not a writing-quality issue, but a submission-hygiene note.

## Honest meta-finding
No single existing workflow combines all of what we have: anti-homogenization-by-design +
exemplar-conformance + claims-ledger integrity + anti-laziness verification. The pieces exist
*separately* — Self-Refine is the loop, PaperOrchestra/AI Scientist are the orchestration,
humanizer is the de-AI pass, perplexity/burstiness are the homogenization metric. Our workflow is
a deliberate SYNTHESIS of these for an honest, near-null, claims-bound paper. So there is no
turnkey tool to copy; the concrete upgrades from this scan are: burstiness check (done),
perplexity-variation check (future, needs a model), and the different-model (Codex) critic.

## References (verify IDs before citing)
- Self-Refine: Iterative Refinement with Self-Feedback — arXiv:2303.17651 (NeurIPS 2023).
- The AI Scientist (Sakana AI) — arXiv:2408.06292; v2 / Nature 2026 (passed first-round workshop review).
- PaperOrchestra (Google Research) — arXiv:2604.05018 (2026); repo: github.com/google-research/paper-orchestra.
- blader/humanizer — github.com/blader/humanizer (installed).
- Perplexity & burstiness in AI detection — multiple 2026 explainers (eyesift, gpthumanizer, dev.to/laakash).

---

## PaperOrchestra — architecture & what to adopt (read 2026-06-28)
Five specialized agents, decoupled for parallelism + iterative self-reflection:
- **Outline Agent** (raw materials -> structured plan) ~ our claims ledger + Doc B narrative.
- **Plotting Agent** (conceptual diagrams + statistical plots) ~ our figures + latex-figure-specialist.
- **Literature Review Agent** — web-searches candidates, then **verifies existence/relevance via
  the Semantic Scholar API** and builds a citation graph. API-grounded validation is their
  headline anti-hallucination safeguard.
- **Section Writing Agent** (full LaTeX) ~ our section-drafter / ml-paper-writing.
- **Content Refinement Agent** — iteratively optimizes the draft on **simulated peer-review
  feedback** ~ our Pass-A/B + adversarial review.

Result: beats Single-Agent and AI-Scientist-v2 in blind human SxS (lit-review +50-68%, overall
+14-38%), but a gap vs human ground truth remains. Ethics: assistive tool, humans retain
accountability, programmatic citation validation minimizes hallucination.

**Adopt into our workflow:**
1. **Programmatic citation validation (Semantic Scholar API)** — the verification upgrade: a
   script that checks every `\cite` key resolves to a real paper (existence + title/author/year),
   closing the `references.bib` VERIFY gap and catching hallucinated cites. (Network via `curl`
   works even with WebFetch down.) Status: proposed, not yet built.
2. **Simulated-peer-review-driven refinement** — make Pass-B/C and the milestone review explicitly
   venue-simulated peer review (academic-paper-reviewer / Codex), like their Content Refinement
   Agent, not just generic writing review.
3. **Honest framing** — their "beats AI baselines, gap vs human GT" + human-accountability ethics
   validate our human-in-loop, no-overclaim stance.

## Burstiness / perplexity — how it is actually implemented
Standard method (GPTZero-style; GitHub detectors shreyavenghat25/ai-text-detector,
umairinayat/AI-Detection, etc.): a small LM (GPT-2) computes **per-sentence perplexity**; report
**mean perplexity** (low = predictable = AI-like) and the **stdev of per-sentence perplexity =
burstiness** (low = uniform = AI-like). Our `check_integrity.py` burstiness uses sentence-LENGTH
variance (a lightweight always-on proxy); the proper GPT-2 version is
`paper_compare/perplexity_burstiness.py` (needs `pip install transformers`). Use it as an INTERNAL
signal compared ACROSS passes -- never as a detector-evasion target (detectors false-positive on
non-native authors).
