"""Do the clock's numbers change behaviour? Prints no task text."""
import collections, glob, json, re, statistics as st
TAB = {(r["folder"], r["iid"], str(r["attempt"])): r for r in map(json.loads, open("data/analysis/run_table.jsonl"))}
GR = {"pub024": "pub (no clock)", "sq1": "sq1 (no clock)", "sq1c2": "sq1c2", "sq1c2t7": "t7", "sq1c2a8": "a8", "sq1c2a8ra": "a8", "sq1c2a8rc": "a8", "sq1c2a6": "a6", "sq1c2a6rc": "a6", "sq1c2a6c": "a6", "sq1c2a6i": "a6", "sq1c2t6": "t6", "sq1c2f6ra": "f6", "sq1c2f6rc": "f6", "srep7": "srep7", "srep8": "srep8"}
bins = (0, 60, 120, 180, 240, 270, 300, 360, 420, 481)
print("== when the first edit lands: share of runs in each window (none = never)")
print(f"{'':18}" + "".join(f"{a}-{b}".rjust(9) for a, b in zip(bins, bins[1:])) + "     none")
for g in dict.fromkeys(GR.values()):
    x = [r for r in TAB.values() if GR.get(r["arm"]) == g]
    if not x: continue
    c = [sum(a <= (r["first_edit"] or 1e9) < b for r in x) / len(x) for a, b in zip(bins, bins[1:])]
    print(f"{g:18}" + "".join(f"{v:9.0%}" for v in c) + f"{sum(r['first_edit'] is None for r in x)/len(x):9.0%}  n={len(x)}")
print("\n== events in the clock's output and the next move; reasoning that mentions time")
cnt = collections.defaultdict(collections.Counter); mention = collections.Counter(); turns = collections.Counter(); after = collections.defaultdict(list)
for f in sorted(glob.glob("data/results/*/requests/requests.jsonl")):
    d = f.split("/")[2]
    J = collections.defaultdict(list)
    for line in open(f):
        r = json.loads(line)
        if isinstance(r.get("reply"), dict) and r.get("job"): J[r["job"]].append(r)
    for job, q in J.items():
        arm = job.split("#a")[-1].split(".")[0]
        if GR.get(arm) is None: continue
        g = GR[arm]; q.sort(key=lambda r: r["t"])
        edited = False
        for r in q:
            ms = r["reply"]["message"]; think = str(ms.get("reasoning_content") or ms.get("reasoning") or "") + str(ms.get("content") or "")
            last = r["request"]["messages"][-1]
            lc = str(last.get("content")) if last.get("role") == "tool" else ""
            calls = [c["function"]["name"] for c in ms.get("tool_calls") or []]
            is_edit = "edit_file" in calls
            turns[g] += 1
            if re.search(r"\b\d+ ?s\b.{0,20}(of|used|left)|\bclock\b|running out of time|time (is|left|remaining)|out of time|\bseconds\b", think, re.I): mention[g] += 1
            ev = None
            if "NO SOURCE EDIT YET" in lc: ev = "warning line"
            elif "REFUSED" in lc and "no source file is edited" in lc: ev = "refusal: no edit"
            elif "REFUSED: FINISH NOW" in lc: ev = "refusal: finish"
            elif "no source edit yet" in lc and not edited: ev = "plain clock line, no edit yet"
            if ev and not edited: cnt[g][ev] += 1; cnt[g][ev + " -> edit next"] += is_edit
            if is_edit: edited = True
print(f"{'':18}{'reasoning mentions time':>26}{'plain line -> edit':>22}{'warning -> edit':>20}{'refusal -> edit':>20}")
for g in dict.fromkeys(GR.values()):
    if not turns[g]: continue
    c = cnt[g]; p = lambda k: f"{c[k+' -> edit next']/c[k]:.0%} of {c[k]}" if c[k] else "-"
    print(f"{g:18}{mention[g]/turns[g]:26.0%}{p('plain clock line, no edit yet'):>22}{p('warning line'):>20}{p('refusal: no edit'):>20}")
