# Figure Generation Brief (handoff for Codex)

Goal: produce the 4 publication figures for the `lst_models` ICAIF/ACM paper as
**vector PDFs in `paper/figures/`**, regenerated from in-repo artifact CSVs, so
that `paper/main.tex` compiles with real figures instead of the current `\fbox`
placeholders.

Repo root in all paths below = the `lst_models` project root.

---

## 0. Tool decision: matplotlib, NOT Origin (read first)

Use **matplotlib (Python), importing `paper/scripts/style.py`, saving vector PDF
to `paper/figures/`.** Do **not** use OriginLab or any GUI/hand-drawn tool. Reasons,
specific to this project:

1. **It is the documented contract.** `paper/scripts/style.py` docstring (Doc A
   section 4): *"Every figure script imports from this module and saves vector PDF
   into `paper/figures/`. Figures are regenerated from `artifacts/` data only; no
   hand-edited or notebook-copied images."* An Origin GUI workflow violates this
   directly (manual, hand-edited, not regenerable).
2. **Reproducibility is the paper's thesis.** The paper's entire contribution is an
   auditable, leak-controlled, regenerable evaluation pipeline. A non-scriptable
   manual figure step contradicts the claim a reviewer is being asked to trust.
3. **The pipeline already exists.** A shared style (Okabe-Ito palette, sigconf
   widths, 300 dpi, embedded fonts) is in `paper/scripts/style.py`, and matching
   exemplar PDFs already exist in `artifacts/ian_email_packet_20260611/figures/`.
   Reuse that toolchain; do not start a parallel one.
4. **All data is small CSV.** Every figure's data (except one curve, see Fig 3)
   is an in-repo CSV of a few rows. No reason to leave the scripted path.

Origin would only make sense if the project were abandoning the reproducible-pipeline
ethos, which is exactly what the paper sells. So: matplotlib.

Output format: **vector PDF** (`pdf.fonttype 42`, already set in the style), one
file per figure, exact filenames in section 3. ACM `acmart` wants PDF/EPS vector.

---

## 1. Hard rules (do not violate)

- **Data provenance:** plot only values that exist in the cited artifact CSV. Do
  NOT invent, smooth, or re-estimate numbers. If a value is missing, stop and say so.
- **Captions are already written** in the `.tex` files (section 3 lists which).
  The figure content must MATCH its caption; do not add a claim the caption does
  not make.
- **Forbidden framings** (same red lines as the prose): never imply a model is
  "best/superior", never imply "significant", "clean test", "tradable/profitable",
  or "well-calibrated". The risk-coverage figure is "accuracy-based; no cost model;
  no operating point". `LightGBM` is never crowned.
- **"activity" = per-(ticker, trading-day) eligible-row-count proxy under the
  no-trade band, NOT volume / liquidity / volatility.** This qualifier must appear
  in the activity-tercile figure (caption already says it; do not contradict).
- **Evidence domains stay labeled and separate:** official validation (n=2 seeds)
  vs guarded historically-contacted walk-forward. The tercile figure shows both and
  must label which is which; never merge them into one bar.
- **Fixed colors:** use the semantic `PALETTE` mapping from `style.py`
  (`validation` = teal, `guarded` = mauve, dummy/baseline = grey) and keep it
  consistent across figures.
- **No chartjunk:** no 3D, no gradients, no background fill; top/right spines off
  (style already does this); a single light grid; a zero-reference line where deltas
  are plotted.

---

## 2. Shared style + output contract

Every script starts with:

```python
import sys; sys.path.insert(0, "paper/scripts")
from style import apply_paper_style, FIG_WIDTH_1COL, FIG_WIDTH_2COL, OKABE_ITO
apply_paper_style()
```

- Width: default **1-column = `FIG_WIDTH_1COL` (3.33 in)** to match the
  `\begin{figure}[t]` environments in the sections. Height: pick per figure, keep
  it compact (roughly 2.0--2.4 in).
- Save: `fig.savefig("paper/figures/<name>.pdf", bbox_inches="tight", pad_inches=0.02)`.
- Run from the repo root so the relative `artifacts/...` and `paper/figures/...`
  paths resolve.

---

## 3. The four figures

Filenames are fixed by the `\includegraphics` paths already in the `.tex`. Produce
exactly these four PDFs.

### Fig 1 — `paper/figures/fig_protocol_timeline.pdf`
- **Referenced in:** `paper/sections/03_protocol.tex`, `\label{fig:protocol-timeline}`
  (read the caption there and match it).
