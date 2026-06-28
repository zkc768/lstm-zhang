#!/usr/bin/env python3
"""Reusable integrity gate for lst_models paper sections (pilot round 1 fix).

Usage:
    python paper_compare/check_integrity.py <file.tex> [more.tex ...]

HARD checks (cause exit 1): red-line claim tokens, "two domains", Tier-1 AI vocab,
phrase blacklist, sentences > 35 words.
WARN checks (reported, do not fail): guarded phrases that may not be negated, em-dash
in body, >2 commentary sentence-openers.

Does NOT verify number<->ledger binding (still a manual step). Exit 0 if no HARD fail.
"""
import re, sys, glob, statistics

RED_LINE_CLAIMS = [r"\bbest\b", r"\boutperform\w*", r"\bsuperior\b", r"\bsignificant\w*",
    r"\bprofitable\b", r"\bwell[ -]?calibrated\b", r"\bstate[ -]of[ -]the[ -]art\b",
    r"\bSOTA\b", r"\bsurpass\w*", r"\btradable\b"]
GUARDED_PHRASES = ["clean test", "out-of-sample proof", "final model", "unseen holdout",
    "untouched holdout", "historically contacted"]
TIER1_BANNED = ["delve","leverage","tapestry","testament","beacon","realm","pinnacle",
    "epitome","cornerstone","watershed","vibrant","bustling","groundbreaking","cutting-edge",
    "seamless","holistic","unparalleled","unprecedented","multifaceted","meticulous",
    "paramount","unveil","transcend","galvanize","nurture","underscore","myriad","plethora",
    "aforementioned","nestled"]
PHRASE_BLACKLIST = ["it is worth noting","plays a crucial role","plays a pivotal role",
    "plays a vital role","sheds light on","holds great promise","bridge the gap",
    "in recent years","opens new avenues","opens up new avenues","rapidly evolving",
    "this highlights the importance","this underscores the importance"]

def strip_latex(t):
    t = "\n".join(l for l in t.split("\n") if not l.strip().startswith("%"))
    # drop table/figure environments so table rows are not counted as prose sentences
    t = re.sub(r"\\begin\{(table|tabular|figure)\*?\}.*?\\end\{\1\*?\}", " ", t, flags=re.S)
    t = re.sub(r"\\section\*?\{[^}]*\}", "", t)
    t = re.sub(r"\\cite\{[^}]*\}", "REF", t)
    t = re.sub(r"\\[a-zA-Z]+\*?\{[^}]*\}", "X", t)
    t = re.sub(r"\\[a-zA-Z]+", "X", t)
    t = re.sub(r"\\[^a-zA-Z]", " ", t)
    t = re.sub(r"[{}$]", " ", t)
    return t

def check(path):
    raw = open(path, encoding="utf-8").read()
    body = "\n".join(l for l in raw.split("\n") if not l.strip().startswith("%"))
    low = body.lower()
    hard, warn = [], []

    hits = sorted({m.group(0).lower() for pat in RED_LINE_CLAIMS
                   for m in re.finditer(pat, body, re.I)})
    if hits: hard.append(("red-line claim tokens", hits))

    if re.search(r"\btwo domains\b", low): hard.append(("'two domains' (expect three)", ["two domains"]))

    t1 = sorted({w for w in TIER1_BANNED if re.search(r"\b"+re.escape(w)+r"\b", low)})
    if t1: hard.append(("Tier-1 AI vocab", t1))

    pb = [p for p in PHRASE_BLACKLIST if p in low]
    if pb: hard.append(("phrase blacklist", pb))

    tx = " ".join(strip_latex(raw).split())
    longs = [f"{len(s.split())}w: {s.strip()[:60]}" for s in re.split(r"(?<=\.)\s+", tx)
             if len(s.split()) > 35]
    if longs: hard.append((">35-word sentences", longs))

    gp = []
    for ph in GUARDED_PHRASES:
        for m in re.finditer(re.escape(ph), low):
            pre = low[max(0, m.start()-12):m.start()]
            if not re.search(r"\b(not|no|never)\b\s*(a\s+|an\s+)?$", pre):
                gp.append(ph)
    if gp: warn.append(("guarded phrase may not be negated (verify)", sorted(set(gp))))

    if "---" in body or "—" in body: warn.append(("em-dash in body", ["---/em-dash"]))

    openers = re.findall(r"(?m)^\s*(Moreover|Furthermore|Additionally|Notably|Importantly)\b", body)
    if len(openers) > 2: warn.append(("too many commentary openers", openers))

    sent_lens = [len(s.split()) for s in re.split(r"(?<=\.)\s+", tx) if len(s.split()) >= 3]
    if len(sent_lens) >= 6:
        sd = statistics.pstdev(sent_lens)
        if sd < 6.0:
            warn.append((f"low burstiness (sentence-length sd={sd:.1f}, aim >6 -- uniform AI rhythm)",
                         [f"n={len(sent_lens)} sentences"]))

    return hard, warn

def main():
    files = []
    for a in sys.argv[1:]:
        files += glob.glob(a)
    if not files:
        print("usage: python paper_compare/check_integrity.py <file.tex ...>"); sys.exit(2)
    any_hard = False
    for f in sorted(set(files)):
        hard, warn = check(f)
        status = "FAIL" if hard else "PASS"
        if hard: any_hard = True
        print(f"{status} {f}")
        for name, items in hard:
            print(f"  [HARD] {name}: {items[:10]}")
        for name, items in warn:
            print(f"  [warn] {name}: {items[:10]}")
    print("\nRESULT:", "HARD FAIL" if any_hard else "all hard checks passed")
    sys.exit(1 if any_hard else 0)

if __name__ == "__main__":
    main()
