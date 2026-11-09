"""r70 checklist-stage reads for kf2c. Usage: python3 -I scripts/mine_bank/checklist_reads.py data/results/FOLDER
Prints counts only, never task text: stage seconds and reruns, checklist kept in the fixer's system prompt, lines filled,
and how many of the issue's quoted or backticked literals the checklist copied."""
import collections, json, re, statistics as st, sys
D = sys.argv[1]; J = collections.defaultdict(list)
for l in open(D + "/requests/requests.jsonl"):
    r = json.loads(l)
    if isinstance(r.get("reply"), dict) and "kf2c" in str(r.get("job")): J[r["job"]].append(r)
STAGE = "Your only job is to copy a checklist"
def sysm(r):
    m = r["request"]["messages"]; return str(m[0].get("content")) if m and m[0].get("role") == "system" else ""
rows = []
for job, q in sorted(J.items()):
    q.sort(key=lambda r: r["t"]); t0 = q[0]["t"]
    stage = [r for r in q if STAGE in sysm(r)]; fix = [r for r in q if STAGE not in sysm(r) and r["request"].get("tools")]
    issue = sysm(stage[0]).split("# THE ISSUE (verbatim)")[-1] if stage else ""
    lits = {x for x in re.findall(r"`([^`\n]{2,80})`|\"([^\"\n]{2,80})\"", issue) for x in x if x}
    cl = sysm(fix[0]).split("# CHECKLIST (copied")[-1] if fix else ""
    filled = sum(1 for k in ("NAMES:", "MESSAGES:", "INPUTS:", "EXPECTED:", "EDGE CASES:") if re.search(k + r"\s*(?!none\b)\S", cl, re.I))
    kept = sum("# CHECKLIST (copied" in sysm(r) and "NAMES:" in sysm(r).split("# CHECKLIST (copied")[-1] for r in fix)
    rows.append(dict(job=job, stage_s=round(fix[0]["t"] - t0) if fix else None, stage_reqs=len(stage),
                     stage_out=sum((r["reply"].get("usage") or {}).get("completion_tokens") or 0 for r in stage),
                     kept=f"{kept}/{len(fix)}", filled=filled, lits=f"{sum(l in cl for l in lits)}/{len(lits)}"))
for r in rows: print(r)
if rows:
    print(f"stage seconds median {st.median(r['stage_s'] for r in rows if r['stage_s'] is not None)}, "
          f"runs with the stage rerun {sum(r['stage_reqs'] > 1 for r in rows)}/{len(rows)}")
