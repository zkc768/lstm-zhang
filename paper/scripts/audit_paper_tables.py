#!/usr/bin/env python3
"""audit_paper_tables.py -- field-level provenance audit for the paper's tables.

Submission-grade auditable table chain: every NUMERIC cell in the three formal
tables (Table 1 dataset / Table 2 validation / Table 3 activity-tercile) is
re-derived from its bound artifact field through a declared transform + rounding
rule, then matched against the value printed in the LaTeX float. Read-only.

It answers, per displayed number:
    table_label -> claim_id -> artifact path -> field -> transform -> displayed -> verdict

Two directions are checked (the "bidirectional set membership" property):
  (A) expected -> displayed: each artifact-bound expected value (rounded to its
      declared precision) MUST appear, at that precision, in the table float.
      A missing/precision-drifted value is a MISMATCH (fabrication / drift guard).
  (B) displayed -> expected: each numeric token in the float MUST be accounted
      for by some expected value OR an explicitly declared structural number.
      Anything left over is an ORPHAN (unsourced number guard).

The source-of-truth is the `table_sources` block in protection_manifest.json
(NOT a parallel file): it cross-references the same claim_id values the L1 gate
already protects. This script and length_gates.py share one manifest.

Outputs paper/length_loop/table_audit_report.{json,md} (hash-stamped), prints a
summary, and exits 0 only when every cell is PASS and no ORPHAN remains.

Usage:
  python audit_paper_tables.py [--manifest <path>] [--out-json <path>] [--quiet]
"""
import os
import re
import sys
import csv
import json
import hashlib
import argparse
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import latex_inventory as inv

PAPER_DIR = inv.PAPER_DIR
REPO_ROOT = os.path.dirname(PAPER_DIR)
MACROS = inv.load_macros()
DEFAULT_MANIFEST = os.path.join(PAPER_DIR, 'length_loop', 'protection_manifest.json')
ROUNDING_RULE = 'ROUND_HALF_UP'  # declared, uniform; recorded in the report


# ---------------------------------------------------------------- artifacts --
def sha256_file(path):
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def _load_yaml(path):
    try:
        import yaml  # optional; the gate scripts are otherwise stdlib-only
        with open(path, encoding='utf-8') as fh:
            return yaml.safe_load(fh)
    except ImportError:
        # Minimal scalar fallback: flat/one-level "key: value" lines only. The
        # only YAML this audit reads is configs/stages/00_*.yaml (simple scalars).
        root, stack = {}, [(-1, None)]
        with open(path, encoding='utf-8') as fh:
            for raw in fh:
                if not raw.strip() or raw.lstrip().startswith('#'):
                    continue
                indent = len(raw) - len(raw.lstrip(' '))
                m = re.match(r'\s*([A-Za-z0-9_]+):\s*(.*?)\s*$', raw)
                if not m:
                    continue
                key, val = m.group(1), m.group(2)
                while stack and stack[-1][0] >= indent:
                    stack.pop()
                parent = stack[-1][1]
                parent = root if parent is None else parent
                if val == '':
                    parent[key] = {}
                    stack.append((indent, parent[key]))
                else:
                    parent[key] = val.strip().strip('"').strip("'")
        return root


def load_artifact(rel_path):
    """Return (kind, data). Paths are relative to the repo root."""
    path = os.path.join(REPO_ROOT, rel_path.replace('\\', '/'))
    if not os.path.exists(path):
        raise FileNotFoundError(rel_path)
    ext = os.path.splitext(path)[1].lower()
    if ext == '.csv':
        with open(path, encoding='utf-8') as fh:
            return 'csv', list(csv.DictReader(fh)), path
    if ext == '.json':
        with open(path, encoding='utf-8') as fh:
            return 'json', json.load(fh), path
    if ext in ('.yaml', '.yml'):
        return 'yaml', _load_yaml(path), path
    raise ValueError(f'unsupported artifact type: {rel_path}')


