#!/usr/bin/env python3
"""Unified LaTeX inventory for the lst_models paper length-reduction loop.

SINGLE SOURCE OF TRUTH for: numeric tokens, cite/ref/label keys, word counts,
and file freeze hashes. Replaces the ad-hoc per-section tmp/check*.py scripts
(which hard-coded tokens, used inconsistent tokenizers, and depended on temp
paths).

One consistent rule set handles:
  - comment stripping (unescaped %)
  - macro expansion (\\newcommand read from main.tex: \\numseeds, \\macrofone, \\pp, ...)
  - numeric ranges (2017--2024, en/em dash)
  - thousands separators (736{,}685 and 736,685 -> 736685)
  - scientific notation (10^{-3}, 4.7e-4, 4.7\\times 10^{-4}) -> exact Decimal value
  - cite/ref/label variants (\\cite \\citep \\citet \\autoref \\ref \\eqref \\Cref \\label, multi-key)
  - caption / table / \\Description text counted in scope

Usage:
  python latex_inventory.py --paper [--full]      # all sections + main.tex + whole-paper aggregate
  python latex_inventory.py FILE [FILE ...] [--full]
Outputs a JSON summary to stdout; with --full also dumps per-file token lists.
"""
import re, json, sys, os, hashlib
from decimal import Decimal, getcontext

getcontext().prec = 50
HERE = os.path.dirname(os.path.abspath(__file__))
PAPER_DIR = os.path.dirname(HERE)               # .../paper
SECTIONS_DIR = os.path.join(PAPER_DIR, 'sections')
MAIN_TEX = os.path.join(PAPER_DIR, 'main.tex')

# ---------- text normalization ----------
def strip_comments(s):
    return re.sub(r'(?<!\\)%.*', '', s)

def load_macros(main_tex=MAIN_TEX):
    macros = {}
    try:
        txt = strip_comments(open(main_tex, encoding='utf-8').read())
    except FileNotFoundError:
        return macros
    for m in re.finditer(r'\\newcommand\{\\([A-Za-z]+)\}(?:\[\d+\])?\{([^{}]*)\}', txt):
        macros[m.group(1)] = m.group(2)
    return macros

def expand_macros(s, macros):
    for _ in range(4):
        before = s
        for name, body in macros.items():
            s = re.sub(r'\\' + re.escape(name) + r'\{\}', body, s)
            s = re.sub(r'\\' + re.escape(name) + r'(?![A-Za-z])', body, s)
        if s == before:
            break
    return s

# ---------- numbers ----------
def _dec_str(d):
    s = format(d, 'f')
    if '.' in s:
        s = s.rstrip('0').rstrip('.')
    return s

def extract_numbers(s):
    """Return sorted list of canonical numeric tokens.
    Sci-notation -> exact decimal string; plain numbers kept as written (sig figs)."""
    sci = []
    # a\times 10^{b} / a\cdot 10^{b}
    def rep_times(m):
        sci.append(_dec_str(Decimal(m.group(1)) * (Decimal(10) ** int(m.group(2)))))
        return ' '
    s = re.sub(r'(\d+(?:\.\d+)?)\s*\\(?:times|cdot)\s*10\^\{?(-?\d+)\}?', rep_times, s)
    # a e b   (4.7e-4)
    def rep_e(m):
        sci.append(_dec_str(Decimal(m.group(1)) * (Decimal(10) ** int(m.group(2)))))
        return ' '
    s = re.sub(r'(\d+(?:\.\d+)?)[eE]([+-]?\d+)\b', rep_e, s)
    # standalone 10^{-k}
    def rep_pow(m):
        sci.append(_dec_str(Decimal(10) ** int(m.group(1))))
        return ' '
    s = re.sub(r'10\^\{?(-?\d+)\}?', rep_pow, s)
    # ranges: digit (-- / en / em dash) digit -> space (avoid spurious negative)
    s = re.sub(r'(?<=\d)\s*(?:---|--|–|—)\s*(?=\d)', ' ', s)
    # thousands  736{,}685  and  736,685
    s = re.sub(r'(?<=\d)\{,\}(?=\d{3})', '', s)
    s = re.sub(r'(?<=\d),(?=\d{3}(?!\d))', '', s)
    plain = re.findall(r'[+-]?\d+(?:\.\d+)?', s)
    return sorted(plain + sci)

