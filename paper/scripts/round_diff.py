#!/usr/bin/env python3
"""round_diff.py -- allowlist-enforcing gate report for ONE revision round.

This is the "gatekeeper" the orchestrator runs (read-only). It:
  1. runs L1-L5 deterministic gates (length_gates.run_gates),
  2. classifies the candidate's CHANGED regions vs the current on-disk section
     (#body / caption:<label> / description:<label>) and ENFORCES a per-round
     region allowlist -- any changed region NOT in the allowlist -> BLOCK,
  3. records hash-backed evidence (frozen baseline / current / candidate /
     manifest / bib sha256 + freshness),
  4. writes runs/<round_id>/gate_report.json.

Verdict is PERMIT_REVIEW (gates pass AND no unauthorized region) or BLOCK.
PERMIT_REVIEW is NOT acceptance -- it only permits the L4 semantic panel; the
synthesizer + orchestrator decide apply/rollback downstream.

Usage:
  python round_diff.py --section sections/08_diagnostics.tex \
      --candidate paper/length_loop/runs/<rid>/candidate_08.tex \
      --round-id <rid> --allowlist "#body,caption:fig:tercile_map"
      [--allowlist paper/length_loop/runs/<rid>/PLAN.md]   # or parse tags from PLAN.md
"""
import re, os, sys, json, hashlib, argparse, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import latex_inventory as inv
import length_gates as G

PAPER_DIR = inv.PAPER_DIR

def sha_file(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest() if os.path.exists(p) else None

def body_without_floats(text):
    t = inv.strip_comments(text)
    t = re.sub(r'\\begin\{(figure|table)\*?\}.*?\\end\{\1\*?\}', ' ', t, flags=re.S)
    return re.sub(r'\s+', ' ', t).strip()

def _norm(s):
    return re.sub(r'\s+', ' ', s).strip()

def region_diff(orig, cand):
    """Regions that changed between orig and cand: '#body', 'caption:<label>', 'description:<label>'."""
    changed = []
    if body_without_floats(orig) != body_without_floats(cand):
        changed.append('#body')
    ob, cb = G.float_blocks(orig), G.float_blocks(cand)
    for lab in sorted(set(ob) | set(cb)):
        o = ob.get(lab, {'caption': '', 'description': ''})
        c = cb.get(lab, {'caption': '', 'description': ''})
        if _norm(o['caption']) != _norm(c['caption']):
            changed.append('caption:' + lab)
        if _norm(o['description']) != _norm(c['description']):
            changed.append('description:' + lab)
    return changed

def parse_allowlist(arg):
    if arg and os.path.exists(arg):  # PLAN.md: lines like "- allow: #body" or "- caption:fig:x"
        txt = open(arg, encoding='utf-8').read()
        return set(re.findall(r'(#body|caption:[\w:.\-]+|description:[\w:.\-]+)', txt))
    return set(t.strip() for t in (arg or '').split(',') if t.strip())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--section', required=True)
    ap.add_argument('--candidate', required=True)
    ap.add_argument('--round-id', default='r000')
    ap.add_argument('--allowlist', default='')
    ap.add_argument('--manifest', default=G.DEFAULT_MANIFEST)
    ap.add_argument('--baseline', default=os.path.join(PAPER_DIR, 'length_loop', 'baseline_inventory.json'))
    ap.add_argument('--out', default='')
    a = ap.parse_args()
    section = a.section.replace('\\', '/')
    section_path = os.path.join(PAPER_DIR, section)
    if not os.path.exists(section_path):
        print(json.dumps({'error': 'section not found: ' + section})); sys.exit(2)
    manifest = G.load_manifest(a.manifest)
    cand_text = open(a.candidate, encoding='utf-8').read()
    orig_text = open(section_path, encoding='utf-8').read()

    gates = G.run_gates(section, cand_text, manifest)
    changed = region_diff(orig_text, cand_text)
    allow = parse_allowlist(a.allowlist)
    unauthorized = [r for r in changed if r not in allow]

    base = json.load(open(a.baseline, encoding='utf-8'))
    brow = next((f for f in base.get('detail', []) if f['file'] == section), None)
    cur_sha = sha_file(section_path)
    report = {
        'round_id': a.round_id,
        'section': section,
        'command': f'round_diff.py --section {section} --candidate {a.candidate} --round-id {a.round_id}',
        'timestamp': datetime.datetime.now().isoformat(timespec='seconds'),
        'hashes': {
            'frozen_baseline_sha256': brow['sha256'] if brow else None,
            'current_on_disk_sha256': cur_sha,
            'candidate_sha256': sha_file(a.candidate),
            'manifest_sha256': sha_file(a.manifest),
            'bib_sha256': sha_file(os.path.join(PAPER_DIR, 'references.bib')),
            'current_matches_frozen_baseline': (brow['sha256'] == cur_sha) if brow else None,
        },
        'gates': {
            'L1_numbers_keys': gates['L1'], 'L2_required_forbidden': gates['L2'],
            'L3_claim_coverage': gates['L3'], 'L4_caption_lock': gates['L4'], 'L5_hedge': gates['L5'],
            'all_pass': gates['pass'],
        },
        'diff': {'changed_regions': changed, 'allowlist': sorted(allow), 'unauthorized_regions': unauthorized},
        'verdict': 'PERMIT_REVIEW' if (gates['pass'] and not unauthorized) else 'BLOCK',
        'note': 'PERMIT_REVIEW is not acceptance; L4 semantic panel + synthesizer decide apply/rollback.',
    }
    out = a.out or os.path.join(PAPER_DIR, 'length_loop', 'runs', a.round_id, 'gate_report.json')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(report, open(out, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    print(json.dumps({'verdict': report['verdict'], 'all_gates_pass': gates['pass'],
                      'changed_regions': changed, 'unauthorized_regions': unauthorized,
                      'report': os.path.relpath(out, PAPER_DIR)}, indent=2, ensure_ascii=False))
    sys.exit(0 if report['verdict'] == 'PERMIT_REVIEW' else 1)

if __name__ == '__main__':
    main()
