#!/usr/bin/env python3
"""Deep anti-homogenization metric: per-sentence GPT-2 perplexity + burstiness.

Mirrors how AI-text detectors actually work (GPTZero-style, and GitHub detectors like
shreyavenghat25/ai-text-detector, umairinayat/AI-Detection):
  - mean perplexity                         : LOWER = more predictable = more AI-like
  - stdev of per-sentence perplexity (= BURSTINESS) : LOWER = more uniform = more AI-like

This is the proper version of the lightweight sentence-LENGTH-variance proxy in
check_integrity.py. Use it as an INTERNAL signal, compared ACROSS revision passes
(if a pass LOWERS mean perplexity or burstiness, that is homogenization -> stop). It is
NOT a detector and NOT a target to optimize against (project rule: never game detectors;
detectors false-positive on non-native authors).

Usage:  python paper_compare/perplexity_burstiness.py <file.tex> [more.tex ...]
Needs:  pip install transformers   (torch + numpy already present)
First run downloads GPT-2 (~500MB).
"""
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")  # work around torch OpenMP double-load
import re, sys, glob, math, statistics


def strip_latex(t):
    t = "\n".join(l for l in t.split("\n") if not l.strip().startswith("%"))
    t = re.sub(r"\\begin\{(table|tabular|figure)\*?\}.*?\\end\{\1\*?\}", " ", t, flags=re.S)
    t = re.sub(r"\\(section|paragraph)\*?\{[^}]*\}", " ", t)
    t = re.sub(r"\\cite\{[^}]*\}", "", t)
    t = re.sub(r"\\[a-zA-Z]+\*?\{[^}]*\}", "", t)
    t = re.sub(r"\\[a-zA-Z]+", "", t)
    t = re.sub(r"\\[^a-zA-Z]", " ", t)
    t = re.sub(r"[{}$]", " ", t)
    return " ".join(t.split())


def sentences(t):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", t) if len(s.split()) >= 4]


def main():
    try:
        import torch
        from transformers import GPT2LMHeadModel, GPT2TokenizerFast
    except Exception as e:
        print("MISSING transformers (or torch). Install:  pip install transformers")
        print("detail:", e)
        sys.exit(2)

    files = []
    for a in sys.argv[1:]:
        files += glob.glob(a)
    if not files:
        print("usage: python paper_compare/perplexity_burstiness.py <file.tex ...>")
        sys.exit(2)

    tok = GPT2TokenizerFast.from_pretrained("gpt2")
    model = GPT2LMHeadModel.from_pretrained("gpt2").eval()
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(dev)

    def ppl(text):
        ids = tok(text, return_tensors="pt").input_ids.to(dev)
        if ids.size(1) < 2:
            return None
        with torch.no_grad():
            loss = model(ids, labels=ids).loss
        return math.exp(min(loss.item(), 20.0))

    for f in sorted(set(files)):
        sents = sentences(strip_latex(open(f, encoding="utf-8").read()))
        vals = [p for p in (ppl(s) for s in sents) if p is not None]
        if len(vals) < 4:
            print(f"{f}: too few sentences ({len(vals)})")
            continue
        mean = statistics.mean(vals)
        sd = statistics.pstdev(vals)
        flags = []
        if mean < 30:
            flags.append("low mean perplexity (very predictable)")
        if sd < 12:
            flags.append("low burstiness (uniform per-sentence perplexity)")
        note = ("  <- " + "; ".join(flags)) if flags else "  (ok)"
        print(f"{f}: mean_perplexity={mean:.1f}  burstiness_sd={sd:.1f}  n={len(vals)}{note}")

    print("\nThresholds are heuristic. The reliable read is the DELTA across revision passes:")
    print("a pass that LOWERS mean perplexity or burstiness_sd is homogenizing the text.")


if __name__ == "__main__":
    main()
