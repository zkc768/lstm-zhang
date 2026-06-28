#!/usr/bin/env python3
"""sync_check.py - guard the v2 sandbox against drift from the authoritative live paper/ (ADR 0003).

The LIVE paper/ is the single source of truth for the ledger and bibliography. v2_skill_draft/
keeps READ-ONLY mirrors. This asserts they are byte-identical before each pass; any drift means a
one-sided hand edit = FAIL. Run from repo root:  python paper_compare/sync_check.py
"""
import hashlib, sys, os

PAIRS = [
    ("ledger", "paper/outline_and_claims.md",
               "paper_compare/v2_skill_draft/outline_and_claims.md"),
    ("bib",    "paper/references.bib",
               "paper_compare/v2_skill_draft/references.bib"),
]
FROZEN = "paper_compare/v1_current/outline_and_claims.md"  # immutable v1 baseline (reference only)

def md5(p):
    if not os.path.exists(p):
        return None
    with open(p, "rb") as fh:
        return hashlib.md5(fh.read()).hexdigest()

def main():
    fail = False
    for name, live, mirror in PAIRS:
        h_live, h_mir = md5(live), md5(mirror)
        if h_live is None or h_mir is None:
            print(f"FAIL {name}: missing file (live={h_live is not None}, mirror={h_mir is not None})")
            fail = True
            continue
        ok = h_live == h_mir
        print(f"{'PASS' if ok else 'FAIL'} {name}: live={h_live[:10]} mirror={h_mir[:10]}")
        if not ok:
            fail = True
            print(f"  -> DRIFT: edit the authoritative copy ({live}), then mirror it; never edit both by hand.")
    hf = md5(FROZEN)
    if hf:
        print(f"info  v1 frozen baseline ledger = {hf[:10]} ({FROZEN})")
    print("\nRESULT:", "DRIFT - fix before any pass" if fail else "v2 mirrors are in sync with live")
    sys.exit(1 if fail else 0)

if __name__ == "__main__":
    main()
