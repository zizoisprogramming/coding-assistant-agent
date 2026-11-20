"""Offline check for a 'history first' gate on sb1h's edit (user 2026-11-20: 'working in both directions is good, try to start
with it rather than late, and yes try building on sb1h because of it solving broken edits').
Gate: the FIRST edit the model sends into a function is not applied; the step prints that function's history (sbF2's filter)
and asks for the edit again; any later edit into a function already shown is applied as in sb1h. CPU only, no git, no network:
  - timing / call position of each run's first heredoc edit: r118-r121 requests (sb1h-family arms: sb1h, sb1hpp, sbA, sbB, sbF,
    sbF2, sb7h fixer), with the run's outcome; a refused first edit costs one more reply + call, so runs whose first edit comes
    late in time or calls would be pushed over the 8-min / 28-call limits;
  - extra calls per run (distinct functions edited) and a useful commit at the gated first edit: the model's r118 + r119 edits,
    with the enclosing function and its history from data/analysis/hist_window_cache.json (window check), labels
    scripts/mine_bank/hist_useful_commits.json (hashes from the same clones).
Bars (set before running, docs/PLAN.md): median extra calls per run <= 2; runs whose first edit is at >= 440 s or call >= 26
<= 15% of runs with an edit; a useful commit at the gated first edit in >= 30% of runs with an edit (labelled tasks).
Run: python3 -I scripts/mine_bank/gate_check.py"""
import ast, collections, glob, json, re, statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARMS = {"sb1h", "sb1hpp", "sbA", "sbB", "sbF", "sbF2", "sb7h"}
HEREDOC = re.compile(r"cat > \.git/agent/old <<'OLD_TEXT'\n(.*?)OLD_TEXT\n.*?python3 - (\S+) <<'EOF'", re.S)
DIRS = sorted(glob.glob(str(ROOT / "data/results/2026-11-19_skill_r11[89]_p*")) + glob.glob(str(ROOT / "data/results/2026-11-19_skill_r120_p*"))
              + glob.glob(str(ROOT / "data/results/2026-11-20_skill_r121_p*")))
solved = {}
for d in DIRS:
    for l in open(f"{d}/results/gen_per_task.jsonl"):
        g = json.loads(l)
        solved[(d, g["instance_id"], g["arm"])] = (g["resolved"] in (True, "True"), g["end"])

runs = collections.defaultdict(list)
for d in DIRS:
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        try:
            r = json.loads(l)
        except Exception:
            continue
        arm = r["job"].split("#a")[1].split(".")[0]
        if arm not in ARMS:
            continue
        runs[(d, r["job"])].append(r)

rows = []
for (d, job), rs in runs.items():
    rs.sort(key=lambda r: float(r["t"]))
    t0 = float(rs[0]["t"])
    calls = 0
    edits = []
    secs = []
    for r in rs:
        if len(r["request"]["messages"]) == 1:
            continue
        try:
            cs = (ast.literal_eval(str(r["reply"])).get("message") or {}).get("tool_calls") or []
        except Exception:
            cs = []
        for c in cs:
            calls += 1
            try:
                a = json.loads(c["function"]["arguments"])
            except Exception:
                continue
            m = HEREDOC.search(a.get("command", "")) if c["function"]["name"] == "run_command" else None
            if m:
                edits.append(dict(t=float(r["t"]) + float(r.get("seconds") or 0) - t0, call=calls, path=m.group(2), old=m.group(1)))
                secs.append(float(r.get("seconds") or 0))
    iid, arm = job.split("#")[0], job.split("#a")[1].split(".")[0]
    s, end = solved.get((d, iid, arm), (False, "?"))
    rows.append(dict(d=d, iid=iid, arm=arm, edits=edits, secs=secs, solved=s, end=end, rnd=re.search(r"r1\d\d", d).group(0)))