# ---------- keys ----------
def extract_keys(s):
    cites, refs, labels = [], [], []
    for m in re.finditer(r'\\(cite[A-Za-z]*|autoref|eqref|[cC]ref|ref|label)\*?(?:\[[^\]]*\])?\{([^}]*)\}', s):
        cmd, body = m.group(1), m.group(2)
        for k in (x.strip() for x in body.split(',')):
            if not k:
                continue
            if cmd.startswith('cite'):
                cites.append(k)
            elif cmd == 'label':
                labels.append(k)
            else:
                refs.append(k)
    return {'cite': sorted(cites), 'ref': sorted(refs), 'label': sorted(labels)}

# ---------- words ----------
def word_count(s):
    s = strip_comments(s)
    # drop key/file command args entirely so keys/filenames are not counted as words
    s = re.sub(r'\\(?:cite[A-Za-z]*|autoref|eqref|[cC]ref|ref|label|includegraphics|input|bibliography|bibliographystyle)\*?(?:\[[^\]]*\])?\{[^}]*\}', ' ', s)
    s = re.sub(r'\$[^$]*\$', ' ', s)                 # inline math
    s = re.sub(r'\\\((.*?)\\\)', ' ', s)             # \( ... \)
    s = re.sub(r'\\[A-Za-z]+\*?(?:\[[^\]]*\])?', ' ', s)  # remaining commands (keep {arg} text)
    s = re.sub(r'[{}$&~^_\\]', ' ', s)
    return len(re.findall(r"[A-Za-z][A-Za-z'\-]*", s))

# ---------- per-file ----------
def inventory_file(path, macros):
    raw = open(path, encoding='utf-8').read()
    body = expand_macros(strip_comments(raw), macros)
    nums = extract_numbers(body)
    keys = extract_keys(strip_comments(raw))   # keys from comment-stripped (pre-expand) text
    return {
        'file': os.path.relpath(path, PAPER_DIR).replace('\\', '/'),
        'sha256': hashlib.sha256(raw.encode('utf-8')).hexdigest(),
        'mtime': os.path.getmtime(path),
        'bytes': len(raw.encode('utf-8')),
        'words': word_count(raw),
        'numbers': nums,
        'n_numbers': len(nums),
        'cite': keys['cite'], 'ref': keys['ref'], 'label': keys['label'],
        'n_cite': len(keys['cite']), 'n_ref': len(keys['ref']), 'n_label': len(keys['label']),
    }

def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    flags = {a for a in sys.argv[1:] if a.startswith('--')}
    macros = load_macros()
    if '--paper' in flags:
        files = [MAIN_TEX] + sorted(
            os.path.join(SECTIONS_DIR, f) for f in os.listdir(SECTIONS_DIR) if f.endswith('.tex'))
    else:
        files = [os.path.abspath(a) for a in args]
    if not files:
        print('usage: latex_inventory.py --paper [--full] | FILE ...', file=sys.stderr)
        sys.exit(2)
    inv = [inventory_file(f, macros) for f in files]
    total_words = sum(x['words'] for x in inv)
    all_nums = sorted(n for x in inv for n in x['numbers'])
    all_cite = sorted(set(c for x in inv for c in x['cite']))
    summary = {
        'macros_expanded': macros,
        'files': [{k: x[k] for k in ('file', 'words', 'n_numbers', 'n_cite', 'n_ref', 'n_label', 'sha256')} for x in inv],
        'totals': {'files': len(inv), 'words': total_words,
                   'numeric_tokens': len(all_nums), 'unique_cite_keys': len(all_cite)},
    }
    if '--full' in flags:
        summary['detail'] = inv
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))

if __name__ == '__main__':
    main()
