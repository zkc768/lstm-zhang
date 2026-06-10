# Ian/Lan Requirement Extracts (verbatim, dated)

Status: provenance record. Read from Gmail on 2026-06-10 (threads between
kevinzhang381@gmail.com and ian Deng <yancongdeng@gmail.com>). This file is
the in-repo citable source for the Stage 04 plan provenance table, the Stage
05 claim register, and the Stage 06 §5 Ian-requirement mapping rows. It is
design guidance and requirement provenance ONLY — it is not performance
evidence and it never overrides frozen stage protocols (AGENTS.md §2).

Quotes are verbatim sentence extracts; ellipses mark omitted text. Gmail
message ids are recorded for auditability.

## Thread: "Assignment5—LSTM Baseline Project"

- 2026-03-13, msg `19ce7a1d1f8f4e83`:
  > "Please revise the pipeline to use a separate train/validation/test
  > split instead of using the test set for early stopping."
  > "keep only regular trading hours and make sure each input window stays
  > within the same trading day, so the sequences do not cross overnight."
  > "add a simple naive baseline for comparison"
- 2026-03-25, msg `19d259ed90498c15`:
  > "the current LSTM baseline does not outperform the naive baseline in
  > the raw price setting" ... "move to a more meaningful target, such as
  > future return over a longer horizon or direction classification" ...
  > "please continue with the 5-minute data rather than the 1-minute
  > version."
- 2026-04-09, msg id in thread `19cd8a7a7b13c6d2`:
  > "checking whether the model is really learning, whether the label
  > distribution is reasonable, and whether the current setup can overfit
  > a small subset." ... "summarize the results clearly in one comparison
  > table"
- 2026-04-19, msg id in thread `19cd8a7a7b13c6d2`:
  > "keep this tuned LSTM as one baseline model" ... "add the following
  > models for comparison: GRU, TCN, and one CNN-based sequence model" ...
  > "change the training strategy from single-stock training to pooled
  > multi-stock training ... evaluate the performance separately on each
  > stock."
- 2026-05-04, msg id in thread `19cd8a7a7b13c6d2`:
  > "simplify the current high-frequency setting into a cleaner binary
  > classification task first" ... "Define the label based on the future
  > average return over a longer horizon. For example 12 bars or 24 bars"
  > ... "please do not rely on one F1 score only. I would like you to
  > include macro F1, balanced accuracy, confusion matrix, and the
  > comparison against the dummy or always-up baseline."

## Thread: "Question About Research Progress and Next Steps"

- 2026-05-18, msg `19e38bf493ce3fa7`:
  > "move toward a more structured proposed model based on DLinear. A
  > possible direction is a stock-aware multi-scale DLinear model with a
  > residual TCN branch."
  > "Instead of only dropping exact-zero returns, use a real no-trade
  > band." ... "Please try a few threshold levels and report test results"
  > "You can keep LSTM, TCN, and standard DLinear as baselines."
  > "try multiple moving-average windows, such as 3, 6, 12, and 24."
  > "for the residual part, you can add a small TCN branch."

## Thread: "Progress update on DLinear stock direction experiments"

- 2026-05-29, msg `19e74cd7695e1f15`:
  > "the current 5-minute technical indicators only provide weak signals.
  > For the next step, please focus on cleaning the features and checking
  > selective prediction."
  > "remove non-stationary raw features such as raw OHLCV, raw volume, and
  > raw MACD." ... "use normalized features instead, such as log return,
  > close-to-open return, high-low range, rolling volatility, normalized
  > volume, RSI, Bollinger %B, normalized MACD histogram, and time-of-day
  > features."
  > "If this shows improvement, we can then rerun the other baselines for
  > a fair comparison."
- 2026-06-01 (Chengkai → Ian, msg `19e83446cbf5ee8f`, context for the
  contamination caveat):
  > "Since this holdout period has already been used before, I would not
  > present this as final evidence."
- 2026-06-04, msg `19e9479d4932a413` (the active instruction set):
  > "run the current model on 2–3 additional walk-forward holdout periods
  > to check whether the positive result is stable over time. For each
  > period, please report tested results."
  > "prepare one final comparison table using the same setting. The table
  > should include Dummy, LightGBM, standard DLinear, TCN, and
  > MS-DLinear+TCN."
  > "prepare a small ablation study with standard DLinear, multi-scale
  > DLinear, and MS-DLinear+TCN. This will help us show whether each part
  > of the proposed model is useful."
  > "start writing the paper now ... Introduction, Related Work, Method
  > sections ... acm template for the draft attached."
- 2026-06-04, msg `19e94ccee27a931b` (timeline):
  > "projecting around 3–4 weeks to complete the remaining experiments and
  > prepare the paper draft." ... "walk-forward tests, the final
  > comparison table, and the ablation study may take the next 1–2 weeks"
  > ... "remaining 2 weeks to complete and revise the draft."

## Route mapping

The requirement → stage mapping table lives in
`docs/lst_models_stage04_implementation_plan.md` (non-blocking provenance
note) and is inherited by the Stage 06 §5 mapping rows in Batch E. The
walk-forward request maps to a pre-registered V2.1 guarded readout, NOT to
Stage 04 (frozen D3 zero-event rule; D4 holdout closure).