print("#### 1. timing of the first edit (all sb1h-family runs, r118-r121)")
E = [x for x in rows if x["edits"]]
late = [x for x in E if x["edits"][0]["t"] >= 440 or x["edits"][0]["call"] >= 26]
print(f"  runs {len(rows)} | with a heredoc edit {len(E)} | first edit at s: median {st.median(x['edits'][0]['t'] for x in E):.0f}"
      f" p75 {sorted(x['edits'][0]['t'] for x in E)[int(len(E) * .75)]:.0f} p90 {sorted(x['edits'][0]['t'] for x in E)[int(len(E) * .9)]:.0f}"
      f" | at call: median {st.median(x['edits'][0]['call'] for x in E):.0f} p90 {sorted(x['edits'][0]['call'] for x in E)[int(len(E) * .9)]}")
print(f"  first edit at >= 440 s or call >= 26: {len(late)}/{len(E)} ({100 * len(late) / len(E):.0f}%), of them solved {sum(x['solved'] for x in late)}"
      f" | all edit runs solved {sum(x['solved'] for x in E)}/{len(E)}")
for lim in (380, 400, 420, 440):
    lt = [x for x in E if x["edits"][0]["t"] >= lim]
    print(f"    first edit at >= {lim} s: {len(lt):3} runs, solved {sum(x['solved'] for x in lt)}")
allsec = [s for x in E for s in x["secs"]]
print(f"  seconds of a reply that sends an edit: median {st.median(allsec):.0f} p75 {sorted(allsec)[int(len(allsec) * .75)]:.0f} (the cost of the resend,"
      f" plus the tool time, plus more context -> earlier compaction)")
print("  per round:", {k: f"{sum(1 for x in E if x['rnd'] == k)} edit runs, late {sum(1 for x in late if x['rnd'] == k)}" for k in ("r118", "r119", "r120", "r121")})

print("\n#### 2. extra calls and a useful commit at the gated first edit (r118 + r119 edits, the window check's function per edit)")
C = json.loads((ROOT / "data/analysis/hist_window_cache.json").read_text())["cache"]
LAB = json.loads((ROOT / "scripts/mine_bank/hist_useful_commits.json").read_text())
use = {t: set(v["useful"]) for t, v in LAB.items() if not t.startswith("_")}
extra, firstuse, n = [], 0, 0
per_task = collections.defaultdict(lambda: [0, 0])
for x in E:
    if x["rnd"] not in ("r118", "r119") or x["iid"] not in use:
        continue
    shown_fns, gated = set(), []
    for e in x["edits"]:
        old = e["old"] if e["old"].endswith("\n") else e["old"] + "\n"
        row = C.get(f"{x['iid']}|{e['path']}|{e['old']}") or C.get(f"{x['iid']}|{e['path']}|{old}")
        if not row or row.get("found") != 1:
            continue  # old text not once in HEAD: no gate (own new text, or found 0 / 2 as in sb1h)
        fn = (e["path"], tuple(row["F"]) if row.get("F") else tuple(row["L"]))
        if fn in shown_fns:
            continue
        shown_fns.add(fn)
        hist = row.get("F3") if row.get("F") else row.get("L3")
        gated.append([h[:7] for h in re.findall(r"^commit ([0-9a-f]{7,})", hist or "", re.M)])
    n += 1
    extra.append(len(gated))
    u = bool(gated) and bool(set(gated[0]) & use[x["iid"]])
    firstuse += u
    per_task[x["iid"]][0] += u
    per_task[x["iid"]][1] += 1
print(f"  runs with an edit on a labelled task {n} | extra calls per run (functions gated): median {st.median(extra) if extra else 0}"
      f" mean {st.mean(extra) if extra else 0:.2f} max {max(extra or [0])} | distribution {dict(sorted(collections.Counter(extra).items()))}")
print(f"  a useful commit at the gated first edit: {firstuse}/{n} ({100 * firstuse / max(n, 1):.0f}%)")
for t, (a, b) in sorted(per_task.items()):
    print(f"    {t[:36]:36} {a}/{b}")
print("\nbars: median extra calls <= 2 | late first edits <= 15% | useful at the gated first edit >= 30%")
