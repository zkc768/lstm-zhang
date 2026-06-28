#!/usr/bin/env python3
"""Self-test for length_gates: an unchanged section MUST pass; tampered candidates
(fabricated number, lost necessary number, introduced forbidden term, catastrophic
over-deletion) MUST block on the right gate. Calibrates the gate+manifest against
the real accepted paper before the length loop runs."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import length_gates as G

M = G.load_manifest()
SEC8 = 'sections/08_diagnostics.tex'
cur8 = G.disk_text(SEC8)

def show(name, res, expect):
    verdict = 'PASS' if res['pass'] else 'BLOCK'
    ok = (verdict == expect)
    print(f"[{'OK ' if ok else 'XX '}] {name}: {verdict} (expected {expect})")
    for L in ('L1', 'L2', 'L3', 'L4', 'L5'):
        for msg in res[L]['issues']:
            print(f"        {L}: {msg}")
    if res['L2'].get('calibration_unmatched') and name.startswith('1'):
        print(f"        L2 calibration: {len(res['L2']['calibration_unmatched'])} required phrases not matched in current prose (floor=0, not enforced): {res['L2']['calibration_unmatched']}")
    return ok

results = []
# 1. identity -> must PASS (calibration: the accepted paper must clear every gate)
results.append(show('1 identity (unchanged 08)', G.run_gates(SEC8, cur8, M), 'PASS'))
# 2. fabricated number -> L1 illegal add
results.append(show('2 fabricated number (+"0.873")', G.run_gates(SEC8, cur8 + "\nHeld-out accuracy reached 0.873 overall.\n", M), 'BLOCK'))
# 3. lost necessary number unique to 08 (0.237 AUGRC, also_appears_in [])
results.append(show('3 lost necessary (delete 0.237)', G.run_gates(SEC8, cur8.replace('0.237', ''), M), 'BLOCK'))
# 4. introduced forbidden term (superior / well-calibrated, un-negated)
results.append(show('4 forbidden introduced (+"clearly superior and well-calibrated")', G.run_gates(SEC8, cur8 + "\nThe TCN is clearly superior and well-calibrated.\n", M), 'BLOCK'))
# 5. introduced multiple forbidden (clean test / profitable / out-of-sample, un-negated)
results.append(show('5 forbidden introduced (+"a clean test of profitable out-of-sample")', G.run_gates(SEC8, cur8 + "\nThis is a clean test of profitable out-of-sample performance.\n", M), 'BLOCK'))
# 6. catastrophic over-deletion of 08 -> L1 lost necessary + L2 required dropped + L3 coverage
stub = "\\section{Diagnostics}\n\\label{sec:diagnostics}\nThe diagnostics are summarized in the appendix.\n"
results.append(show('6 catastrophic cut (08 -> stub)', G.run_gates(SEC8, stub, M), 'BLOCK'))
# 7. delete a still-locked Fig.4 caption caveat -> L4 caption lock must fire.
# (Originally "rank-defined within ticker"; r040 intentionally UNLOCKED that phrase from
#  fig:tercile_map and relocated it to the section-08 body, so it is no longer caption-locked.
#  Re-pointed at "not confidence intervals", which fig:tercile_map still locks, so the L4
#  caption-lock mechanism stays under test.)
results.append(show('7 caption-clobber (delete "not confidence intervals")', G.run_gates(SEC8, cur8.replace('not confidence intervals', 'not error bars'), M), 'BLOCK'))
# 8. strip the abstention conditional hedge -> L5 hedge lock must fire
results.append(show('8 hedge-strengthen (strip "To the extent")', G.run_gates(SEC8, cur8.replace('To the extent ', '', 1), M), 'BLOCK'))
# 9. the REAL clobbered cand_08.tex (the cut that passed the old gate) -> must now BLOCK
_cand = os.path.join(G.PAPER_DIR, 'length_loop', 'cand_08.tex')
if os.path.exists(_cand):
    results.append(show('9 real clobbered cand_08.tex (regression)', G.run_gates(SEC8, G.read(_cand), M), 'BLOCK'))

# ---- table field-level audit calibration (audit_paper_tables) ----
# Same philosophy as above: the accepted paper must audit CLEAN, and a fabricated
# table value MUST be caught -- so the provenance audit is proven to have teeth.
import audit_paper_tables as ATA


def show_audit(name, results_, expect_clean):
    clean = ATA.clean_verdict(results_)
    ok = (clean == expect_clean)
    print(f"[{'OK ' if ok else 'XX '}] {name}: {'CLEAN' if clean else 'FINDINGS'} "
          f"(expected {'CLEAN' if expect_clean else 'FINDINGS'})")
    if clean != expect_clean:
        print(f"        audit counts: {ATA.summarize(results_)}")
    return ok


_MAN = ATA.DEFAULT_MANIFEST
_, _ar = ATA.audit(_MAN)
results.append(show_audit('10 table audit (current paper -> clean)', _ar, True))
_sec06 = os.path.join(G.PAPER_DIR, 'sections', '06_results.tex')
_tamper = open(_sec06, encoding='utf-8').read().replace('0.5170', '0.9999')
_, _ar = ATA.audit(_MAN, {'sections/06_results.tex': _tamper})
results.append(show_audit('11 fabricated table value (0.5170->0.9999 -> caught)', _ar, False))

# ---- dedup / per-scope floor machinery (design v4 §4): synthetic states exercise gate_L2 ----
def _st(secmap):
    return {'sec_norm': {k: G.normalize_for_match(v) for k, v in secmap.items()},
            'paper_norm': G.normalize_for_match(' \n '.join(secmap.values()))}
def _mini(rp):
    return {'required_phrases': [rp], 'forbidden_terms': []}
def show_l2(name, rp, cur_map, cand_map, expect_pass, want):
    L2 = G.gate_L2(_st(cur_map), _st(cand_map), _mini(rp))
    vp = L2['pass']
    has = bool(L2[want]) if want else True
    ok = (vp == expect_pass) and has
    detail = [(r['id'], r.get('group'), r['scope']) for r in L2[want]] if want else 'n/a'
    print(f"[{'OK ' if ok else 'XX '}] {name}: pass={vp} (expect {expect_pass}); {want}={detail}")
    return ok

SEC = 'sections/08_diagnostics.tex'
# 12 allowed dedup: 3->1 in a floored scope, floor still met -> PASS + dedup_ok recorded
results.append(show_l2('12 allowed dedup (3->1, floor met)',
    {'id': 'T', 'match_any': ['alpha'], 'floors': {'section:08': 1}},
    {SEC: 'alpha alpha alpha'}, {SEC: 'alpha'}, True, 'dedup_ok'))
# 13 floor_breach: last instance removed -> BLOCK + missing_required
results.append(show_l2('13 floor_breach (1->0 last instance)',
    {'id': 'T', 'match_any': ['beta'], 'floors': {'section:08': 1}},
    {SEC: 'beta'}, {SEC: 'no hits here'}, False, 'missing_required'))
# 14 main.tex floor: abstract loses its only instance -> BLOCK
results.append(show_l2('14 main.tex floor_breach',
    {'id': 'T', 'match_any': ['gamma'], 'floors': {'main.tex': 1}},
    {'main.tex': 'gamma'}, {'main.tex': 'removed'}, False, 'missing_required'))
# 15 required_groups: drop ONE group, keep the other -> BLOCK on the dropped group
results.append(show_l2('15 required_groups breach (one group dropped)',
    {'id': 'T', 'required_groups': [{'name': 'g1', 'match_any': ['delta'], 'floors': {'section:08': 1}},
                                    {'name': 'g2', 'match_any': ['epsilon'], 'floors': {'section:08': 1}}]},
    {SEC: 'delta epsilon'}, {SEC: 'delta'}, False, 'missing_required'))
# 16 floor_unbound: declared floor whose phrase has no live hit -> BLOCK (non-silent, design v4 MAJOR-1)
results.append(show_l2('16 floor_unbound (declared floor, 0 live hits)',
    {'id': 'T', 'match_any': ['phrase that is absent'], 'floors': {'section:08': 1}},
    {SEC: 'unrelated content'}, {SEC: 'unrelated content'}, False, 'floor_unbound'))
# 17 main.tex scope fidelity (W2): phrase lives only in sec08; a main.tex floor must read the
#    abstract ONLY -> 0 hits -> floor_unbound. If scope_text regressed to whole-paper it would
#    find it in sec08 and wrongly bind -> this case fails closed.
results.append(show_l2('17 main.tex scope fidelity (not whole-paper)',
    {'id': 'T', 'match_any': ['zeta'], 'floors': {'main.tex': 1}},
    {'main.tex': 'abstract only', SEC: 'zeta lives only in sec08'},
    {'main.tex': 'abstract only', SEC: 'zeta lives only in sec08'}, False, 'floor_unbound'))

print(f"\nSELFTEST: {sum(results)}/{len(results)} cases behaved as expected.")
sys.exit(0 if all(results) else 1)
