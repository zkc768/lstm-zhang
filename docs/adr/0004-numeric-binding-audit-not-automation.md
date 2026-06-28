# Numeric↔ledger binding: 3× audit accepted; per-pass automation declined

**Status:** accepted (2026-06-28)

Numbers are the cardinal integrity risk (a wrong number is fabrication), yet no automated gate
checks number↔ledger binding — `check_integrity.py` tests vocabulary/structure only. The obvious
"fix" would be a `numbers_check.py` that extracts numeric tokens from the .tex and matches them to
the ledger.

**Decision:** Accept the existing **three independent verifications** as sufficient binding
coverage: (1) the Pass-B main-loop audit against the ledger + artifact CSVs (0 discrepancies, exact
values), (2) the Codex cross-model confirmation that load-bearing numbers match the ledger, and
(3) the `DRAFT_NOTES.md` number→location→artifact-value map. **Decline** a per-pass
`numbers_check.py`: extracting numbers from LaTeX false-positives heavily on years, macro
arguments, equation constants, and table-vs-prose duplication, so it would add noise without
beating the 3× coverage. The only automation kept on the table is an **optional pre-submission
tripwire** (run once before submit), never a per-pass gate.

**Consequences:** number binding stays a point-in-time human + cross-model audit; it MUST be
re-run if any number or the ledger changes. `sync_check.py` (ADR 0003) flags ledger drift, which is
the main trigger to re-audit — so the two guards compose: structural drift detection (automated) +
numeric correctness (audited on trigger).
