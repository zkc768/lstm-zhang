#!/usr/bin/env python3
"""Fail-closed structured gates for the lst_models length-reduction loop.

DELTA semantics: every gate compares the CANDIDATE paper-state against the
CURRENT on-disk paper-state (the thing the edit is replacing). The gate blocks
only what the *edit* breaks -- it never asserts an idealized absolute, so it is
robust to manifest/variant imperfection and to benign pre-existing substrings
(e.g. "volume" inside price_volume_time, "alpha" inside a cite key).

L1 numbers/keys
  - illegal numeric ADD: a token in the candidate section that was not in the
    original section and is not a manifest canonical (claim-bound) value -> BLOCK (fabrication).
  - lost NECESSARY number: a manifest necessary number present paper-wide NOW but
    absent paper-wide in the candidate -> BLOCK (real result dropped). Duplicates
    (still present elsewhere) are free to remove.
  - lost last citation / orphaned label / dangling ref -> BLOCK.
L2 required/forbidden (normalized: comments+keys stripped, macros expanded,
   lowercased, hyphens->space, whitespace collapsed)
  - required phrase: floor = min(min_count, original_scope_hits); candidate scope
    hits < floor -> BLOCK. (floor=0 when the variant list doesn't match current
    prose, so no false positive; logged as calibration warning.)
  - forbidden term: candidate un-negated count > current un-negated count -> BLOCK
    (catches a cut that strips a negator or exposes a bare forbidden term).
L3 coverage: a claim covered NOW (necessary numbers + required phrases present)
   that becomes uncovered in the candidate -> BLOCK.

Single tokenizer: imports latex_inventory.

Exit 0 = pass, 1 = at least one BLOCK, 2 = usage/IO error.
Usage: python length_gates.py --section sections/08_diagnostics.tex --candidate cand.tex
       [--manifest paper/length_loop/protection_manifest.json]
"""
import re, os, sys, json, argparse
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import latex_inventory as inv

PAPER_DIR = inv.PAPER_DIR
SECTIONS_DIR = inv.SECTIONS_DIR
MACROS = inv.load_macros()
DEFAULT_MANIFEST = os.path.join(PAPER_DIR, 'length_loop', 'protection_manifest.json')

def rel(p):
    return os.path.relpath(p, PAPER_DIR).replace('\\', '/')

def read(p):
    return open(p, encoding='utf-8').read()

def all_section_relpaths():
    out = ['main.tex']
    out += [rel(os.path.join(SECTIONS_DIR, f)) for f in sorted(os.listdir(SECTIONS_DIR)) if f.endswith('.tex')]
    return out

def disk_text(relpath):
    return read(os.path.join(PAPER_DIR, relpath))

# ---------- normalization ----------
KEY_CMD = r'\\(?:cite[A-Za-z]*|autoref|eqref|[cC]ref|ref|label|includegraphics|input)\*?(?:\[[^\]]*\])?\{[^}]*\}'
def normalize_for_match(s):
    s = inv.strip_comments(s)
    s = re.sub(KEY_CMD, ' ', s)               # drop keys/filenames so identifiers don't pollute matching
    s = inv.expand_macros(s, MACROS)
    s = s.lower()
    s = re.sub(r'[\-‐-―]', ' ', s)  # hyphens / dashes -> space
    s = re.sub(r'[{}\\$~^_&]', ' ', s)
    s = re.sub(r'\s+', ' ', s)
    return s

def section_numbers(text):
    return Counter(inv.extract_numbers(inv.expand_macros(inv.strip_comments(text), MACROS)))

# ---------- whole-paper state for a given override {relpath: text} ----------
def compute_state(override):
    nums, cites, labels, refs = Counter(), Counter(), Counter(), Counter()
    sec_norm, parts = {}, []
    for r in all_section_relpaths():
        t = override[r] if r in override else disk_text(r)
        raw = inv.strip_comments(t)
        nums.update(inv.extract_numbers(inv.expand_macros(raw, MACROS)))
        k = inv.extract_keys(raw)
        cites.update(k['cite']); labels.update(k['label']); refs.update(k['ref'])
        n = normalize_for_match(t)
        sec_norm[r] = n; parts.append(n)
    return {'nums': nums, 'cites': cites, 'labels': labels, 'refs': refs,
            'sec_norm': sec_norm, 'paper_norm': ' \n '.join(parts)}