- **Type:** schematic timeline (no CSV; values below). A horizontal time axis with
  three contiguous era bands and an annotation.
- **Content:**
  - Train: `1998-01-02` to `2013-09-16` (n_train = 736,685 rows).
  - Official validation: `2013-09-16` to `2017-01-25` (n_val = 151,064; n=2 seeds).
  - Holdout: closed from `2017-01-25` (zero validation-phase contact) — draw distinct
    (e.g. hatched/greyed) to signal "closed".
  - Over the post-2017 span, draw the **guarded, historically-contacted walk-forward**
    as 7 consecutive period ticks (2017--2024). Label it "guarded (historically
    contacted), not a clean test".
  - A "frozen before readout" marker at the train/validation boundary: label, no-trade
    band, splits, model roster, predeclared criteria frozen before the first score.
- **Style:** dummy/grey for closed holdout, tcn-blue accent for the frozen arrow;
  small text labels; no data axis numbers needed beyond the dates.

### Fig 2 — `paper/figures/fig_validation_deltas.pdf`
- **Referenced in:** `paper/sections/06_results.tex`, `\label{fig:validation_deltas}`.
- **Data:** Panel A reads
  `artifacts/ian_email_packet_20260611/tables/03_official_validation_per_ticker_readout.csv`,
  column `delta_macro_f1_vs_stratified_dummy_train_prior`, per ticker, averaged over
  the two seeds (101, 202). Cross-seed means (in pp), descending:
  - CSCO +2.21, KO +1.96, MSFT +1.79, WMT +1.42, JPM +1.00  (all 5 positive).
  - Overall (row-pooled) first row at +1.69 pp.
  Panel B reads `artifacts/05_guarded_base_rates/05_guarded_base_rates.csv`,
  `scope=period`, period labels `2017–18` through `2023–24`; seed means (in pp):
  +0.92, +1.20, +0.74, -0.26, +0.60, -0.13, +0.77.
  - Overall (row-pooled) guarded first row at +0.64 pp.
- **Type:** single-column A/B forest/dot-interval figure. Panel A =
  prespecified validation by ticker; Panel B = guarded secondary analysis by
  evaluation period. Both panels share the x-axis range -1.5 to +3.5 pp, with
  ticks at -1, 0, 1, 2, and 3 so negative intervals are not clipped. The
  first row in each panel is the row-pooled overall estimate, separated from the
  subgroup rows by a light rule. Capped whiskers are unadjusted 95% block-bootstrap
  intervals conditional on the fixed seeds; circle and diamond markers are seeds
  101 and 202 where seed-specific subgroup values exist; filled squares are
  domain-colored means of two fixed seeds (validation teal, guarded mauve), with
  both colors explained in the legend. Legend order should read visually as
  `Validation mean | Guarded mean | 95% block-bootstrap CI`, then
  `Seed 101 | Seed 202`; the CI legend handle should be a horizontal interval
  with two end caps. Draw a dashed zero line only. Do not draw
  dotted row-pooled reference lines and do not place CSCV PBO or LCB annotations
  inside this figure.
- **Caption already says:** filled squares are arithmetic means across seeds
  101 and 202; seed markers are descriptive subgroup estimates, not confidence
  intervals; row-pooled rows are computed by pooling rows within seed then
  averaging seed deltas, and seed markers are omitted on those rows unless a
  source artifact provides audited pooled seed-specific estimates for both
  domains; the block-bootstrap intervals are descriptive, unadjusted,
  conditional on fixed seeds, and do not include between-seed variability;
  positive values favor the model over the stratified-random baseline; all
  prespecified tickers and periods are shown; evidence domains are separate; and
  the guarded panel is a historically contacted secondary descriptive analysis,
  not a clean test, significance test, or model-selection ranking.
  Match it.

### Fig 3 — `paper/figures/fig_risk_coverage.pdf`  (DATA CAVEAT — read)
- **Referenced in:** `paper/sections/08_diagnostics.tex`, `\label{fig:risk_coverage}`.
- **Type:** two-panel accuracy-based selective-risk--coverage diagnostic:
  prespecified confidence score vs perfect-ranking oracle, plus a compact
  random-minus-score selective-risk difference panel, seed mean.
