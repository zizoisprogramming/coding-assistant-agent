"""Gated-shell arms (combo1en, combo1en2): first refusal -> next call, and seconds from the first refusal to the first
source edit that worked. Usage: python3 -I scripts/mine_bank/refusal_next.py RESULTS_FOLDER [RESULTS_FOLDER ...]"""
import collections, json, re, statistics as st, sys
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")
for D in sys.argv[1:]:
    J = collections.defaultdict(list)
    for l in open(D + "/requests/requests.jsonl"):
        r = json.loads(l)
        if isinstance(r.get("reply"), dict) and r.get("job"): J[r["job"]].append(r)
    out = collections.defaultdict(list)
    for job, q in J.items():
        arm = job.partition("#a")[2].split(".")[0]
        q.sort(key=lambda r: r["t"]); t0 = q[0]["t"]; R = {}
        for r in q:
            for m in r["request"]["messages"]:
                if m.get("role") == "tool": R.setdefault(m.get("tool_call_id"), str(m.get("content")))
        calls = []
        for r in q:
            if not r["request"].get("tools"): continue
            for c in r["reply"]["message"].get("tool_calls") or []:
                try: a = json.loads(c["function"]["arguments"])
                except Exception: a = {}
                calls.append((r["t"] + r["seconds"] - t0, c["function"]["name"], a, R.get(c.get("id"), "")))
        ref = next((i for i, c in enumerate(calls) if "REFUSED" in c[3]), None)
        if ref is None: continue
        nxt = calls[ref + 1][1] if ref + 1 < len(calls) else "END"
        nref = sum("REFUSED" in c[3] for c in calls)
        ed = next((c[0] for c in calls[ref + 1:] if c[1] in ("edit_file", "write_file") and "error" not in c[3].lower()[:300]
                   and not TEST.search(str(c[2].get("filepath", ""))) and not str(c[2].get("filepath", "")).startswith("/tmp")), None)
        out[arm].append((job.partition("#a")[0], calls[ref][0], nxt, nref, None if ed is None else ed - calls[ref][0]))
    print(D)
    for arm, rows in out.items():
        print(f"  {arm}: refusal runs {len(rows)} | next call after first refusal {dict(collections.Counter(r[2] for r in rows))}"
              f" | edit next {sum(r[2] == 'edit_file' for r in rows)}/{len(rows)} | refusals {sum(r[3] for r in rows)}")
        lat = [r[4] for r in rows if r[4] is not None]
        print(f"    refusal -> first working edit: {len(lat)}/{len(rows)} runs, median {st.median(lat) if lat else '-'} s")
        for r in sorted(rows):
            print(f"    {r[0]:16s} refused at {r[1]:5.0f}s next {r[2]:16s} refusals {r[3]} edit after {'-' if r[4] is None else round(r[4])}")
