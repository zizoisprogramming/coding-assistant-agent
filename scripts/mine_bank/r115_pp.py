"""r115: sb1 vs sb1pp05 / sb1pp15 (presence_penalty 0.5 / 1.5) on rich_3521, geopandas-3240, fastapi_14419, rich_4079.
Checks the bars set before the run (docs/PLAN.md RUN BUILT r115). Run: python3 -I scripts/mine_bank/r115_pp.py
(repo root; logs only). Per arm, from requests.jsonl (model replies) and digest.jsonl (run results):
tokens per reply, share of model time in replies >= 60 s, 'Wait' / 'Actually' per 1k thinking chars, failed edit
results per run (tool results that say old_string not found / occurs ... times / flexibly matches / mandatory input
parameters), CJK / Cyrillic chars in thinking per run, ends, no patch, agent time.
Luck vs effect: the same numbers for every earlier sb1 run on these 4 tasks (all 2026-11-1* folders), and a matched
resample (one bank sb1 run per task an arm ran, 20,000 times) gives the range sb1 itself shows by chance."""
import ast, collections, glob, json, random, re, statistics as st

NEW = sorted(glob.glob("data/results/2026-11-18_skill_pp4_p*"))
TASKS = ("rich_3521", "geopandas__geopandas-3240", "fastapi_14419", "rich_4079")
WAIT = re.compile(r"\b(Wait|Actually)\b")
CJK = re.compile(r"[一-鿿぀-ヿ가-힯Ѐ-ӿ]")
FAIL = re.compile(r"old_string not found|occurs \d+ times|flexibly match|mandatory input parameters are not present")


def reply_fields(rep):
    try:
        d = ast.literal_eval(rep)
        msg = d.get("message") or {}
        think = msg.get("reasoning_content") or ""
        tok = (d.get("usage") or {}).get("completion_tokens")
    except Exception:
        m = re.search(r"'reasoning_content': '(.*?)', '", rep, re.S)
        think = m.group(1) if m else ""
        tok = None
    if tok is None:
        m = re.search(r"'completion_tokens': (\d+)", rep)
        tok = int(m.group(1)) if m else None
    return think, tok


def load(d, arms):
    runs = {}
    for f in ("digest.jsonl", "gen_per_task.jsonl"):
        p = f"{d}/results/{f}"
        if glob.glob(p):
            for l in open(p):
                g = json.loads(l)
                if g.get("arm") in arms and g["instance_id"] in TASKS:
                    runs.setdefault(g["job"] if "job" in g else f"{g['instance_id']}#a{g['attempt']}", {}).update(g)
            break
    reqs = collections.defaultdict(list)
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        try:
            r = json.loads(l)
        except Exception:
            continue
        if r.get("job") not in runs:
            continue
        think, tok = reply_fields(str(r.get("reply")))
        last = (r.get("request") or {}).get("messages", [{}])[-1] if isinstance(r.get("request"), dict) else {}
        tool_text = str(last.get("content")) if last.get("role") == "tool" else ""
        reqs[r["job"]].append(dict(t=float(r["t"]), s=float(r.get("seconds") or 0), tok=tok, think=think, fail=bool(FAIL.search(tool_text))))
    out = {}
    for job, g in runs.items():
        R = sorted(reqs.get(job, []), key=lambda x: x["t"])
        if not R:
            continue
        S = sum(x["s"] for x in R)
        th = "".join(x["think"] for x in R)
        toks = [x["tok"] for x in R if x["tok"] is not None]
        out[f"{d}:{job}"] = dict(task=g["instance_id"], arm=g["arm"], solved=g["resolved"] in (True, "True"), end=g["end"],
                                 nop=not g.get("patch_chars"), agent=g.get("model_s", 0) + g.get("tool_s", 0) if "model_s" in g else g.get("agent_s", 0),
                                 replies=len(R), tok=st.mean(toks) if toks else 0, long=100 * sum(x["s"] for x in R if x["s"] >= 60) / S if S else 0,
                                 wait=1000 * len(WAIT.findall(th)) / max(1, len(th)), fails=sum(x["fail"] for x in R), cjk=len(CJK.findall(th)),
                                 tok_sum=sum(toks), n_tok=len(toks), long_s=sum(x["s"] for x in R if x["s"] >= 60), S=S, w=len(WAIT.findall(th)), chars=len(th))
    return out