- **CAVEAT:** the in-repo CSV `09_validation_selective_summary.csv` has only the
  **summary scalars**, not the full curve: AURC 0.4717/0.4697 (oracle 0.1404/0.1406),
  e-AURC 0.3313/0.3291, full-coverage risk 0.4807/0.4809 (seeds 101/202). The
  horizontal reference is the expected risk under random ranking, equal to
  full-coverage risk. The risk-reduction panel should show
  `100 * (full_coverage_risk - selective_risk_score)` so the near-random
  magnitude is visible. The per-coverage curve needs the validation
  **predictions dump** (`03_validation_predictions.csv`,
  Drive-only, ~44 MB). Two acceptable options:
  1. **Preferred (reuse):** the curve was already rendered at
     `artifacts/ian_email_packet_20260611/figures/fig_04_selective_risk_coverage.pdf`.
     Re-style it to the paper width/fonts if its source script is available
     (look in `src/lst_models/diagnostics.py` / `stages/diagnostics_ablation.py` for
     the risk-coverage plot function and the curve arrays), or copy it into
     `paper/figures/fig_risk_coverage.pdf` if a faithful regenerate is not possible
     in-repo, and note the provenance.
  2. **Regenerate from the dump (PREFERRED — gives a figure consistent with the
     other three).** The dump is NOT in the repo (Drive-only, route guide section 11).
     Acquire and reproduce exactly as follows.

     **Drive location** (proven by the Stage 05 mirror `run_manifest.json` fields
     `source_stage03_run_id` + `input_artifacts`):
     - Drive path: `My Drive/lst_models/results/03_frozen_validation_readout/20260610_133305_716174/03_validation_predictions.csv`
     - Colab runtime path (manifest-recorded): `/content/lst_models_results/03_frozen_validation_readout/20260610_133305_716174/03_validation_predictions.csv`
     - Stage 03 `run_id = 20260610_133305_716174`. ~302,128 rows (151,064 eval rows x
       2 seeds), ~44 MB. There is NO in-repo Drive file ID for this dump; open that
       run folder on Drive (or read its own `drive_backup_manifest.json` there) for
       the file ID if using the Drive API. **Keep the file OUT of git** (route guide
       section 11); read it from an absolute path / argument, not a committed location.

     **Exact schema** (column order is gated fail-closed in `diagnostics.py`
     `DUMP_COLUMNS`):
     `candidate_role, candidate_id, model_family, hpo_profile_id, seed, sample_id,
     ticker, target_timestamp, trading_day, y_true, p_up, y_pred, scope`.
     All rows: `candidate_role=primary`, `scope=validation_only`, `seed in {101,202}`.

     **Reproduce the curve as the pipeline did** (`diagnostics.py:107-108` +
     `metrics.py`):
     - `correct = (y_pred == y_true)` (use the dump's own `y_pred`).
     - `confidence = metrics.top_label_confidence(p_up)` = `max(p_up, 1 - p_up)`.
     - Accept rows by descending confidence. Per seed:
       `metrics.risk_coverage_curve(confidence, correct, tie_break=sample_id)`
       returns `coverage, n_covered, confidence_at_coverage, selective_risk
       (= 1 - cumulative_accuracy), selective_accuracy`; risk is ACCURACY-based, which
       matches the caption. Then `metrics.aurc_metrics(...)` for AURC / oracle / e-AURC.
       Average the two per-seed curves for the seed-mean panel. Use the SAME `tie_break`
       and per-seed-then-mean aggregation as the call site in
       `src/lst_models/stages/diagnostics_ablation.py` so the numbers reconcile.
     - **Reconciliation gate (proves the dump is correct):** per-seed AURC must
       reproduce `09_validation_selective_summary.csv`: AURC 0.47173 (s101) /
       0.46970 (s202); oracle 0.14043 / 0.14056; e-AURC 0.33130 / 0.32914. Match to
       ~1e-4 before plotting.
  - Put AURC values in the legend only; do not place e-AURC, gap-closed, or
    AUGRC text inside either plotting axis. Draw the perfect-ranking oracle
    curve and an expected-random-ranking reference line (= full-coverage risk,
    and equal to random-ranking AURC under the constant reference).
    Caption: accuracy-based 0/1 selective error, no cost model, no operating
    point; abstention removes the high-activity bars. Match it.
  - Add descriptive bands only when the full dump is available: paired
    trading-day cluster (block) bootstrap bands for the score curve/difference panel, plus a
    random-row-ordering permutation band around the expected-random-risk line.
    Bands are official-validation row/day uncertainty summaries, not seed-level
    significance tests.
  - Do **not** annotate AUGRC inside the selective-risk axes. If AUGRC is
    reported, put it in caption/prose and state that it is computed from the
    generalized-risk--coverage curve, not from the displayed selective-risk
    curve.
  - Markers are display-only at selected coverage levels; AURC values are
    computed from the complete ranked prediction sequence.
  - Coverage zero is display-only context: selective risk starts at `1/n`, so
    `c=0` is not part of AURC.
  - The lower panel is random-minus-prespecified selective-risk difference in
    percentage points. Avoid "risk reduction" wording in the axis label because
    this is a descriptive ordering diagnostic, not a causal risk-reduction claim.
  - Save `paper/figures/fig_risk_coverage_source.csv` with the displayed
    curves, bootstrap bands, and permutation bands; save
    `paper/figures/fig_risk_coverage_scalar_summary.csv` with the global AURC,
    gap-closed, AUGRC, and high-coverage partial summaries. Record SHA256 values
    in the provenance note.
  - Even with bootstrap/permutation bands, do not describe the small AURC gap as
    significant or statistically reliable with only two training seeds.
  - **Fallback** (only if the 44 MB dump cannot be obtained): reuse the already-rendered
    `artifacts/ian_email_packet_20260611/figures/fig_04_selective_risk_coverage.pdf`,
    and note in the caption/commit that it is the older notebook-style render (visually
    inconsistent with the other three figures).

### Fig 4 — `paper/figures/fig_tercile_map.pdf`  (REGENERATE — paired diverging grouped bars with seed overlay, both eras)
- **Referenced in:** `paper/sections/08_diagnostics.tex`, `\label{fig:tercile_map}`.
  This supersedes the validation-only `fig_05_activity_tercile_delta` — the paper
  needs **both eras side by side**.
- **Data (delta vs same-row dummy, pp):**
  - Validation (`artifacts/05_thesis_synthesis/20260619_090454_562658/05_selective_autopsy.csv`,
    rows `activity_tercile in {low,mid,high}`, `seed=seed_mean`, col `delta_vs_dummy`):
    low +5.43, medium +1.91, high -1.54. Seed-specific rows for 101 and 202
    are in the same artifact and must be overlaid as raw points.
  - Guarded (`artifacts/05_guarded_activity_tercile/05_guarded_activity_tercile.csv`,
    `seed=seed_mean`, col `delta_vs_dummy`): low +4.08, medium +0.56, high
    -2.10. Seed-specific rows for 101 and 202 are in the same artifact and must
    be overlaid as raw points.
  - High-tercile macro-F1: validation ~0.483, guarded 0.480; balanced random prior
    ~0.498--0.500.
  - Seed-mean row counts for low/medium/high groups: validation
    44,144/51,572/55,348; guarded 95,310/111,178/119,479.
  - MDE half-widths (`artifacts/05_fig2_uncertainty/fig4_tercile_ci.csv`):
    validation low/mid/high = 0.85/0.81/0.86pp; guarded low/mid/high =
    0.57/0.56/0.54pp. Treat these as **per-trading-day block-bootstrap MDE
    half-widths**, not as confidence intervals, standard errors, seed-level
    uncertainty, or significance intervals.
- **Type:** paired diverging grouped bar chart. X-axis = ordered activity tercile
  (Low activity, Medium activity, High activity). Y-axis = macro-F1 difference
  `model - same-row stratified dummy`, pp. At each tercile, dodge the two domains
  (validation teal bar, guarded mauve bar with sparse hatch) against a bold solid
  zero rule. Overlay open circle and diamond markers for seed 101 and seed 202.
  This is the most conventional option and makes Fig. 4 visually distinct from
  Fig. 2's forest plot and Fig. 3's curve. A faint grey `axhspan` below zero
  marks the below-dummy-floor region that the high-tercile bars fall into. Show
  the MDE as a faded grey sleeve (a `Rectangle` behind each bar endpoint) -- NOT
  a capped whisker -- so it reads as a descriptive half-width and does not
  duplicate Fig. 2's CI whiskers. Legend sits inside the empty upper-right
  quadrant. No stars, no significance labels, no heatmap. Rationale from the
  later agent review:
  lollipop felt uncommon to the user; profile/point-range remained close to
  point-interval graphics; grouped bars are the lowest-explanation-cost main-text
  choice for a 2-domain x 3-tercile condition map.
- **Labels:** legend "Validation" vs "Guarded WF", "Seed 101", "Seed 202", and
  "Day-block MDE band"; x-axis "Activity tercile (eligible-row count)"; y-axis
  two-line `Delta Macro-F1` / `vs. stratified baseline (pp)` using the Greek
  delta symbol. The caption must spell out same-row stratified dummy, define WF/MDE, map
  circle/diamond to seeds 101/202, and state that the grey MDE sleeves are not
  confidence intervals. Activity terciles are rank-defined within ticker, so do
  not invent a single global cut point.
  Keep the full historically-contacted and not-clean-test limitation in the
  caption/prose, with only a compact in-figure label.
- **Caption constraints:** say positive values favor the model; activity is the
  eligible-row-count proxy under the no-trade band, not volume/liquidity/
  volatility; low is positive and high is below the random-prior/dummy floor in
  both domains; guarded is measure-only and historically contacted, not a clean
  test; bars are arithmetic means across seeds 101 and 202, with seed-specific
  points overlaid; MDE sleeves are descriptive and do not represent confidence
  intervals, standard errors, or seed-level uncertainty. Do not claim statistical
  significance or cross-seed reliability.

---

## 4. Files to read before plotting

- `paper/scripts/style.py` — import and use it (widths, palette, rc).
- `paper/main.tex` — package whitelist is booktabs/graphicx/siunitx/amsmath only
  (so deliver external PDFs via `\includegraphics`; do not require tikz/pgfplots).
- The 3 section files with the figure environments + captions to match:
  `paper/sections/03_protocol.tex`, `06_results.tex`, `08_diagnostics.tex`.
- `paper/outline_and_claims.md` — the claims ledger (canonical numbers; cross-check
  every value you plot against it).
- Existing exemplar figures + their source, to match house style:
  `artifacts/ian_email_packet_20260611/figures/fig_01_validation_delta_by_ticker.pdf`
  (≈ Fig 2), `fig_04_selective_risk_coverage.pdf` (Fig 3), `fig_05_activity_tercile_delta.pdf`
  (validation-only ancestor of Fig 4); plotting logic in
  `src/lst_models/diagnostics.py` and `src/lst_models/stages/diagnostics_ablation.py`.

---

## 5. Suggested script layout (one script per figure)

```
paper/scripts/make_fig_protocol_timeline.py   -> paper/figures/fig_protocol_timeline.pdf
paper/scripts/make_fig_validation_deltas.py   -> paper/figures/fig_validation_deltas.pdf
paper/scripts/make_fig_risk_coverage.py       -> paper/figures/fig_risk_coverage.pdf
paper/scripts/make_fig_tercile_map.py         -> paper/figures/fig_tercile_map.pdf
```

Each: import `style`, read its CSV(s) with stdlib `csv` or pandas, build the plot,
save the PDF. Keep each script under ~80 lines. A `make_all.py` that runs the four
is a nice-to-have.

---

## 6. After the PDFs exist: swap the placeholders in the `.tex`

Each figure environment currently has a commented `\includegraphics`, a visible
`\fbox{...}` placeholder, and a `% TODO figure:` line. Once a real PDF lands,
uncomment the `\includegraphics[width=\linewidth]{figures/<name>}` line and delete
the matching `\fbox{\parbox{...}{Figure placeholder: ...}}` block. (Leave the
`\caption` and `\label` untouched.) The brief author (Claude) can do this swap once
the four PDFs are delivered — coordinate so it happens exactly once.

---

## 7. Acceptance checklist

- [ ] 4 vector PDFs in `paper/figures/` with the exact names in section 3.
- [ ] Each imports `paper/scripts/style.py` (Okabe-Ito colors, sigconf width, 300 dpi).
- [ ] Every plotted number traces to the cited CSV and matches the claims ledger.
- [ ] Zero/reference lines present where appropriate (no-improvement line on Fig 2 and Fig 4).
- [ ] Activity defined as eligible-row-count proxy (not volume/liquidity) on Fig 4.
- [ ] Evidence domains labeled (validation n=2 vs guarded) on Fig 4; no domain merged.
- [ ] No forbidden framing (best/significant/clean-test/tradable) in any in-figure text.
- [ ] Fig 3 provenance noted (reused rendered curve vs regenerated from the dump).
- [ ] `main.tex` compiles with the 4 figures (after the section-6 placeholder swap).
```