def dotted(obj, key):
    cur = obj
    for part in key.split('.'):
        cur = cur[part]
    return cur


def select_rows(rows, where):
    out = []
    for r in rows:
        if all(str(r.get(k, '')).strip() == str(v).strip() for k, v in (where or {}).items()):
            out.append(r)
    return out


# ----------------------------------------------------------------- derive ----
def _agg(values, how):
    if not values:
        raise ValueError('no rows matched the filter')
    if how in (None, 'none', 'first'):
        return values[0]
    if how == 'mean':
        return sum(values) / len(values)
    if how == 'min':
        return min(values)
    if how == 'max':
        return max(values)
    if how == 'sum':
        return sum(values)
    raise ValueError(f'unknown agg: {how}')


def derive_expected(entry):
    """Re-derive the expected printed quantity from the bound artifact field.

    Returns a dict describing the derivation (kind + value/strings) so the report
    can show the full transform chain. Raises on any source/IO problem so a
    mis-declared source surfaces loudly instead of silently passing.
    """
    kind, data, abspath = load_artifact(entry['artifact'])
    mode = entry.get('mode', 'number')
    field = entry.get('field')
    where = entry.get('where')
    agg = entry.get('agg', 'none')
    src_sha = sha256_file(abspath)

    if mode == 'date':
        if kind == 'yaml' or kind == 'json':
            raw = str(dotted(data, field))
        else:
            raw = str(select_rows(data, where)[0][field])
        return {'mode': mode, 'expected_str': raw.strip(), 'src_sha256': src_sha,
                'transform': f'read {field}'}

    if mode == 'ratio':
        # numerator field vs denominator (field or constant); printed as "a/b".
        rows = select_rows(data, where) if kind == 'csv' else None
        num = float(rows[0][field]) if rows else float(dotted(data, field))
        den_field = entry.get('den_field')
        den_const = entry.get('den_const')
        den = (float(rows[0][den_field]) if (den_field and rows)
               else float(den_const))
        return {'mode': mode, 'num': int(round(num)), 'den': int(round(den)),
                'expected_str': f'{int(round(num))}/{int(round(den))}',
                'src_sha256': src_sha, 'transform': f'{field}/{den_field or den_const}'}

    if mode == 'regex_int':
        rows = select_rows(data, where)
        val = str(rows[0][field])
        m = re.search(entry['pattern'], val)
        if not m:
            raise ValueError(f'regex {entry["pattern"]!r} no match in {val!r}')
        return {'mode': 'number', 'value': Decimal(m.group(1)), 'precision': 0,
                'expected_str': m.group(1), 'src_sha256': src_sha,
                'transform': f'{field} =~ {entry["pattern"]}'}

    # ----- numeric / descriptive_range -----
    if kind in ('yaml', 'json'):
        raw_vals = [Decimal(str(dotted(data, field)))]
    else:
        rows = select_rows(data, where)
        raw_vals = [Decimal(str(r[field])) for r in rows]
    scale = Decimal(str(entry.get('scale', 1)))
    precision = int(entry.get('round', 0))
    aggregated = _agg(raw_vals, agg) if agg not in (None, 'none', 'first') else raw_vals[0]
    if not isinstance(aggregated, Decimal):
        aggregated = Decimal(str(aggregated))
    scaled = aggregated * scale
    q = Decimal(1).scaleb(-precision)
    value = scaled.quantize(q, rounding=ROUND_HALF_UP)

    transform = f'read {field}'
    if agg not in (None, 'none', 'first'):
        transform = f'{agg}({field}) over {len(raw_vals)} rows'
    if scale != 1:
        transform += f' x{scale}'
    transform += f', round {precision} ({ROUNDING_RULE})'

    out = {'mode': 'number' if mode == 'number' else 'descriptive_range',
           'value': value, 'precision': precision, 'expected_str': _fmt(value, precision),
           'src_sha256': src_sha, 'transform': transform}
    if mode == 'descriptive_range':
        out['range_lo'] = Decimal(str(entry['range_lo']))
        out['range_hi'] = Decimal(str(entry['range_hi']))
    return out


