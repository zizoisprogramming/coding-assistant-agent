# 1. Export the FAILED runs (scripts/export_failed.py, written to /kaggle/working/code). CPU; Internet ON only for the
#    download list. Pass 1: full + retry outputs attached, DOWNLOAD = gen-extra-all v1 (the extra run).
#    Pass 2 (fresh session): only the combined run attached, DOWNLOAD = [].
import glob, hashlib, json, subprocess, sys, time
from pathlib import Path
CODE = Path('/kaggle/working/code')
CODE.mkdir(parents=True, exist_ok=True)
(CODE / 'export_failed.py').write_text('"""Compact copy of the FAILED runs of generation outputs, for reading them locally (failure-pattern analysis).\n\n    python3 scripts/export_failed.py GEN_DIR [GEN_DIR ...] --out failed.jsonl.gz\n\nA request log repeats the whole conversation in every line (~1.6 GB for all runs). Per failed run this keeps only the\nrecords that hold the conversation once: the last model call before each compaction (the summary drops the history\nafter it) and the run\'s last call, each with the model\'s reply; the tool schema is dropped. Plus the run\'s result row\nand its patch. One JSON line per run. Public tasks (level \'public\') are all kept: their grades were redone after the\nrun (re-grade), so `resolved` here is not final.\n"""\nimport argparse\nimport gzip\nimport json\nimport sys\nfrom pathlib import Path\n\nSUMMARY_PREFIX = "The following is a conversation history"\n\n\ndef is_summary(rec):\n    msgs = rec["request"].get("messages") or []\n    last = msgs[-1] if msgs else {}\n    return last.get("role") == "user" and str(last.get("content") or "").startswith(SUMMARY_PREFIX)\n\n\ndef slim(rec):\n    req = {k: v for k, v in rec["request"].items() if k != "tools"}\n    return {"t": rec.get("t"), "seconds": rec.get("seconds"), "request": req, "reply": rec.get("reply")}\n\n\ndef export(gen_dir, fh):\n    gen_dir = Path(gen_dir)\n    rows = {f"{r[\'instance_id\']}#a{r[\'attempt\']}": r for r in map(json.loads, open(gen_dir / "results/gen_per_task.jsonl"))}\n    want = {j for j, r in rows.items() if not r.get("resolved") or r.get("level") == "public"}\n    prev, kept, n_calls, bad = {}, {}, {}, 0\n    with open(gen_dir / "requests/requests.jsonl") as f:\n        for line in f:\n            try:\n                rec = json.loads(line)\n            except ValueError:\n                bad += 1\n                continue\n            job = rec.get("job")\n            if job not in want or not isinstance(rec.get("request"), dict):\n                continue\n            n_calls[job] = n_calls.get(job, 0) + 1\n            if is_summary(rec):\n                if job in prev:  # the history the summary is about to replace\n                    kept.setdefault(job, []).append(prev.pop(job))\n                kept.setdefault(job, []).append({"summary_call": True, "t": rec.get("t"), "seconds": rec.get("seconds"),\n                                                 "summary": ((rec.get("reply") or {}).get("message") or {}).get("content")})\n            else:\n                prev[job] = slim(rec)\n    n = 0\n    for job in sorted(want):\n        recs = kept.get(job, []) + ([prev[job]] if job in prev else [])\n        if not recs:\n            continue\n        r = rows[job]\n        pf = gen_dir / "results/gen/patches" / f"{r[\'instance_id\']}__a{r[\'attempt\']}.diff"\n        fh.write(json.dumps({"job": job, "src": gen_dir.name, "row": r, "patch": pf.read_text() if pf.exists() else None,\n                             "model_calls": n_calls.get(job, 0), "records": recs}) + "\\n")\n        n += 1\n    print(f"{gen_dir}: {n} runs exported of {len(rows)} ({len(want)} failed or public)"\n          + (f", {bad} unreadable log lines" if bad else ""), file=sys.stderr, flush=True)\n    return n\n\n\ndef main():\n    ap = argparse.ArgumentParser()\n    ap.add_argument("dirs", nargs="+")\n    ap.add_argument("--out", required=True)\n    a = ap.parse_args()\n    with gzip.open(a.out, "wt") as fh:\n        for d in a.dirs:\n            export(d, fh)\n\n\nif __name__ == "__main__":\n    main()\n')
DOWNLOAD = ['ziadsamer/gen-extra-all/versions/1']
roots = ['/kaggle/input']
for ref in DOWNLOAD:  # Kaggle allows this only in an INTERACTIVE session (a committed run refuses a new version)
    try:
        import kagglehub
        roots.append(kagglehub.dataset_download(ref))
        print('downloaded', ref, '->', roots[-1], flush=True)
    except Exception as e:  # noqa: BLE001
        print(f'WARNING: could not download {ref} ({str(e)[:160]}): continuing without it', flush=True)
GENS, seen = [], set()
for root in roots:
    for p in sorted(glob.glob(f'{root}/**/results/gen_per_task.jsonl', recursive=True)):
        g = Path(p).parent.parent
        if not (g / 'requests/requests.jsonl').exists():
            print('skip (no request log):', g)
            continue
        h = hashlib.sha1(Path(p).read_bytes()).hexdigest()
        if h in seen:
            print('skip (same run attached twice):', g)
            continue
        seen.add(h)
        GENS.append(g)
        rows = [json.loads(l) for l in open(p)]
        print(f'generation output {len(GENS)}: {g} | {len(rows)} runs, {sum(not r["resolved"] for r in rows)} failed', flush=True)
assert GENS, 'attach the generation outputs (each has results/gen_per_task.jsonl and requests/requests.jsonl)'
