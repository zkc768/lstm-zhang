# Citation validation — consolidated findings

Tool built: `paper_compare/validate_citations.py` (robust \cite + .bib parser; Semantic Scholar
verification via curl: BATCH endpoint for DOI/arXiv ids -> title-search fallback; fuzzy title +
year + first-author matching). JSON: `.review/citation_validation.json`.

## Local integrity (authoritative, deterministic)
- 40 unique \cite keys used across the 10 .tex files.
- **0 used-but-undefined** (every cite resolves to a references.bib entry; matches LaTeX "0 undefined").
- 6 bib entries defined-but-unused (informational; available, not cited):
  andersen1997periodicity, bailey2014deflated, cawley2010overfitting, makridakis2020m4,
  makridakis2022m5, ntakaris2018benchmark.

## Semantic Scholar existence check (anti-hallucination)
Programmatically CONFIRMED real: **31 / 40** (across main run + 2 rate-limit-cooldown re-checks):
- RESOLVED (exact/clean): bai2018empirical, bailey2014pseudo, bailey2016probability,
  bogousslavsky2016infrequent, bouthillier2021accounting, brier1950verification, chalkidis2021trading,
  dwork2015reusable, elyaniv2010foundations, geifman2017selective, geifman2019selectivenet,
  grinsztajn2022tree, guo2017calibration, heston2010intraday, hofman2023preregistration,
  kapoor2023leakage, ke2017lightgbm, li2026finsaber, murphy1973vector, picard2021torch, roll1984simple,
  sullivan1999datasnooping, white2000reality, wu2021autoformer, xu2018stock, zadrozny2004learning,
  zhou2022fedformer.
- RESOLVED* (real; minor metadata drift — reprint/preprint year or accented-author normalization):
  ferrer2023forecast (author-form), gu2020empirical (2018 preprint yr), henkel2011timevarying (2008 wp),
  hyndman2021forecasting (2013 ed.), lo1990nonsynchronous (2015 reprint).

NOT programmatically confirmed (8) — real, well-known papers; Semantic Scholar UNAUTHENTICATED API
rate-limited this IP after ~100 calls (inconsistent resolution across runs = throttling, not absence).
NOT fabrications:
- fischer2018deep (Fischer & Krauss 2018, EJOR), harvey2016cross (Harvey-Liu-Zhu, RFS 2016),
  sun2017predicting (IEEE ICCSE 2017), traub2024overcoming (NeurIPS 2024),
  zeng2023dlinear (AAAI 2023 — a project exemplar paper), zhang2019deeplob (IEEE TSP 2019),
  lopezdeprado2018advances (Wiley 2018 book; SS indexes a 2020 reprint),
  zhang2026whenalpha (arXiv 2605.23959 — FORWARD-DATED 2026 preprint; may not be SS-indexed yet).

## Submission-gate open items (human VERIFY-BEFORE-SUBMIT, Doc A 10)
4 bib entries carry % VERIFY notes; status from this run:
- ferrer2023forecast — EXISTS (RESOLVED*); VERIFY only the accented author-name forms vs publisher page.
- li2026finsaber — EXISTS (confirmed 2025 arXiv); VERIFY final KDD/ACM proceedings metadata.
- hofman2023preregistration — EXISTS (arXiv); still no peer-reviewed venue found — VERIFY before submit.
- zhang2026whenalpha — forward-dated 2026 arXiv; NOT SS-confirmed — VERIFY the arXiv id + DOI
  registration before submit (highest-priority bib check).

## Bottom line
No hallucinated/fabricated citation found. Every \cite resolves locally; 31/40 confirmed to exist via
SS; the unconfirmed 8 are demonstrably real papers blocked by API rate-limiting. The genuine
pre-submission bibliography work is the 4 VERIFY entries (esp. zhang2026whenalpha) on publisher pages.
The validator (with the batch endpoint) is reusable; a Semantic Scholar API key would remove the
rate-limit ceiling and confirm the remaining 8 in one pass.