def _fmt(dec, precision):
    return f'{dec:.{precision}f}'


# ------------------------------------------------------------- LaTeX float ---
def table_float_text(section_text, label):
    """Return the \\begin{table}...\\end{table} block carrying \\label{label}."""
    t = inv.strip_comments(section_text)
    for m in re.finditer(r'\\begin\{table\*?\}', t):
        endm = re.search(r'\\end\{table\*?\}', t[m.end():])
        seg = t[m.start(): m.end() + endm.end()] if endm else t[m.start():]
        if re.search(r'\\label\{' + re.escape(label) + r'\}', seg):
            return seg
    return None


def displayed_tokens(float_text):
    expanded = inv.expand_macros(float_text, MACROS)
    # \macrofone expands to the literal metric name 'macro-F1'; its trailing '1'
    # is a label, not a data value -- drop it so it is not a spurious token.
    expanded = expanded.replace('macro-F1', 'macro-F')
    # Unit-suffixed numeric ranges ("29.9k--30.8k") defeat the shared tokenizer's
    # range rule, which only fires digit--digit; here the dash run sits between a
    # unit letter and a digit, so the upper bound is mis-read as a negative. Split
    # "<unit><dash><digit>" into "<unit> <digit>" so the bound parses positive.
    expanded = re.sub(r'([kKmMbB%])\s*(?:---|--|–|—)\s*(?=\d)', r'\1 ', expanded)
    return inv.extract_numbers(expanded)


def to_dec(tok):
    try:
        return Decimal(tok.lstrip('+'))
    except (InvalidOperation, ValueError):
        return None


def decimals_of(tok):
    tok = tok.lstrip('+-')
    return len(tok.split('.', 1)[1]) if '.' in tok else 0


# ------------------------------------------------------------------ audit ----
DATE_RE = re.compile(r'\d{4}-\d{2}-\d{2}')


def match_number(expected, precision, tokens):
    """Find a token equal in value AND in decimal precision. Returns
    ('PASS', tok) | ('PRECISION_DRIFT', tok) | ('MISMATCH', None)."""
    value_hit = None
    for tok in tokens:
        d = to_dec(tok)
        if d is None:
            continue
        if d == expected:
            if decimals_of(tok) == precision:
                return 'PASS', tok
            value_hit = tok
    if value_hit is not None:
        return 'PRECISION_DRIFT', value_hit
    return 'MISMATCH', None


