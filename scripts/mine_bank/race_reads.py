"""race2 (r75) mechanism reads, per task: scout calls / time / notes, each engineer's calls, first edit, submit time,
who won, engineer B edits outside its worktree, B's finish command, largest prompt per agent (compaction fires at
14,336), errors. Agents are told apart by the first line of their system prompt.
Usage: python3 -I scripts/mine_bank/race_reads.py RESULTS_FOLDER [ARM]   (ARM defaults to race2)"""
import collections, json, re, statistics as st, sys

D = sys.argv[1]; ARM = sys.argv[2] if len(sys.argv) > 2 else "race2"
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")
G = {(r["instance_id"], r["attempt"]): r for r in map(json.loads, open(D + "/results/gen_per_task.jsonl"))}
J = collections.defaultdict(list)
for l in open(D + "/requests/requests.jsonl"):
    r = json.loads(l)
    if isinstance(r.get("reply"), dict) and r.get("job") and f"#a{ARM}." in r["job"]:
        J[r["job"]].append(r)


def who(r):
    s = str(r["request"]["messages"][0].get("content") or "")[:200]
    return "scout" if "You are the scout" in s else "A" if "You are engineer A" in s else "B" if "You are engineer B" in s else "other"


rows = []
for job, q in sorted(J.items()):
    iid, _, att = job.partition("#a")
    q.sort(key=lambda r: r["t"]); t0 = q[0]["t"]; R = {}
    for r in q:
        for m in r["request"]["messages"]:
            if m.get("role") == "tool": R.setdefault(m.get("tool_call_id"), str(m.get("content")))
    A = collections.defaultdict(lambda: dict(calls=0, first=None, last=None, edit=None, submit=None, maxp=0, outside=0, finish=0, apply_fail=0, notes=""))
    for r in q:
        if not r["request"].get("tools"): continue  # summarizer calls
        w = who(r); a = A[w]; end = r["t"] + r["seconds"] - t0
        a["first"] = a["first"] if a["first"] is not None else r["t"] - t0; a["last"] = end
        a["maxp"] = max(a["maxp"], (r["reply"].get("usage") or {}).get("prompt_tokens") or 0)
        m = r["reply"]["message"]
        if w == "scout" and not m.get("tool_calls") and m.get("content"): a["notes"] = str(m["content"])
        for c in m.get("tool_calls") or []:
            a["calls"] += 1; n = c["function"]["name"]
            try: x = json.loads(c["function"]["arguments"])
            except Exception: x = {}
            p = str(x.get("filepath") or ""); cmd = str(x.get("command") or ""); res = R.get(c.get("id"), "")
            if n in ("edit_file", "write_file") and p and not TEST.search(p) and "error_type" not in res[:200] and "mandatory" not in res:
                a["edit"] = a["edit"] if a["edit"] is not None else end
                if w == "B" and not p.lstrip("/").replace("workspace/", "", 1).startswith(".git/wt_b/"): a["outside"] += 1
                if w == "A" and ".git/wt_b" in p: a["outside"] += 1
            if n == "run_command" and "b_fix.patch" in cmd:
                a["finish"] += 1; a["apply_fail"] += ("error" in res.lower() or "exit_code" in res) and "patch failed" in res.lower() or "does not apply" in res
            if n == "submit_patch" and a["submit"] is None: a["submit"] = end
    g = G.get((iid, att), {})
    subs = [(A[w]["submit"], w) for w in ("A", "B") if A[w]["submit"] is not None]
    rows.append(dict(task=iid, solved=bool(g.get("resolved")), patch=g.get("patch_chars"), agent=g.get("agent_s"), end=g.get("end"), err=(g.get("error") or "")[:80],
                     winner=min(subs)[1] if subs else "-", A=dict(A)))
print(f"{ARM}: {len(rows)} runs")
for x in rows:
    s, a, b = x["A"].get("scout", {}), x["A"].get("A", {}), x["A"].get("B", {})
    f = lambda v: "-" if v is None else f"{v:.0f}"
    print(f"{x['task']:15s} {'Y' if x['solved'] else ('e' if x['patch'] else '.')} agent {f(x['agent'])} s end {x['end']} winner {x['winner']} {x['err']}")
    print(f"   scout: {s.get('calls', 0)} calls, done at {f(s.get('last'))} s, max prompt {s.get('maxp', 0)}, notes {len(s.get('notes', ''))} chars, "
          f"fields {[k for k in ('WHERE', 'CAUSE', 'CHANGE', 'ALSO', 'CHECK', 'TEST') if k + ':' in s.get('notes', '')]}")
    for w, e in (("A", a), ("B", b)):
        print(f"   {w}: {e.get('calls', 0)} calls, start {f(e.get('first'))} s, first edit {f(e.get('edit'))} s, submit {f(e.get('submit'))} s, max prompt {e.get('maxp', 0)}, "
              f"edits outside its tree {e.get('outside', 0)}" + (f", finish cmd {e.get('finish', 0)} (apply failed {e.get('apply_fail', 0)})" if w == "B" else ""))
sc = [x["A"]["scout"]["last"] for x in rows if "scout" in x["A"]]
mp = [max(x["A"].get(w, {}).get("maxp", 0) for w in ("A", "B")) for x in rows]
print(f"\nsummary: solved {sum(x['solved'] for x in rows)}/{len(rows)} | no patch {sum(not x['patch'] for x in rows)} | winners {dict(collections.Counter(x['winner'] for x in rows))} | "
      f"scout done median {st.median(sc) if sc else '-'} s | engineer max prompt {max(mp) if mp else '-'} (compaction at 14,336) | errors {sum(bool(x['err']) for x in rows)} | "
      f"B edits outside wt_b {sum(x['A'].get('B', {}).get('outside', 0) for x in rows)} | A edits in wt_b {sum(x['A'].get('A', {}).get('outside', 0) for x in rows)}")
