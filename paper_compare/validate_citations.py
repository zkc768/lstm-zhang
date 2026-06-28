#!/usr/bin/env python3
"""Citation validator (PaperOrchestra-style anti-hallucination upgrade).

Checks that every \\cite key actually used in the compiled draft (a) resolves to a
references.bib entry, and (b) corresponds to a REAL paper, verified against the
Semantic Scholar Graph API (existence + title/year/first-author agreement).

Resolution strategy (rate-limit aware):
  1. BATCH endpoint (one POST) for every entry that has a DOI or arXiv id -> exact lookup,
     dodges the per-call rate limit that throttles the search endpoint.
  2. title SEARCH for the remainder (conf papers w/o DOI), throttled + exponential backoff on 429.

Network goes through `curl` (WebFetch/urllib may be blocked in this env; curl works).
This is descriptive anti-hallucination tooling, NOT a substitute for the human
VERIFY-BEFORE-SUBMIT publisher-page check (Doc A 10); it flags entries whose bib note
still carries a "VERIFY" marker.

Usage:
  python paper_compare/validate_citations.py \
      --tex "paper_compare/v2_skill_draft/sections/*.tex" "paper_compare/v2_skill_draft/main.tex" \
      --bib paper_compare/v2_skill_draft/references.bib \
      [--offline] [--json-out report.json]
"""
import argparse, glob, json, os, re, subprocess, sys, tempfile, time, urllib.parse

SS = "https://api.semanticscholar.org/graph/v1"
FIELDS = "title,year,authors.name,externalIds"
SEARCH_THROTTLE_S = 3.0
BACKOFF = [8, 16, 32, 64]      # 429 exponential backoff for single GETs


# ----------------------------- parsing -------------------------------------
def strip_comments(t):
    out = []
    for line in t.split("\n"):
        m = re.search(r"(?<!\\)%", line)
        out.append(line[: m.start()] if m else line)
    return "\n".join(out)


def used_cite_keys(tex_files):
    keys = {}
    cite_cmd = re.compile(r"\\(?:cite|citep|citet|citeyear|citeauthor)\*?\{([^}]*)\}", re.S)
    for f in tex_files:
        raw = strip_comments(open(f, encoding="utf-8").read())
        for m in cite_cmd.finditer(raw):
            for k in m.group(1).split(","):
                k = k.strip()
                if k:
                    keys.setdefault(k, []).append(f)
    return keys


def parse_bib(bib_file):
    text = open(bib_file, encoding="utf-8").read()
    entries, i, n = {}, 0, len(text)
    while True:
        at = text.find("@", i)
        if at < 0:
            break
        brace = text.find("{", at)
        if brace < 0:
            break
        depth, j = 0, brace
        while j < n:
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        body = text[brace + 1 : j]
        etype = text[at + 1 : brace].strip().lower()
        i = j + 1
        if etype in ("comment", "preamble", "string"):
            continue
        key = body.split(",", 1)[0].strip()
        if not key:
            continue
        fields = {}
        for fm in re.finditer(r"(\w+)\s*=\s*", body):
            name = fm.group(1).lower()
            if name == key.lower():
                continue
            p = fm.end()
            if p >= len(body):
                continue
            if body[p] == "{":
                d, q = 0, p
                while q < len(body):
                    if body[q] == "{":
                        d += 1
                    elif body[q] == "}":
                        d -= 1
                        if d == 0:
                            break
                    q += 1
                fields[name] = body[p + 1 : q]
            elif body[p] == '"':
                q = body.find('"', p + 1)
                fields[name] = body[p + 1 : q if q > 0 else len(body)]
            else:
                q = re.search(r"[,\n]", body[p:])
                fields[name] = body[p : p + (q.start() if q else 0)].strip()
        entries[key] = fields
    return entries


# ----------------------------- normalization -------------------------------
def norm_title(s):
    s = re.sub(r"\\[a-zA-Z]+", " ", s)
    s = re.sub(r"[{}\\$~]", " ", s)
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return " ".join(s.split())