def audit(manifest_path, section_overrides=None):
    """Audit every table_sources cell. `section_overrides` ({section_rel: text})
    lets a self-test feed a tampered section in-memory without touching disk."""
    section_overrides = section_overrides or {}
    manifest = json.load(open(manifest_path, encoding='utf-8'))
    block = manifest.get('table_sources', [])
    sources = block.get('entries', []) if isinstance(block, dict) else block
    if not sources:
        raise SystemExit('manifest has no table_sources block')

    # group source entries by table label
    by_table = {}
    for e in sources:
        by_table.setdefault(e['table_label'], []).append(e)

    section_cache, results = {}, []
    for label, entries in by_table.items():
        section_rel = entries[0]['section']
        if section_rel not in section_cache:
            if section_rel in section_overrides:
                txt = section_overrides[section_rel]
                section_cache[section_rel] = (txt, hashlib.sha256(txt.encode('utf-8')).hexdigest())
            else:
                p = os.path.join(PAPER_DIR, section_rel)
                section_cache[section_rel] = (open(p, encoding='utf-8').read(), sha256_file(p))
        section_text, section_sha = section_cache[section_rel]
        float_text = table_float_text(section_text, label)
        if float_text is None:
            results.append({'table_label': label, 'section': section_rel,
                            'error': 'table float not found', 'cells': []})
            continue
        tokens = displayed_tokens(float_text)

        cells, matched_tokens = [], set()
        for e in entries:
            rec = {'table_label': label, 'claim_id': e.get('claim_id'),
                   'cell': e.get('cell'), 'artifact': e['artifact'],
                   'field': e.get('field'), 'section': section_rel,
                   'section_sha256': section_sha}
            try:
                d = derive_expected(e)
            except Exception as ex:  # noqa: BLE001 - surface any source error as a finding
                rec.update({'verdict': 'SOURCE_ERROR', 'detail': f'{type(ex).__name__}: {ex}'})
                cells.append(rec)
                continue
            rec['transform'] = d['transform']
            rec['src_sha256'] = d['src_sha256']
            rec['expected'] = d['expected_str']

            if d['mode'] == 'date':
                hit = d['expected_str'] in DATE_RE.findall(inv.strip_comments(float_text))
                rec['verdict'] = 'PASS' if hit else 'MISMATCH'
                if hit:
                    matched_tokens.update(re.findall(r'\d+', d['expected_str']))
            elif d['mode'] == 'ratio':
                rstr = d['expected_str']
                hit = re.search(re.escape(rstr), inv.expand_macros(float_text, MACROS)) is not None
                rec['verdict'] = 'PASS' if hit else 'MISMATCH'
                if hit:
                    matched_tokens.update([str(d['num']), str(d['den'])])
            elif d['mode'] == 'descriptive_range':
                lo, hi = d['range_lo'], d['range_hi']
                in_range = lo <= d['value'] <= hi
                # the printed range endpoints should both be present as tokens
                ep_present = all(any(to_dec(t) == ep for t in tokens) for ep in (lo, hi))
                rec['verdict'] = 'PASS' if (in_range and ep_present) else 'REVIEW'
                rec['detail'] = (f'artifact stat {d["expected_str"]} within printed '
                                 f'[{_fmt(lo, d["precision"])},{_fmt(hi, d["precision"])}]; '
                                 f'endpoints_present={ep_present}')
                for ep in (lo, hi):
                    for t in tokens:
                        if to_dec(t) == ep:
                            matched_tokens.add(t)
            else:  # number
                verdict, tok = match_number(d['value'], d['precision'], tokens)
                rec['verdict'] = verdict
                if tok is not None:
                    matched_tokens.add(tok)
                    rec['displayed'] = tok
            cells.append(rec)

        # ---- direction (B): orphan / structural accounting ----
        # Structural numbers are non-artifact tokens (counts, n-seeds, bar
        # frequencies) declared explicitly per table with a reason -- so they are
        # ACCOUNTED, never silently ignored. Dates are stripped (the shared
        # tokenizer mangles hyphenated dates into negative fragments); ratio cells
        # like "5/5" are covered via matched_tokens, so slash-separated value lists
        # (e.g. per-tercile row counts "44{,}144/51{,}572/55{,}348") stay intact.
        stripped = DATE_RE.sub(' ', inv.strip_comments(float_text))
        struct = {}
        for e in entries:
            for s in e.get('structural_numbers', []) or []:
                struct[str(s['value'])] = s.get('reason', '')
        struct_decs = {Decimal(str(k)) for k in struct}
        orphans = []
        for tok in displayed_tokens(inv.expand_macros(stripped, MACROS)):
            if tok in matched_tokens or tok in struct:
                continue
            d = to_dec(tok)
            if d is not None and d in struct_decs:
                continue
            orphans.append(tok)
        results.append({'table_label': label, 'section': section_rel,
                        'section_sha256': section_sha, 'cells': cells,
                        'orphans': sorted(set(orphans)),
                        'structural_numbers': struct})
    return manifest, results


