#!/usr/bin/env python3
"""anchor_lint.py -- ADVISORY anchor-absence triage for non-empirical paper prose.

Mechanical aid for the Final-QC Originality / Similarity Triage lens
(docs/protocols/lst_models_paper_revision_workflow.md section 8.2, step 3). It
flags paragraphs in the HIGH-similarity-risk non-empirical sections (default
section 1 Intro and section 2 Related) that carry ZERO project-specific anchor --
the connective/background prose where template text and external similarity
concentrate.

A paragraph is ANCHORED if, after the shared length_gates normalization, it
contains at least one of:
  - a \\cite or \\ref key (binds to project literature / a project float),
  - a numeric token (a project result/parameter; macros are expanded so
    \\numseeds etc. count),
  - a project-specific required-phrase from protection_manifest.json
    (required_phrases[].match_any -- the machine-truth list of load-bearing
    project phrases). NO hand-maintained wordlist lives in this file; the
    lexicon is sourced entirely from the manifest, so it never drifts from the
    claims/Doc-B contracts.

A paragraph with none of these is reported `anchor_absent`. This is a TRIAGE
SIGNAL, not a fail-closed gate and not an apply-blocking verdict: a human (or the
Triage reviewer lens) confirms whether the paragraph is genuine template filler
to compress/cut, or a legitimately anchor-light bridge sentence. Per section 8.2
the fix is NEVER to fabricate a number or upgrade a hedge to manufacture an
anchor. This linter has no apply authority; it never edits sections/*.tex.

Known lenience (advisory tool biases toward NOT flagging): macro expansion makes
\\macrofone render a digit, so a bare macro-F1 mention reads as number-anchored.
That is acceptable -- macro-F1 is the project estimand, a legitimate anchor.

Exit 0 = no anchor-absent paragraph; 1 = >=1 anchor-absent paragraph (review);
2 = usage/IO error.
Usage:
  python anchor_lint.py                          # scan section 1 + section 2 (default)
  python anchor_lint.py --section sections/01_intro.tex [--section ...]
  python anchor_lint.py --section main.tex       # scans the abstract environment only
  python anchor_lint.py --min-words 12 [--verbose] [--out report.json]
  python anchor_lint.py --selftest
"""
import re, os, sys, json, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import latex_inventory as inv
import length_gates as G

PAPER_DIR = inv.PAPER_DIR
DEFAULT_SECTIONS = ['sections/01_intro.tex', 'sections/02_related.tex']

def strip_floats(text):
    t = inv.strip_comments(text)
    return re.sub(r'\\begin\{(figure|table)\*?\}.*?\\end\{\1\*?\}', ' ', t, flags=re.S)

def section_body(relpath, text):
    """For main.tex, scan the abstract environment only (the non-empirical part);
    for a normal section, scan the whole file."""
    if relpath.endswith('main.tex'):
        m = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', text, flags=re.S)
        return m.group(1) if m else ''
    return text

def split_paragraphs(text):
    body = re.sub(r'\\(?:sub)*section\*?\{[^}]*\}', ' ', strip_floats(text))
    return [p.strip() for p in re.split(r'\n\s*\n', body) if p.strip()]

def load_anchor_lexicon(manifest):
    """Project-anchor phrases = every required_phrases[].match_any, normalized
    with the SAME tokenizer the gates use. Single source of truth = the manifest."""
    lex = set()
    for rp in manifest.get('required_phrases', []):
        for v in rp.get('match_any', []):
            s = G.normalize_for_match(v).strip()
            if s:
                lex.add(s)
    return lex

def paragraph_anchors(para, lexicon):
    raw = inv.strip_comments(para)
    keys = inv.extract_keys(raw)
    nums = inv.extract_numbers(inv.expand_macros(raw, G.MACROS))
    norm = G.normalize_for_match(para)
    phrases = sorted({p for p in lexicon if p in norm})
    return {'cite': keys['cite'], 'ref': keys['ref'],
            'n_numbers': len(nums), 'numbers': nums, 'phrases': phrases}

def is_anchored(a):
    return bool(a['cite'] or a['ref'] or a['n_numbers'] or a['phrases'])