def first_author_surname(author_field):
    if not author_field:
        return ""
    first = re.split(r"\s+and\s+", author_field.strip())[0]
    first = re.sub(r"\\[a-zA-Z]+", "", first)
    first = re.sub(r"[{}\\'\"`~^]", "", first)
    sur = first.split(",")[0] if "," in first else (first.split()[-1] if first.split() else "")
    return re.sub(r"[^a-z]", "", sur.lower())


def jaccard(a, b):
    sa, sb = set(a.split()), set(b.split())
    return len(sa & sb) / len(sa | sb) if sa and sb else 0.0


def title_match(bib_t, ss_t):
    a, b = norm_title(bib_t), norm_title(ss_t)
    if not a or not b:
        return False
    return a in b or b in a or jaccard(a, b) >= 0.6


# ----------------------------- network -------------------------------------
def curl(args):
    try:
        r = subprocess.run(["curl", "-s", "-w", "\n%{http_code}", "--max-time", "40"] + args,
                           capture_output=True, text=True, timeout=60)
        out = r.stdout
    except Exception as e:
        return None, f"curl-fail:{e}"
    if "\n" not in out:
        return None, "no-response"
    payload, code = out.rsplit("\n", 1)
    code = code.strip()
    if code != "200":
        return None, code
    try:
        return json.loads(payload), None
    except Exception:
        return None, "bad-json"


def ss_get(path):
    for delay in [0] + BACKOFF:
        if delay:
            time.sleep(delay)
        data, err = curl([f"{SS}/{path}"])
        if err == "429":
            continue
        return data, err
    return None, "429-persist"


def ss_batch(ids):
    """POST /paper/batch — one call resolves many DOI/arXiv ids. Returns dict id->record."""
    if not ids:
        return {}
    result = {}
    for start in range(0, len(ids), 100):
        chunk = ids[start:start + 100]
        body = json.dumps({"ids": chunk})
        tf = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        tf.write(body); tf.close()
        data, err = None, None
        for delay in [0] + BACKOFF:
            if delay:
                time.sleep(delay)
            data, err = curl(["-X", "POST", f"{SS}/paper/batch?fields={FIELDS}",
                              "-H", "Content-Type: application/json", "-d", f"@{tf.name}"])
            if err == "429":
                continue
            break
        os.unlink(tf.name)
        if isinstance(data, list):
            for cid, rec in zip(chunk, data):
                result[cid] = rec      # rec may be None (not found)
        else:
            for cid in chunk:
                result[cid] = ("ERR", err)
        time.sleep(1.0)
    return result


# ----------------------------- matching ------------------------------------
def match_record(fields, data):
    title = fields.get("title", "")
    try:
        byear = int(re.search(r"\d{4}", fields.get("year", "")).group(0)) if fields.get("year") else None
    except Exception:
        byear = None
    sur = first_author_surname(fields.get("author", ""))
    res = {"bib_title": title[:88], "bib_year": byear,
           "doi": fields.get("doi", "").strip() or None,
           "eprint": fields.get("eprint", "").strip() or None,
           "verify_note": "VERIFY" in fields.get("note", "").upper()}
    if not data or not isinstance(data, dict):
        res["status"] = "UNRESOLVED"
        res["detail"] = "not-found" if data is None else str(data)
        return res
    ss_t = data.get("title", "")
    ss_y = data.get("year")
    authors = [a.get("name", "") for a in (data.get("authors") or [])]
    tmatch = title_match(title, ss_t)
    ymatch = (byear is None or ss_y is None or abs(byear - ss_y) <= 1)
    amatch = (not sur) or any(sur in re.sub(r"[^a-z]", "", a.lower()) for a in authors)
    res.update({"ss_title": ss_t[:88], "ss_year": ss_y, "title_match": tmatch,
                "year_match": ymatch, "author_match": amatch, "ss_id": data.get("paperId")})
    res["status"] = "RESOLVED" if (tmatch and ymatch and amatch) else (
        "RESOLVED*" if (tmatch and (ymatch or amatch)) else "MISMATCH")
    return res