# ----------------------------------------------------------------- report ----
def summarize(results):
    counts = {}
    for tbl in results:
        for c in tbl.get('cells', []):
            counts[c['verdict']] = counts.get(c['verdict'], 0) + 1
        if tbl.get('orphans'):
            counts['ORPHAN'] = counts.get('ORPHAN', 0) + len(tbl['orphans'])
        if tbl.get('error'):
            counts['TABLE_ERROR'] = counts.get('TABLE_ERROR', 0) + 1
    return counts


def clean_verdict(results):
    """Strict: clean only when every counted verdict is PASS (any MISMATCH /
    SOURCE_ERROR / TABLE_ERROR / ORPHAN / PRECISION_DRIFT / REVIEW fails)."""
    return set(summarize(results)) <= {'PASS'}


def write_reports(manifest, results, out_json):
    counts = summarize(results)
    ok = clean_verdict(results)
    payload = {
        'tool': 'audit_paper_tables.py',
        'manifest_version': manifest.get('version'),
        'rounding_rule': ROUNDING_RULE,
        'verdict': 'PASS' if ok else 'FINDINGS',
        'counts': counts,
        'tables': results,
    }
    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    json.dump(payload, open(out_json, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)

    md_path = os.path.splitext(out_json)[0] + '.md'
    lines = ['# Table field-level audit report', '',
             f'- tool: `audit_paper_tables.py` (read-only)',
             f'- manifest: `{manifest.get("version")}`',
             f'- rounding rule: `{ROUNDING_RULE}` (uniform, declared)',
             f'- verdict: **{payload["verdict"]}**  counts: `{counts}`', '']
    for tbl in results:
        lines.append(f'## `{tbl["table_label"]}`  ({tbl["section"]})')
        if tbl.get('error'):
            lines.append(f'- ERROR: {tbl["error"]}')
            lines.append('')
            continue
        lines.append('')
        lines.append('| cell | claim | artifact -> field | transform | expected | displayed | verdict |')
        lines.append('|---|---|---|---|---|---|---|')
        for c in tbl['cells']:
            disp = c.get('displayed', c.get('detail', ''))
            lines.append(
                f'| {c.get("cell","")} | {c.get("claim_id","")} | '
                f'`{c["artifact"]}` -> `{c.get("field","")}` | {c.get("transform","")} | '
                f'`{c.get("expected","")}` | {disp} | **{c["verdict"]}** |')
        if tbl.get('orphans'):
            lines.append('')
            lines.append(f'- ORPHAN tokens (displayed, unsourced): `{tbl["orphans"]}`')
        if tbl.get('structural_numbers'):
            lines.append(f'- declared structural numbers: `{tbl["structural_numbers"]}`')
        lines.append('')
    open(md_path, 'w', encoding='utf-8').write('\n'.join(lines))
    return payload, md_path, ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', default=DEFAULT_MANIFEST)
    ap.add_argument('--out-json', default=os.path.join(PAPER_DIR, 'length_loop', 'table_audit_report.json'))
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()
    manifest, results = audit(a.manifest)
    payload, md_path, ok = write_reports(manifest, results, a.out_json)
    print(json.dumps({'verdict': payload['verdict'], 'counts': payload['counts'],
                      'report_json': os.path.relpath(a.out_json, PAPER_DIR),
                      'report_md': os.path.relpath(md_path, PAPER_DIR)},
                     indent=2, ensure_ascii=False))
    if not a.quiet and not ok:
        for tbl in results:
            for c in tbl.get('cells', []):
                if c['verdict'] not in ('PASS',):
                    print(f'  [{c["verdict"]}] {tbl["table_label"]} / {c.get("cell")} '
                          f'expected={c.get("expected")} displayed={c.get("displayed","-")} '
                          f'{c.get("detail","")}', file=sys.stderr)
            if tbl.get('orphans'):
                print(f'  [ORPHAN] {tbl["table_label"]}: {tbl["orphans"]}', file=sys.stderr)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