def scope_text(state, scope):
    if not scope or scope == 'paper':
        return state['paper_norm']
    if scope in state['sec_norm']:                 # literal relpath, e.g. 'main.tex' or 'sections/06_results.tex'
        return state['sec_norm'][scope]            # per-file text ONLY (W2: main.tex must not fall through to whole paper)
    m = re.match(r'section:?\s*0*(\d+)', str(scope))
    if m:
        num = int(m.group(1))
        for r, n in state['sec_norm'].items():
            if re.search(rf'/0*{num}_', '/' + r):
                return n
    return state['paper_norm']

def count_variants(variants, text):
    return sum(text.count(v) for v in variants if v)

def count_unnegated(term, negators, text):
    """Count occurrences of `term` not preceded by a negator IN THE SAME clause.
    The window is clipped at the previous sentence/clause boundary (. ; :) so a
    negator from a different sentence cannot spuriously mask a new violation."""
    c = 0
    for m in re.finditer(re.escape(term), text):
        win = text[max(0, m.start() - 60):m.start()]
        cut = max(win.rfind('.'), win.rfind(';'), win.rfind(':'))
        if cut != -1:
            win = win[cut + 1:]
        if not any(neg and neg in win for neg in negators):
            c += 1
    return c

# ---------- gates ----------
def canonical_values(manifest):
    s = set()
    for c in manifest.get('claims', []):
        for n in c.get('necessary_numbers', []):
            s.add(str(n))
    return s

def gate_L1(section_rel, orig_text, cand_text, cur, cand, manifest):
    canon = canonical_values(manifest)
    necessary = sorted({str(n) for c in manifest.get('claims', []) for n in c.get('necessary_numbers', [])})
    added = list((section_numbers(cand_text) - section_numbers(orig_text)).elements())
    illegal_adds = sorted({t for t in added if t not in canon})
    lost_necessary = sorted({n for n in necessary if cur['nums'][n] > 0 and cand['nums'][n] <= 0})
    lost_cites = sorted({c for c in cur['cites'] if cur['cites'][c] > 0 and cand['cites'][c] <= 0})
    dangling_refs = sorted({r for r in cand['refs'] if cand['labels'][r] <= 0})
    issues = []
    if illegal_adds: issues.append(f"illegal numeric additions (fabrication guard): {illegal_adds}")
    if lost_necessary: issues.append(f"necessary numbers lost paper-wide: {lost_necessary}")
    if lost_cites: issues.append(f"last paper-wide occurrence of citation(s) removed: {lost_cites}")
    if dangling_refs: issues.append(f"dangling \\ref with no \\label: {dangling_refs}")
    return {'pass': not issues, 'issues': issues, 'illegal_adds': illegal_adds,
            'lost_necessary': lost_necessary, 'lost_cites': lost_cites, 'dangling_refs': dangling_refs}