# ----------------------------- main ----------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tex", nargs="+", required=True)
    ap.add_argument("--bib", required=True)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    tex_files = sorted({f for pat in args.tex for f in glob.glob(pat)})
    used = used_cite_keys(tex_files)
    bib = parse_bib(args.bib)
    used_keys = sorted(used)
    undefined = [k for k in used_keys if k not in bib]
    unused = sorted(set(bib) - set(used_keys))

    print(f"tex files: {len(tex_files)} | used cite keys: {len(used_keys)} | bib entries: {len(bib)}")
    print(f"\n[LOCAL] used-but-undefined (would break compile): {len(undefined)}")
    for k in undefined:
        print(f"   !! {k}  (in {', '.join(used[k])})")
    print(f"[LOCAL] bib-defined-but-unused (informational): {len(unused)}")
    if unused:
        print("   " + ", ".join(unused))
    if args.offline:
        print("\n[offline] skipping Semantic Scholar verification.")
        sys.exit(1 if undefined else 0)

    # ---- batch-resolve DOI / arXiv entries (1 call each chunk) ----
    id_for = {}
    for k in used_keys:
        f = bib.get(k, {})
        doi = f.get("doi", "").strip()
        ep = f.get("eprint", "").strip()
        if doi:
            id_for[k] = f"DOI:{doi}"
        elif ep:
            id_for[k] = f"ARXIV:{ep}"
    print(f"\n[NET] batch-resolving {len(id_for)} DOI/arXiv entries in one request...")
    batch = ss_batch(list(dict.fromkeys(id_for.values())))

    print(f"[NET] verifying {len(used_keys)} cited entries (search fallback throttled)...\n")
    results, counts = [], {}
    for k in used_keys:
        if k not in bib:
            r = {"key": k, "status": "UNDEFINED-IN-BIB"}
        else:
            f = bib[k]
            data, method = None, None
            if k in id_for and isinstance(batch.get(id_for[k]), dict):
                data, method = batch[id_for[k]], ("doi" if id_for[k].startswith("DOI") else "arxiv")
            if data is None:               # no id, or batch missed -> title search
                method = "search"
                sr, _ = ss_get(f"paper/search?query={urllib.parse.quote(norm_title(f.get('title','')))}"
                               f"&limit=6&fields={FIELDS}")
                if sr and sr.get("data"):
                    data = max(sr["data"], key=lambda p: jaccard(norm_title(f.get("title", "")),
                                                                 norm_title(p.get("title", ""))))
                time.sleep(SEARCH_THROTTLE_S)
            r = match_record(f, data)
            r["key"] = k
            r["method"] = method
        results.append(r)
        counts[r["status"]] = counts.get(r["status"], 0) + 1
        tag = " [bib-note:VERIFY]" if r.get("verify_note") else ""
        line = f"  {r['status']:<12} {k:<26} via {r.get('method','-')}{tag}"
        if r["status"] in ("MISMATCH", "RESOLVED*"):
            line += f"\n        bib: {r.get('bib_title')} ({r.get('bib_year')})"
            line += (f"\n        ss : {r.get('ss_title')} ({r.get('ss_year')})  "
                     f"[title={r.get('title_match')} year={r.get('year_match')} author={r.get('author_match')}]")
        elif r["status"] == "UNRESOLVED":
            line += f"   ({r.get('detail')})  bib: {r.get('bib_title')}"
        print(line, flush=True)

    print("\n==================== SUMMARY ====================")
    for s in ("RESOLVED", "RESOLVED*", "MISMATCH", "UNRESOLVED", "UNDEFINED-IN-BIB"):
        if counts.get(s):
            print(f"  {s:<16} {counts[s]}")
    vnotes = [r["key"] for r in results if r.get("verify_note")]
    print(f"  bib-note VERIFY  {len(vnotes)}  ({', '.join(vnotes) or '-'})")
    print(f"  unused bib       {len(unused)}")

    if args.json_out:
        json.dump({"used": used_keys, "undefined": undefined, "unused": unused,
                   "results": results, "counts": counts}, open(args.json_out, "w"), indent=2)
        print(f"\nwrote {args.json_out}")

    hard = undefined or counts.get("MISMATCH") or counts.get("UNRESOLVED") or counts.get("UNDEFINED-IN-BIB")
    sys.exit(1 if hard else 0)


if __name__ == "__main__":
    main()
