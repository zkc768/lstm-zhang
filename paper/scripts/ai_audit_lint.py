#!/usr/bin/env python3
"""ai_audit_lint.py -- schema gate for Final-QC AI-use audit artifacts.

Validates the per-round artifacts required by revision workflow §10:
  - ai_use_log.json
  - similarity_triage_report.md, when the round used an external similarity/AI
    report or the caller passes --require-similarity-report.

This is a process-integrity gate, not an AI-detector-score gate. It checks that
the accepted round records tools, input scope, edit motivation, human
disposition, severity, applied state, anchor-lint evidence, overlap provenance,
and hashes. It also flags report language that turns a detector/similarity score
into an acceptance target.

Exit 0 = clean, 1 = findings to review, 2 = usage/IO/JSON error.
Usage:
  python ai_audit_lint.py --round-dir paper/length_loop/runs/r0NN
  python ai_audit_lint.py --ai-use-log path/to/ai_use_log.json
  python ai_audit_lint.py --ai-use-log path/to/ai_use_log.json --similarity-report path/to/report.md
  python ai_audit_lint.py --selftest
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import latex_inventory as inv

PAPER_DIR = inv.PAPER_DIR

REQUIRED_TOP_LEVEL = {
    'round_id': str,
    'mode': str,
    'tools': list,
    'input_scope': list,
    'edits': list,
    'anchor_lint': dict,
    'overlap_provenance': list,
    'hashes': dict,
    'note': str,
}
ALLOWED_MODE = 'final_qc_similarity_triage'
ALLOWED_DISPOSITIONS = {'accept', 'reject', 'modify'}
ALLOWED_SEVERITIES = {'P0', 'P1', 'P2', 'none'}
REQUIRED_EDIT_FIELDS = {
    'region': str,
    'motivation': str,
    'from_external_report': bool,
    'human_disposition': str,
    'severity': str,
    'applied': bool,
}
FORBIDDEN_SCORE_TARGETS = [
    re.compile(r'\b(detector|similarity|ai)\s+score\b.{0,40}\b(target|goal|acceptance|threshold)\b', re.I),
    re.compile(r'\b(must|need|needs|should)\s+(reach|hit|get|achieve)\b.{0,40}\b(score|similarity)\b', re.I),
    re.compile(r'\b(score|similarity)\b.{0,30}\b(must|needs?|should)\s+(be\s+)?(below|under|less than|lower than)\b', re.I),
]

def rel(path):
    if not path:
        return ''
    try:
        return os.path.relpath(path, PAPER_DIR).replace('\\', '/')
    except ValueError:
        return path

def nonempty_string(value):
    return isinstance(value, str) and bool(value.strip())

def list_of_strings(value):
    return isinstance(value, list) and all(isinstance(x, str) and x.strip() for x in value)

def add(findings, code, message, severity='P1', path=''):
    findings.append({'code': code, 'message': message, 'severity': severity, 'path': path})

def validate_log(payload):
    findings = []
    if not isinstance(payload, dict):
        add(findings, 'top_level_type', 'ai_use_log.json must be one JSON object', 'P0')
        return findings
    for key, expected_type in REQUIRED_TOP_LEVEL.items():
        if key not in payload:
            add(findings, 'missing_field', f'missing required field: {key}', 'P0')
            continue
        if not isinstance(payload[key], expected_type):
            add(findings, 'field_type', f'{key} must be {expected_type.__name__}', 'P0')
    if payload.get('mode') != ALLOWED_MODE:
        add(findings, 'mode', f'mode must be {ALLOWED_MODE!r}', 'P1')
    if not nonempty_string(payload.get('round_id')):
        add(findings, 'round_id', 'round_id must be a non-empty string', 'P0')
    if not list_of_strings(payload.get('tools')):
        add(findings, 'tools', 'tools must be a non-empty list of strings', 'P0')
    if not list_of_strings(payload.get('input_scope')):
        add(findings, 'input_scope', 'input_scope must be a non-empty list of strings', 'P0')
    note = payload.get('note')
    if isinstance(note, str) and 'not an acceptance target' not in note.lower():
        add(findings, 'note', 'note must state that similarity / detector score is not an acceptance target', 'P1')
    validate_edits(payload.get('edits'), findings)
    validate_anchor(payload.get('anchor_lint'), findings)
    validate_overlap(payload.get('overlap_provenance'), findings)
    validate_hashes(payload.get('hashes'), findings)
    return findings

def validate_edits(edits, findings):
    if not isinstance(edits, list) or not edits:
        add(findings, 'edits', 'edits must be a non-empty list', 'P0')
        return
    for idx, edit in enumerate(edits):
        path = f'edits[{idx}]'
        if not isinstance(edit, dict):
            add(findings, 'edit_type', 'each edit must be an object', 'P0', path)
            continue
        for key, expected_type in REQUIRED_EDIT_FIELDS.items():
            if key not in edit:
                add(findings, 'missing_edit_field', f'missing edit field: {key}', 'P0', path)
                continue
            if not isinstance(edit[key], expected_type):
                add(findings, 'edit_field_type', f'{key} must be {expected_type.__name__}', 'P0', path)
        if edit.get('human_disposition') not in ALLOWED_DISPOSITIONS:
            add(findings, 'human_disposition', 'human_disposition must be accept|reject|modify', 'P1', path)
        if edit.get('severity') not in ALLOWED_SEVERITIES:
            add(findings, 'severity', 'severity must be P0|P1|P2|none', 'P1', path)
        if not nonempty_string(edit.get('motivation')):
            add(findings, 'motivation', 'motivation must be non-empty', 'P1', path)
        if not nonempty_string(edit.get('region')):
            add(findings, 'region', 'region must be non-empty', 'P1', path)

def validate_anchor(anchor, findings):
    if not isinstance(anchor, dict):
        return
    count = anchor.get('anchor_absent_count')
    if not isinstance(count, int) or count < 0:
        add(findings, 'anchor_absent_count', 'anchor_absent_count must be a non-negative integer', 'P1')
    if not list_of_strings(anchor.get('sections')):
        add(findings, 'anchor_sections', 'anchor_lint.sections must be a non-empty list of strings', 'P1')

def validate_overlap(entries, findings):
    if not isinstance(entries, list):
        return
    for idx, entry in enumerate(entries):
        path = f'overlap_provenance[{idx}]'
        if not isinstance(entry, dict):
            add(findings, 'overlap_entry_type', 'overlap_provenance entries must be objects', 'P1', path)
            continue
        if not nonempty_string(entry.get('passage')):
            add(findings, 'overlap_passage', 'overlap passage must be non-empty', 'P1', path)
        if not nonempty_string(entry.get('source')):
            add(findings, 'overlap_source', 'overlap source must be non-empty; use "none" explicitly when none was reused', 'P1', path)

def validate_hashes(hashes, findings):
    if not isinstance(hashes, dict):
        return
    for key in ('candidate_sha256', 'manifest_sha256'):
        if not nonempty_string(hashes.get(key)):
            add(findings, 'hashes', f'hashes.{key} must be a non-empty string', 'P1')

def similarity_report_required(payload, force):
    if force:
        return True
    if not isinstance(payload, dict):
        return False
    edits = payload.get('edits', [])
    return any(isinstance(e, dict) and e.get('from_external_report') for e in edits)

def validate_similarity_report(path, required):
    findings = []
    if not path:
        if required:
            add(findings, 'similarity_report_missing', 'similarity_triage_report.md is required for this round', 'P0')
        return findings
    if not os.path.exists(path):
        if required:
            add(findings, 'similarity_report_missing', f'similarity report not found: {path}', 'P0')
        return findings
    text = open(path, encoding='utf-8').read()
    findings.extend(validate_similarity_report_text(text))
    return findings

def load_json(path):
    try:
        with open(path, encoding='utf-8') as fh:
            return json.load(fh), None
    except FileNotFoundError:
        return None, f'ai_use_log.json not found: {path}'
    except json.JSONDecodeError as exc:
        return None, f'invalid JSON in {path}: {exc}'

def build_paths(args):
    ai_log = args.ai_use_log
    report = args.similarity_report
    if args.round_dir:
        ai_log = ai_log or os.path.join(args.round_dir, 'ai_use_log.json')
        report = report or os.path.join(args.round_dir, 'similarity_triage_report.md')
    if not ai_log:
        ai_log = os.path.join(PAPER_DIR, 'length_loop', 'runs', 'r0NN', 'ai_use_log.json')
    if not os.path.isabs(ai_log):
        ai_log = os.path.join(os.getcwd(), ai_log)
    if report and not os.path.isabs(report):
        report = os.path.join(os.getcwd(), report)
    return ai_log, report

def lint(ai_log, report, force_report=False):
    payload, error = load_json(ai_log)
    if error:
        return {'verdict': 'FINDINGS', 'findings': [{'code': 'ai_use_log_missing_or_invalid',
                'message': error, 'severity': 'P0', 'path': rel(ai_log)}], 'payload': None}
    findings = validate_log(payload)
    findings.extend(validate_similarity_report(report, similarity_report_required(payload, force_report)))
    return {'verdict': 'FINDINGS' if findings else 'CLEAN', 'findings': findings, 'payload': payload}

def clean_payload():
    return {
        'round_id': 'r001',
        'mode': 'final_qc_similarity_triage',
        'tools': ['anchor_lint.py', 'similarity tool'],
        'input_scope': ['sections/01_intro.tex'],
        'edits': [{
            'region': 'sections/01_intro.tex:paragraph-2',
            'motivation': 'clarity',
            'from_external_report': False,
            'human_disposition': 'accept',
            'severity': 'none',
            'applied': True,
        }],
        'anchor_lint': {'anchor_absent_count': 0, 'sections': ['sections/01_intro.tex']},
        'overlap_provenance': [{'passage': 'none', 'source': 'none'}],
        'hashes': {'candidate_sha256': 'abc123', 'manifest_sha256': 'def456'},
        'note': 'similarity score is NOT an acceptance target (anti-AI §11).',
    }

def selftest():
    cases = []
    base = clean_payload()
    cases.append(('1 clean payload', len(validate_log(base)) == 0, True))
    missing = dict(base)
    missing.pop('round_id')
    cases.append(('2 missing required field', len(validate_log(missing)) >= 1, True))
    bad_severity = json.loads(json.dumps(base))
    bad_severity['edits'][0]['severity'] = 'critical'
    cases.append(('3 invalid severity', any(f['code'] == 'severity' for f in validate_log(bad_severity)), True))
    external = json.loads(json.dumps(base))
    external['edits'][0]['from_external_report'] = True
    cases.append(('4 external report requires companion', similarity_report_required(external, False), True))
    cases.append(('5 detector target phrase caught',
        len([f for f in validate_similarity_report_text('must reach a lower similarity score before acceptance') if f['code'] == 'detector_score_target']) == 1, True))
    npass = 0
    for name, got, expected in cases:
        ok = got == expected
        npass += ok
        print(f"[{'OK ' if ok else 'XX '}] {name}: got={got} expected={expected}")
    print(f"\nAI_AUDIT_LINT SELFTEST: {npass}/{len(cases)} cases behaved as expected.")
    return npass == len(cases)

def validate_similarity_report_text(text):
    findings = []
    if not text.strip():
        add(findings, 'similarity_report_empty', 'similarity report is empty', 'P0')
    for pat in FORBIDDEN_SCORE_TARGETS:
        if pat.search(text):
            add(findings, 'detector_score_target', 'report language treats a detector/similarity score as an acceptance target', 'P0')
            break
    return findings

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--round-dir', default='')
    ap.add_argument('--ai-use-log', default='')
    ap.add_argument('--similarity-report', default='')
    ap.add_argument('--require-similarity-report', action='store_true')
    ap.add_argument('--out', default='')
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()
    if args.selftest:
        sys.exit(0 if selftest() else 1)
    ai_log, report = build_paths(args)
    result = lint(ai_log, report, args.require_similarity_report)
    output = {
        'tool': 'ai_audit_lint.py',
        'ai_use_log': rel(ai_log),
        'similarity_report': rel(report),
        'findings': result['findings'],
        'verdict': result['verdict'],
        'note': 'Final-QC process gate; detector/similarity score is never an acceptance target.',
    }
    if args.out:
        os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
        json.dump(output, open(args.out, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    print(json.dumps(output, indent=2, ensure_ascii=False))
    sys.exit(0 if output['verdict'] == 'CLEAN' else 1)

if __name__ == '__main__':
    main()