def gate_L2(cur, cand, manifest):
    # Per-scope floors + required_groups + dedup classification (design v4 §3).
    # Back-compat: a D-lock with neither `floors` nor `required_groups` keeps the
    # legacy single-scope min_count behaviour (oh==0 -> calibration warning).
    missing_required, calib_warn, floor_unbound, dedup_ok = [], [], [], []
    for rp in manifest.get('required_phrases', []):
        rid = rp.get('id')
        declared = bool(rp.get('floors') or rp.get('required_groups'))
        default_floors = rp.get('floors') or {rp.get('scope', 'paper'): rp.get('min_count', 1)}
        if rp.get('required_groups'):
            groups = [(g.get('name'), g.get('match_any', []), g.get('floors') or default_floors)
                      for g in rp['required_groups']]
        else:
            groups = [(None, rp.get('match_any', []), default_floors)]
        for gname, raw_variants, floors_map in groups:
            variants = [normalize_for_match(v).strip() for v in raw_variants]
            for scope, min_inst in floors_map.items():
                oh = count_variants(variants, scope_text(cur, scope))
                ch = count_variants(variants, scope_text(cand, scope))
                rec = {'id': rid, 'group': gname, 'scope': scope, 'orig_hits': oh, 'cand_hits': ch}
                if oh == 0:
                    if declared:
                        floor_unbound.append(rec)          # NON-silent: declared floor with no live hit
                    else:
                        calib_warn.append(rid)             # legacy default-scope calibration warning
                    continue
                floor = min(int(min_inst), oh)
                if ch < floor:
                    rec['floor'] = floor; rec['concept'] = rp.get('concept')
                    missing_required.append(rec)
                elif ch < oh:
                    dedup_ok.append(rec)                    # redundant restatement removed, floor still met
    forbidden_introduced = []
    for ft in manifest.get('forbidden_terms', []):
        term = normalize_for_match(ft.get('term', '')).strip()
        if not term:
            continue
        negs = [normalize_for_match(n).strip() for n in ft.get('negators', [])]
        oc = count_unnegated(term, negs, cur['paper_norm'])
        cc = count_unnegated(term, negs, cand['paper_norm'])
        if cc > oc:
            forbidden_introduced.append({'id': ft.get('id'), 'term': term, 'orig': oc, 'cand': cc})
    issues = []
    if missing_required: issues.append(f"required phrases dropped below floor (floor_breach): {[(r['id'], r.get('group'), r['scope']) for r in missing_required]}")
    if floor_unbound: issues.append(f"declared floor(s) unbound -- no live hit: {[(r['id'], r.get('group'), r['scope']) for r in floor_unbound]}")
    if forbidden_introduced: issues.append(f"new un-negated forbidden term(s): {[h['id'] for h in forbidden_introduced]}")
    return {'pass': not issues, 'issues': issues, 'missing_required': missing_required,
            'floor_unbound': floor_unbound, 'dedup_ok': dedup_ok,
            'forbidden_introduced': forbidden_introduced, 'calibration_unmatched': calib_warn}

def gate_L3(cur, cand, manifest):
    req_by_id = {rp.get('id'): rp for rp in manifest.get('required_phrases', [])}
    def covered(state, claim):
        for n in claim.get('necessary_numbers', []):
            if state['nums'][str(n)] <= 0:
                return False
        for pid in claim.get('required_phrase_ids', []):
            rp = req_by_id.get(pid)
            if not rp:
                continue
            variants = [normalize_for_match(v).strip() for v in rp.get('match_any', [])]
            if count_variants(variants, scope_text(state, rp.get('scope', 'paper'))) < 1:
                return False
        return True
    regressed = []
    for c in manifest.get('claims', []):
        if covered(cur, c) and not covered(cand, c):
            miss_n = [n for n in c.get('necessary_numbers', []) if cand['nums'][str(n)] <= 0]
            regressed.append({'claim_id': c.get('claim_id'), 'newly_missing_numbers': miss_n})
    return {'pass': not regressed,
            'issues': ([f"claims regressed to uncovered: {[r['claim_id'] for r in regressed]}"] if regressed else []),
            'regressed_claims': regressed}

# ---------- L4: caption / Description locks (the §8/Fig4-clobber guard) ----------
def _extract_braced(s, brace_start):
    depth = 0
    for i in range(brace_start, len(s)):
        if s[i] == '{':
            depth += 1
        elif s[i] == '}':
            depth -= 1
            if depth == 0:
                return s[brace_start + 1:i]
    return s[brace_start + 1:]

def float_blocks(text):
    """Return {label: {'caption':..., 'description':...}} for figure/table floats,
    using balanced-brace extraction so nested macros in captions are handled."""
    t = stripComments_safe(text)
    blocks = {}
    for env in ('figure', 'table'):
        for m in re.finditer(r'\\begin\{' + env + r'\*?\}', t):
            endm = re.search(r'\\end\{' + env + r'\*?\}', t[m.end():])
            seg = t[m.end(): m.end() + endm.start()] if endm else t[m.end():]
            lab = re.search(r'\\label\{([^}]*)\}', seg)
            if not lab:
                continue
            label = lab.group(1).strip()
            cap = desc = ''
            cm = re.search(r'\\caption\*?', seg)
            if cm:
                b = seg.find('{', cm.end())
                if b != -1:
                    cap = _extract_braced(seg, b)
            dm = re.search(r'\\Description', seg)
            if dm:
                b = seg.find('{', dm.end())
                if b != -1:
                    desc = _extract_braced(seg, b)
            blocks[label] = {'caption': cap, 'description': desc}
    return blocks

