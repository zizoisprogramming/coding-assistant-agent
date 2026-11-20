"""Option 2 study: runs that never edit (user 2026-11-20: 'while it runs see option 2'). Read-only on r118-r124 requests of the
sb1h family (sb1h, sb1hpp, sbA, sbF, sbF2, sbG, sb1hl). For every run with no applied source edit:
  - how its 8 minutes were spent: model seconds in normal replies, in the longest reply, in compactions; calls by kind;
  - the longest reply: output tokens, how much was thinking, what it was doing (first / last words printed for hand reading);
  - when the model first said in its reasoning what it would change ('the fix is', 'I will change', 'I need to modify', ...)
    and how many seconds were left then;
  - whether it had read the file it later named as the place to change.
Compared with runs that edited (time of the first edit) to see what differs.
Run: python3 -I scripts/mine_bank/noedit_study.py"""
import ast, collections, glob, json, re, statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARMS = {"sb1h", "sb1hpp", "sbA", "sbF", "sbF2", "sbG", "sb1hl"}
DIRS = sorted(glob.glob(str(ROOT / "data/results/2026-11-19_skill_r1[12][890]_p*")) + glob.glob(str(ROOT / "data/results/2026-11-20_skill_r12[1-4]_p*")))
PLAN = re.compile(r"(the fix (is|should|would|will)|I will (change|modify|edit|update|fix)|I('ll| will) (now )?(make|apply) the (edit|change|fix)|"
                  r"I need to (change|modify|edit|update)|we (need|should) (to )?(change|modify)|so the fix|let me (fix|edit|modify|change))", re.I)
G = {}
for d in DIRS:
    for l in open(f"{d}/results/gen_per_task.jsonl"):
        g = json.loads(l)
        G[(d, g["instance_id"], g["arm"])] = g
runs = collections.defaultdict(list)
for d in DIRS:
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        try:
            r = json.loads(l)
        except Exception:
            continue
        arm = r["job"].split("#a")[1].split(".")[0]
        if arm in ARMS:
            runs[(d, r["job"].split("#")[0], arm)].append(r)


def parse(r):
    try:
        d = ast.literal_eval(str(r["reply"]))
    except Exception:
        return "", "", [], {}
    m = d.get("message") or {}
    return (m.get("reasoning_content") or ""), (m.get("content") or ""), (m.get("tool_calls") or []), (d.get("usage") or {})


rows = []
for key, rs in runs.items():
    rs.sort(key=lambda r: float(r["t"]))
    t0 = float(rs[0]["t"])
    edit_t = None
    plan_t = None
    plan_text = ""
    comp_s = normal_s = 0.0
    kinds = collections.Counter()
    longest = (0, None)
    for i, r in enumerate(rs):
        s = float(r.get("seconds") or 0)
        if len(r["request"]["messages"]) == 1:
            comp_s += s
            continue
        normal_s += s
        think, text, calls, usage = parse(r)
        if s > longest[0]:
            longest = (s, dict(think=think, text=text, out=usage.get("completion_tokens"), t=float(r["t"]) - t0, calls=[c["function"]["name"] + ":" + str(c["function"]["arguments"])[:80] for c in calls]))
        if plan_t is None and PLAN.search(think + " " + text):
            plan_t = float(r["t"]) + s - t0
            m = PLAN.search(think + " " + text)
            plan_text = (think + " " + text)[max(0, m.start() - 150):m.end() + 250].replace("\n", " ")
        for c in calls:
            a = str(c["function"]["arguments"])
            k = c["function"]["name"]
            if k == "run_command":
                k = "edit" if "OLD_TEXT" in a else "pytest" if "pytest" in a else "python check" if re.search(r"python3? (- <<|-c|reproduce|repro|\S+\.py)", a) or "cat > " in a and ".py" in a else "grep/find/ls/git" if re.search(r"(git |grep|find |ls |sed -n|cat |head|tail)", a) else "other"
            kinds[k] += 1
            if k == "edit" and edit_t is None:
                edit_t = float(r["t"]) + s - t0
    g = G.get(key, {})
    rows.append(dict(key=key, solved=g.get("resolved") in (True, "True"), patch=bool(g.get("patch_chars")), end=g.get("end"), edit_t=edit_t, plan_t=plan_t,
                     plan_text=plan_text, comp_s=comp_s, normal_s=normal_s, kinds=kinds, longest=longest))

NE = [r for r in rows if r["edit_t"] is None]
ED = [r for r in rows if r["edit_t"] is not None]
print(f"runs {len(rows)} | never sent an edit {len(NE)} | edited {len(ED)}")
for name, grp in (("never edited", NE), ("edited", ED)):
    print(f"\n#### {name} ({len(grp)} runs)")
    print(f"  model seconds: normal replies median {st.median(r['normal_s'] for r in grp):.0f}, compactions median {st.median(r['comp_s'] for r in grp):.0f}"
          f" | longest reply median {st.median(r['longest'][0] for r in grp):.0f} s (>= 120 s in {sum(r['longest'][0] >= 120 for r in grp)}), output tokens median"
          f" {st.median([r['longest'][1]['out'] or 0 for r in grp if r['longest'][1]] or [0]):.0f}")
    k = sum((r["kinds"] for r in grp), collections.Counter())
    print("  calls per run by kind: " + ", ".join(f"{a} {v / len(grp):.1f}" for a, v in k.most_common()))
    pl = [r for r in grp if r["plan_t"] is not None]
    print(f"  said what it would change: {len(pl)}/{len(grp)} runs, at median {st.median([r['plan_t'] for r in pl] or [0]):.0f} s"
          + (f"; edit came median {st.median([r['edit_t'] - r['plan_t'] for r in pl if r['edit_t']] or [0]):.0f} s after that" if name == "edited" else
             f"; seconds left then median {st.median([480 - r['plan_t'] for r in pl] or [0]):.0f}"))
print("\n#### never-edited runs, one by one (hand reading)")
for r in sorted(NE, key=lambda r: -r["longest"][0]):
    d, iid, arm = r["key"]
    L = r["longest"][1] or {}
    print(f"\n  ## {Path(d).name[-8:]} {iid[:28]} {arm} | end {r['end']} | calls {dict(r['kinds'])} | compactions {r['comp_s']:.0f} s"
          f" | said what to change at {('%.0f s' % r['plan_t']) if r['plan_t'] else 'never'}")
    if r["plan_text"]:
        print("     PLAN WORDS: ..." + r["plan_text"][:400])
    print(f"     LONGEST REPLY {r['longest'][0]:.0f} s at {L.get('t', 0):.0f} s, {L.get('out')} tokens, calls {L.get('calls')}")
    th = (L.get("think") or "").replace("\n", " ")
    print("     its thinking starts: " + th[:300])
    print("     ... and ends: " + th[-300:])