def lint_section(relpath, lexicon, min_words):
    text = section_body(relpath, open(os.path.join(PAPER_DIR, relpath), encoding='utf-8').read())
    records, flagged = [], []
    for i, para in enumerate(split_paragraphs(text), 1):
        wc = inv.word_count(para)
        if wc < min_words:
            continue  # headings / short fragments are not template-risk prose
        a = paragraph_anchors(para, lexicon)
        anchored = is_anchored(a)
        rec = {'section': relpath, 'paragraph': i, 'words': wc, 'anchored': anchored,
               'anchors': {'cite': a['cite'], 'ref': a['ref'],
                           'n_numbers': a['n_numbers'], 'phrases': a['phrases']},
               'snippet': re.sub(r'\s+', ' ', para)[:90]}
        records.append(rec)
        if not anchored:
            flagged.append(rec)
    return records, flagged

def run(sections, min_words, verbose):
    manifest = G.load_manifest()
    lexicon = load_anchor_lexicon(manifest)
    all_records, all_flagged = [], []
    for s in sections:
        recs, fl = lint_section(s, lexicon, min_words)
        all_records += recs
        all_flagged += fl
    report = {
        'tool': 'anchor_lint.py',
        'advisory': True,
        'note': ('anchor_absent is a TRIAGE SIGNAL for the Final-QC Similarity '
                 'Triage lens (revision workflow 8.2), not an apply-blocking verdict; '
                 'a human confirms filler-to-cut vs legitimate bridge. Never '
                 'fabricate an anchor to clear a flag.'),
        'lexicon_size': len(lexicon),
        'sections_scanned': sections,
        'min_words': min_words,
        'paragraphs_checked': len(all_records),
        'anchor_absent_count': len(all_flagged),
        'anchor_absent': all_flagged,
    }
    if verbose:
        report['all_paragraphs'] = all_records
    return report

def selftest():
    manifest = G.load_manifest()
    lex = load_anchor_lexicon(manifest)
    cases = []
    filler = ("In recent years, deep learning has attracted increasing attention from "
              "researchers across many fields, opening up new avenues for future work "
              "and showing great potential.")
    cases.append(('1 template filler -> absent', not is_anchored(paragraph_anchors(filler, lex)), True))
    proj = "We report the binding row-pooled estimand with an equal-weight companion."
    cases.append(('2 project phrase -> anchored', is_anchored(paragraph_anchors(proj, lex)), True))
    cite = "Asset-pricing studies apply machine-learning models to panels \\cite{gu2020empirical}."
    cases.append(('3 cite -> anchored', is_anchored(paragraph_anchors(cite, lex)), True))
    num = "The margin is 1.69 in the seed mean."
    cases.append(('4 number -> anchored', is_anchored(paragraph_anchors(num, lex)), True))
    ok5 = len(lex) > 0
    for s in DEFAULT_SECTIONS:
        lint_section(s, lex, 12)  # must not raise
    cases.append(('5 lexicon built + section 1/2 scan runs', ok5, True))
    npass = 0
    for name, got, exp in cases:
        ok = (got == exp)
        npass += ok
        print(f"[{'OK ' if ok else 'XX '}] {name}: got={got} expected={exp}")
    print(f"\nANCHOR_LINT SELFTEST: {npass}/{len(cases)} cases behaved as expected.")
    return npass == len(cases)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--section', action='append', default=None, help='repeatable; default section 1 + section 2')
    ap.add_argument('--min-words', type=int, default=12)
    ap.add_argument('--verbose', action='store_true')
    ap.add_argument('--out', default='')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    sections = [s.replace('\\', '/') for s in (a.section or DEFAULT_SECTIONS)]
    for s in sections:
        if not os.path.exists(os.path.join(PAPER_DIR, s)):
            print(json.dumps({'error': f'section not found: {s}'})); sys.exit(2)
    report = run(sections, a.min_words, a.verbose)
    if a.out:
        os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
        json.dump(report, open(a.out, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    sys.exit(0 if report['anchor_absent_count'] == 0 else 1)

if __name__ == '__main__':
    main()
