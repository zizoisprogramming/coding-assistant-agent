"""Clock numbers on the same 24 tasks (e24), next move after each clock message, and reasoning that refers to time. Prints no task text."""
import collections, glob, json, re, statistics as st
TAB = list(map(json.loads, open("data/analysis/run_table.jsonl")))
A8 = {r["iid"] for r in TAB if r["arm"] == "sq1c2a8"}
ARMS = [("pub024", "no clock"), ("sq1", "no clock, split"), ("sq1c2", "warn 180, refuse 270"), ("sq1c2a8", "warn 180, refuse 270"), ("sq1c2a8rc", "warn 180, refuse 270"), ("sq1c2t7", "warn 160, refuse 240"), ("sq1c2f6", "warn 180, refuse 270"), ("sq1c2f6ra", "warn 180, refuse 270"), ("sq1c2a6rc", "warn 180, refuse 270")]
bins = (0, 90, 135, 160, 180, 240, 270, 300, 481)
print("first edit on the e24 tasks: share of runs by window")
print(f"{'':12}{'':24}" + "".join(f"{a}-{b}".rjust(9) for a, b in zip(bins, bins[1:])) + "    never  n")
for a, lab in ARMS:
    x = [r for r in TAB if r["arm"] == a and r["iid"] in A8]
    if not x: continue
    c = [sum(p <= (r["first_edit"] or 1e9) < q for r in x) / len(x) for p, q in zip(bins, bins[1:])]
    print(f"{a:12}{lab:24}" + "".join(f"{v:9.0%}" for v in c) + f"{sum(r['first_edit'] is None for r in x)/len(x):9.0%}  {len(x)}")
GR = {"sq1c2": "8 min", "sq1c2a8": "8 min", "sq1c2a8ra": "8 min", "sq1c2a8rc": "8 min", "sq1c2t7": "7 min", "sq1c2a6": "6 min", "sq1c2a6rc": "6 min", "sq1c2a6c": "6 min", "sq1c2a6i": "6 min", "sq1c2f6ra": "6 min", "sq1c2f6rc": "6 min"}
ev = collections.defaultdict(collections.Counter); turns = collections.Counter(); ment = collections.Counter(); samples = []; reasoned = collections.Counter(); wordy = collections.Counter()
PAT = re.compile(r"\[clock\]|\bclock\b|\b\d{2,3} ?(s|sec|seconds)\b|\btime (is|left|remaining|limit)\b|running out of time|out of time|\b\d+ of (360|420|480)\b|\bdeadline\b", re.I)
for f in sorted(glob.glob("data/results/*/requests/requests.jsonl")):
    J = collections.defaultdict(list)
    for line in open(f):
        r = json.loads(line)
        if isinstance(r.get("reply"), dict) and r.get("job"): J[r["job"]].append(r)
    for job, q in J.items():
        arm = job.split("#a")[-1].split(".")[0]; g = GR.get(arm)
        if not g: continue
        q.sort(key=lambda r: r["t"]); edited = False; tr = []
        for r in q:
            if not r["request"].get("tools"): continue
            ms = r["reply"]["message"]; think = str(ms.get("reasoning_content") or ms.get("reasoning") or "") + " " + str(ms.get("content") or "")
            last = r["request"]["messages"][-1]; lc = str(last.get("content")) if last.get("role") == "tool" else ""
            calls = [c["function"]["name"] for c in ms.get("tool_calls") or []]
            is_edit = "edit_file" in calls or any(c["function"]["name"] == "run_skill_script" and "sed -i" in str(c["function"]["arguments"]) for c in ms.get("tool_calls") or [])
            turns[g] += 1; reasoned[g] += bool(think.strip())
            if PAT.search(think):
                ment[g] += 1
                if len(samples) < 6:
                    m = PAT.search(think); samples.append(think[max(0, m.start() - 70):m.end() + 70].replace("\n", " "))
            e = None
            if "REFUSED" in lc and "no source file is edited" in lc: e = "refusal"
            elif "NO SOURCE EDIT YET" in lc: e = "warning"
            elif "no source edit yet" in lc: e = "plain"
            if e and not edited:
                ev[g][e] += 1; ev[g][e + "_edit"] += is_edit
            if is_edit: edited = True
print("\nno edit yet: chance the very next model turn is an edit, by what the clock line said")
for g in ev:
    c = ev[g]; p = lambda k: f"{c[k+'_edit']/c[k]:.0%} of {c[k]}" if c[k] else "-"
    print(f"  {g:6} plain line {p('plain'):14} warning {p('warning'):14} refusal {p('refusal'):14} | turns with reasoning {reasoned[g]/turns[g]:.0%} | reasoning refers to time or clock {ment[g]/turns[g]:.1%}")
print("samples (reasoning near a time reference):")
for s in samples: print("  -", s[:200])
print("\nsame tasks (e24): no-edit share and first-edit seconds for runs that edited")
for a, _ in ARMS:
    x = [r for r in TAB if r["arm"] == a and r["iid"] in A8]
    if x:
        e = [r["first_edit"] for r in x if r["first_edit"] is not None]
        print(f"  {a:12} n={len(x):3} never {sum(not r['n_edits'] for r in x)/len(x):.0%} median first edit {st.median(e):.0f} s, solved {sum(r['resolved'] for r in x)/len(x):.0%}")