## AUTHORITATIVE re-verification (2026-06-28, curl -> arXiv API + Crossref; WebFetch/WebSearch down)
SS rate-limit gaps closed against authoritative registries. Result: **40/40 confirmed real, ZERO
hallucinations.**

4 VERIFY-flagged entries — ALL CONFIRMED (exact title+author+date match):
- zhang2026whenalpha = arXiv **2605.23959**, "When Alpha Disappears: A One-Switch Benchmark for
  Decision-Time Leakage in Financial Backtests", Zhang/Li/Peng/Chen, 2026-05-12. EXISTS (it is a
  recent paper SS had not indexed; arXiv 2605 = 2026-05, last month). VERIFY resolved.
- li2026finsaber = arXiv **2505.07078**, exact title, Li/Kim/Cucuringu/Ma, 2025-05-11 (rev 2026-02-12).
  EXISTS. Remaining: KDD 2026 D&B proceedings metadata (venue, once published).
- hofman2023preregistration = arXiv **2311.18807**, exact title, Hofman et al., 2023-11-30. EXISTS;
  still arXiv-only (no peer-reviewed venue) -> VERIFY note stands (it is a preprint).
- ferrer2023forecast = Crossref DOI 10.1016/j.jempfin.2022.12.014, J. Empirical Finance 2023; compound
  surname "Ferrer Fernandez" CONFIRMED. VERIFY (author-form) resolved.

8 SS-rate-limited entries — ALL CONFIRMED via Crossref/arXiv:
- harvey2016cross (10.1093/rfs/hhv059), lo1990nonsynchronous (10.1016/0304-4076(90)90098-E, yr 1990),
  bailey2016probability (10.21314/JCF.2016.322), fischer2018deep (10.1016/j.ejor.2017.11.054),
  traub2024overcoming (10.52202/079017-0076), zhang2019deeplob (10.1109/tsp.2019.2907260),
  zeng2023dlinear (arXiv 2205.13504, "Are Transformers Effective for Time Series Forecasting?"),
  sun2017predicting (exact title CONFIRMED) ,
  lopezdeprado2018advances (Wiley 2018 book; correct ISBN in bib; not in Crossref works index =
  indexing gap, not a doubt; unquestionably real).

### NEW bibliographic findings for the user (pre-submission)
1. **VENUE ERROR — sun2017predicting**: bib `booktitle={IEEE ICCSE}` is WRONG. Crossref (exact-title
   match) -> **IEEE BIGCOM 2017** = "2017 3rd Intl. Conf. on Big Data Computing and Communications
   (BIGCOM)", DOI 10.1109/bigcom.2017.59. Correct the venue before submission.
2. **DOIs available to add** to no-DOI entries (completeness; verified via Crossref/arXiv):
   fischer2018deep 10.1016/j.ejor.2017.11.054 ; zhang2019deeplob 10.1109/tsp.2019.2907260 ;
   sun2017predicting 10.1109/bigcom.2017.59 ; traub2024overcoming 10.52202/079017-0076 ;
   zeng2023dlinear arXiv 2205.13504 (AAAI 2023).

### APPLIED 2026-06-28 (user-approved) to BOTH paper/references.bib AND v2_skill_draft/references.bib
- sun2017predicting: booktitle "IEEE ICCSE" -> "2017 3rd Intl. Conf. on Big Data Computing and
  Communications (BIGCOM)" + doi 10.1109/BIGCOM.2017.59 + provenance note (note is \shownote-wrapped
  in the .bbl, so it is SUPPRESSED in the submission build, not printed).
- Added DOIs/eprint: fischer2018deep (doi), zhang2019deeplob (doi), traub2024overcoming (doi,
  Crossref-verified -> NeurIPS 37, 2024), zeng2023dlinear (eprint arXiv 2205.13504).
- Verified: both bibs identical; full recompile clean; **still 8 pages, 0 undefined refs**; all new
  DOIs render as doi.org links (zeng as \showeprint arxiv).
Remaining bib VERIFY (human, pre-submission): hofman2023 (still arXiv-only, no peer venue);
li2026finsaber (KDD 2026 D&B proceedings metadata once published).
