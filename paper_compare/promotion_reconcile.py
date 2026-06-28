#!/usr/bin/env python3
"""promotion_reconcile.py - the v1->v2 promotion gate (ADR 0005).

Before v2 (paper_compare/v2_skill_draft/) is promoted to live paper/, it MUST satisfy the live
protection_manifest.json (v1-era pinned hedges/captions/never-delete). This is the bridge between
Workflow 1 (sandbox writing, PAPER_WORKFLOW.md) and Workflow 2 (revision/QC, the docs/protocols
family): Workflow 2's gates are built around the manifest, so promotion cannot break it.

GATES (exit 1 on any unmet): required_phrases (>=1 match_any present), caption_locks (must_contain),
never_delete invariants (Description/GenAI/macros/keywords/ccsdesc). forbidden_terms are reported as
WARN (cite-keys like zhang2026whenalpha and negated/foil uses cause benign false-positives -> human check).

Usage:  python paper_compare/promotion_reconcile.py [target_dir]   (default v2_skill_draft)
"""
import json, glob, re, sys, os

MANIFEST = "paper/length_loop/protection_manifest.json"

def norm(s):
    return " ".join(s.split()).lower()

def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "paper_compare/v2_skill_draft"
    if not os.path.exists(MANIFEST):
        print("MISSING manifest:", MANIFEST); sys.exit(2)
    d = json.load(open(MANIFEST, encoding="utf-8"))
    files = [os.path.join(target, "main.tex")] + sorted(glob.glob(os.path.join(target, "sections", "*.tex")))
    T = norm("\n".join(open(f, encoding="utf-8").read() for f in files if os.path.exists(f)))
    fail = False

    rp = d.get("required_phrases", [])
    unmet = [(e.get("id"), (e.get("concept", "") or "")[:60]) for e in rp
             if not any(norm(p) in T for p in (e.get("match_any") or ([e["phrase"]] if "phrase" in e else [])))]
    print(f"required_phrases (D-locks): {len(rp)-len(unmet)}/{len(rp)} satisfied")
    for i, c in unmet:
        print(f"  [FAIL] UNMET {i}: {c}"); fail = True

    cl = d.get("caption_locks", [])
    cbad = 0
    for e in cl:
        miss = [s for s in e.get("must_contain", []) if norm(s) not in T]
        if miss:
            print(f"  [FAIL] caption {e.get('label')} missing {miss}"); cbad += 1; fail = True
    print(f"caption_locks: {len(cl)-cbad}/{len(cl)} satisfied")

    inv = {"\\Description block": T.count("\\description") > 0,
           "GenAI statement": "generative ai usage" in T,
           "\\macrofone": "\\macrofone" in T, "\\numseeds": "\\numseeds" in T, "\\pp": "\\pp" in T,
           "\\keywords": "\\keywords" in T, "\\ccsdesc": "\\ccsdesc" in T}
    print("never_delete invariants:")
    for k, v in inv.items():
        print(f"  {'[ ok ]' if v else '[FAIL]'} {k}")
        if not v: fail = True

    ft = d.get("forbidden_terms", [])
    warn = []
    for e in ft:
        term = norm(e.get("term", "")); negs = [norm(x) for x in e.get("negators", [])] + ["rather than", "instead of", "not ", "no "]
        for m in re.finditer(re.escape(term), T):
            pre = T[max(0, m.start()-30):m.start()]
            if pre[-1:].isalpha():  # cite-key / compound word, e.g. zhang2026whenalpha
                continue
            if not any(n in pre for n in negs):
                warn.append((e.get("id"), e.get("term"))); break
    print(f"forbidden_terms: {len(ft)-len(warn)}/{len(ft)} clean; {len(warn)} WARN (human-check, often cite-key/foil)")
    for i, t in warn[:10]:
        print(f"  [warn] {i} '{t}'")

    print("\nRESULT:", "PROMOTION BLOCKED - reconcile required" if fail else "v2 satisfies the v1 manifest - promotion gate PASS")
    sys.exit(1 if fail else 0)

if __name__ == "__main__":
    main()