def agg(rs):
    n = len(rs)
    return dict(n=n, solved=sum(r["solved"] for r in rs), nop=sum(r["nop"] for r in rs), time=sum(r["end"] == "time" for r in rs),
                tok=sum(r["tok_sum"] for r in rs) / max(1, sum(r["n_tok"] for r in rs)), long=100 * sum(r["long_s"] for r in rs) / max(1, sum(r["S"] for r in rs)),
                wait=1000 * sum(r["w"] for r in rs) / max(1, sum(r["chars"] for r in rs)), fails=sum(r["fails"] for r in rs) / n,
                cjk=sum(r["cjk"] for r in rs) / n, agent=st.mean(r["agent"] for r in rs))


def line(name, a):
    return (f"  {name:16} runs {a['n']:3} | solved {a['solved']} | no patch {a['nop']} | time ends {a['time']} | tokens/reply {a['tok']:5.0f}"
            f" | long-reply share {a['long']:3.0f}% | Wait/1k {a['wait']:4.2f} | failed edits/run {a['fails']:4.1f} | CJK/run {a['cjk']:5.1f} | agent s {a['agent']:4.0f}")


new = {}
for d in NEW:
    new.update(load(d, ("sb1", "sb1pp05", "sb1pp15")))
print("#### r115 (same run)")
A = {arm: agg([r for r in new.values() if r["arm"] == arm]) for arm in ("sb1", "sb1pp05", "sb1pp15")}
for arm, a in A.items():
    print(line(arm, a))
print("\n  per run: task | arm | solved end nop | tokens/reply long% Wait/1k fails CJK agent s")
for k, r in sorted(new.items(), key=lambda kv: (kv[1]["task"], kv[1]["arm"])):
    print(f"    {r['task'][:26]:26} {r['arm']:8} {'S' if r['solved'] else '-'} {r['end']:5} {'nop' if r['nop'] else 'ptc'} | {r['tok']:5.0f} {r['long']:3.0f}% {r['wait']:4.2f} {r['fails']:2} {r['cjk']:3} {r['agent']:4.0f}")

bank = {}
for d in sorted(glob.glob("data/results/2026-11-1*")):
    if d in NEW or not glob.glob(f"{d}/requests/requests.jsonl"):
        continue
    try:
        bank.update(load(d, ("sb1",)))
    except Exception as e:
        print("skip", d, e)
B = collections.defaultdict(list)
for r in bank.values():
    B[r["task"]].append(r)
print(f"\n#### bank sb1 on these 4 tasks: " + ", ".join(f"{t[:14]} {len(B[t])}" for t in TASKS))
print(line("bank sb1", agg([r for v in B.values() for r in v])))

random.seed(0)
print("\n#### matched resample of bank sb1 (one run per task the arm ran): 5th-95th percentile, and where each arm sits")
for arm in ("sb1", "sb1pp05", "sb1pp15"):
    rs = [r for r in new.values() if r["arm"] == arm]
    ts = [r["task"] for r in rs if B[r["task"]]]
    sims = [agg([random.choice(B[t]) for t in ts]) for _ in range(20000)]
    a = agg([r for r in rs if B[r["task"]]])
    cells = []
    for m in ("tok", "long", "wait", "fails", "cjk", "agent", "time", "nop", "solved"):
        v = sorted(s[m] for s in sims)
        lo, hi = v[len(v) // 20], v[-len(v) // 20]
        pl = sum(x <= a[m] for x in v) / len(v)
        cells.append(f"{m} {a[m]:.2f} [{lo:.2f}, {hi:.2f}] p<= {pl:.2f}")
    print(f"  {arm:8} " + " | ".join(cells))