def stripComments_safe(text):
    return inv.strip_comments(text)

def gate_L4(section_rel, orig_text, cand_text, manifest):
    locks = [c for c in manifest.get('caption_locks', []) if c.get('section') == section_rel]
    if not locks:
        return {'pass': True, 'issues': [], 'violations': []}
    cur_b = float_blocks(orig_text)
    cand_b = float_blocks(cand_text)
    violations = []
    for lk in locks:
        label = lk['label']
        if label not in cur_b:
            continue  # this float isn't in this section's current text; nothing to protect here
        cb = cand_b.get(label)
        if cb is None:
            violations.append({'label': label, 'issue': 'caption/float for label removed'})
            continue
        full = normalize_for_match(cb['caption']) + ' ' + normalize_for_match(cb['description'])
        for sub in lk.get('must_contain', []):
            s = normalize_for_match(sub).strip()
            if s and s not in full:
                violations.append({'label': label, 'missing_phrase': sub})
        cap_nums = inv.extract_numbers(inv.expand_macros(inv.strip_comments(cb['caption'] + ' ' + cb['description']), MACROS))
        for num in lk.get('must_contain_numbers', []):
            if str(num) not in cap_nums:
                violations.append({'label': label, 'missing_number': num})
        if lk.get('require_description') and not cb['description'].strip():
            violations.append({'label': label, 'issue': 'Description block removed/empty'})
    issues = [f"caption-lock violations: {violations}"] if violations else []
    return {'pass': not violations, 'issues': issues, 'violations': violations}

# ---------- L5: hedge monotonicity (no conditional->assertive strip) ----------
def gate_L5(section_rel, orig_text, cand_text, manifest):
    locks = [h for h in manifest.get('hedge_locks', []) if h.get('section') in (section_rel, 'paper')]
    on = normalize_for_match(orig_text)
    cn = normalize_for_match(cand_text)
    stripped = []
    for h in locks:
        for ph in h.get('phrases', []):
            p = normalize_for_match(ph).strip()
            if p and on.count(p) > cn.count(p):
                stripped.append({'phrase': ph, 'orig': on.count(p), 'cand': cn.count(p)})
    issues = [f"protected hedge(s) removed/reduced: {[s['phrase'] for s in stripped]}"] if stripped else []
    return {'pass': not stripped, 'issues': issues, 'stripped': stripped}

def run_gates(section_rel, cand_text, manifest):
    section_rel = section_rel.replace('\\', '/')
    orig_text = disk_text(section_rel)
    cur = compute_state({})
    cand = compute_state({section_rel: cand_text})
    L1 = gate_L1(section_rel, orig_text, cand_text, cur, cand, manifest)
    L2 = gate_L2(cur, cand, manifest)
    L3 = gate_L3(cur, cand, manifest)
    L4 = gate_L4(section_rel, orig_text, cand_text, manifest)
    L5 = gate_L5(section_rel, orig_text, cand_text, manifest)
    ok = L1['pass'] and L2['pass'] and L3['pass'] and L4['pass'] and L5['pass']
    return {'section': section_rel, 'pass': ok, 'L1': L1, 'L2': L2, 'L3': L3, 'L4': L4, 'L5': L5}

def load_manifest(path=DEFAULT_MANIFEST):
    return json.load(open(path, encoding='utf-8'))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--section', required=True)
    ap.add_argument('--candidate', required=True)
    ap.add_argument('--manifest', default=DEFAULT_MANIFEST)
    a = ap.parse_args()
    if not os.path.exists(os.path.join(PAPER_DIR, a.section.replace('\\', '/'))):
        print(json.dumps({'error': f'section not found: {a.section}'})); sys.exit(2)
    res = run_gates(a.section, read(a.candidate), load_manifest(a.manifest))
    print(json.dumps(res, indent=2, ensure_ascii=False))
    sys.exit(0 if res['pass'] else 1)

if __name__ == '__main__':
    main()
