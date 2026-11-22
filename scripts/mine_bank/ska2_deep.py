"""sk_a2 deep dive (user 2026-11-22: 'why is it our top LB and what does it do, deep investigation').
Builds one row per logged 31B run over every data/results/*/ folder (gen_per_task.jsonl + requests/requests.jsonl) and
writes data/analysis/ska2_deep_runs.jsonl. Then compares sk_a2 with other agents on the SAME tasks (task-matched rates).
Run: python3 -I scripts/mine_bank/ska2_deep.py [--rebuild]"""
import ast, collections, glob, json, re, statistics as st, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/analysis/ska2_deep_runs.jsonl"
SRC_EDIT = re.compile(r"(repro|reproduce|check|debug|scratch|\.git/agent|/tmp/)")


def parse_reply(x):
    if isinstance(x, dict):
        return x
    if x is None:
        return {}
    try:
        return ast.literal_eval(str(x))
    except Exception:  # noqa: BLE001
        try:
            return json.loads(str(x))
        except Exception:  # noqa: BLE001
            return {}


def kind(n, a):
    c = a.get("command", "") if isinstance(a, dict) else ""
    if n == "run_skill_script":
        return "install"
    if n in ("edit_file", "write_file"):
        fp = str(a.get("filepath", "") or a.get("path", "") or a.get("file_path", ""))
        return "src_edit" if fp.endswith(".py") and not SRC_EDIT.search(fp) and "test" not in fp else "scratch_write"
    if n == "read_file":
        return "read_file"
    if n in ("submit_patch", "get_status"):
        return n
    if "OLD_TEXT" in c or re.search(r"\.replace\(|sed -i|git apply", c) and "a.py" not in c and "check" not in c:
        return "src_edit"
    if "a.py show" in c:
        return "show"
    if "a.py find" in c or re.search(r"(^|\s)(grep|git grep|rg)\b", c):
        return "search"
    if "a.py outline" in c:
        return "outline"
    if re.search(r"(^|\s)(cat|sed -n|head|tail|nl)\b", c):
        return "raw_read"
    if "pytest" in c or "check" in c or "repro" in c or "python3 -" in c or "python -c" in c or "python3 -c" in c:
        return "run_code"
    return "other"


def build():
    rows = []
    for d in sorted(glob.glob(str(ROOT / "data/results/*/"))):
        gp, rp = Path(d) / "results/gen_per_task.jsonl", Path(d) / "requests/requests.jsonl"
        if not gp.exists() or not rp.exists():
            continue
        G = {}
        for l in open(gp, errors="replace"):
            try:
                g = json.loads(l)
            except Exception:  # noqa: BLE001
                continue
            G[g.get("instance_id", "") + "#a" + str(g.get("attempt", ""))] = g
        by = collections.defaultdict(list)
        for l in open(rp, errors="replace"):
            try:
                r = json.loads(l)
            except Exception:  # noqa: BLE001
                continue
            by[r.get("job", "")].append(r)
        for job, rs in by.items():
            g = G.get(job)
            if not g:
                continue
            rs.sort(key=lambda r: float(r.get("t", 0)))
            kw = (rs[0].get("request") or {}).get("kwargs") or {}
            model = str((rs[0].get("request") or {}).get("model", ""))
            if "31b" not in model.lower():
                continue
            budget = ((kw.get("extra_body") or {}).get("thinking_token_budget")) or 0
            outs, secs, calls, ptok, comp, nudges, sumcalls = [], [], [], [], 0, 0, 0
            for r in rs:
                msgs = (r.get("request") or {}).get("messages") or []
                rep = parse_reply(r.get("reply")) or {}
                u = rep.get("usage") or {}
                if len(msgs) <= 1:
                    sumcalls += 1
                    continue
                o = u.get("completion_tokens") or 0
                p = u.get("prompt_tokens") or 0
                if ptok and p < 0.7 * ptok[-1]:
                    comp += 1
                ptok.append(p)
                outs.append(o)
                secs.append(float(r.get("seconds") or 0))
                m = rep.get("message") or {}
                tc = m.get("tool_calls") or []
                if not tc:
                    nudges += 1
                for c in tc:
                    fn = c.get("function") or {}
                    try:
                        a = json.loads(fn.get("arguments") or "{}")
                    except Exception:  # noqa: BLE001
                        a = {}
                    calls.append(kind(fn.get("name", ""), a if isinstance(a, dict) else {}))
            if not outs:
                continue
            cap = 0.88 * budget if budget else 10 ** 9
            first_edit = next((i for i, k in enumerate(calls) if k == "src_edit"), None)
            rows.append(dict(folder=Path(d).name, arm=g.get("arm") or job.split("#a")[1].split(".")[0], task=g.get("instance_id"),
                             split=g.get("split") or g.get("level"), solved=g.get("resolved") in (True, "True", 1),
                             end=g.get("end"), agent_s=float(g.get("agent_s") or 0), patch=int(g.get("patch_chars") or 0),
                             temp=kw.get("temperature"), budget=budget, max_out=kw.get("max_completion_tokens"),
                             n_tools=len((rs[0].get("request") or {}).get("tools") or []),
                             replies=len(outs), out_mean=st.mean(outs), s_reply=st.mean(secs), capped=sum(o >= cap for o in outs),
                             long3500=sum(o >= 3500 for o in outs), out_max=max(outs), comp=comp, nudges=nudges, sumcalls=sumcalls,
                             calls=calls, n_calls=len(calls), first_edit=first_edit, edited=first_edit is not None))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return rows


rows = build() if "--rebuild" in sys.argv or not OUT.exists() else [json.loads(l) for l in open(OUT)]
A = collections.defaultdict(list)
for r in rows:
    A[r["arm"]].append(r)
print(f"{len(rows)} runs, {len(A)} arms")


def summ(rs):
    n = len(rs)
    fe = [r["first_edit"] for r in rs if r["first_edit"] is not None]
    return dict(n=n, solve=sum(r["solved"] for r in rs) / n, nopatch=sum(r["patch"] == 0 for r in rs) / n,
                edited=sum(r["edited"] for r in rs) / n, timeend=sum(r["end"] == "time" for r in rs) / n,
                agent_s=st.mean(r["agent_s"] for r in rs), s_reply=st.mean(r["s_reply"] for r in rs),
                out=st.mean(r["out_mean"] for r in rs), capped=st.mean(r["capped"] for r in rs),
                long=sum(r["long3500"] for r in rs) / max(1, sum(r["replies"] for r in rs)),
                comp=st.mean(r["comp"] for r in rs), nudges=st.mean(r["nudges"] for r in rs), calls=st.mean(r["n_calls"] for r in rs),
                fe_med=st.median(fe) if fe else None)


def matched(arm, other):
    """task-matched: average over tasks both ran of (per-task rate arm - per-task rate other)."""
    ta = collections.defaultdict(list)
    to = collections.defaultdict(list)
    for r in A[arm]:
        ta[r["task"]].append(r)
    for r in A[other]:
        to[r["task"]].append(r)
    common = sorted(set(ta) & set(to))
    if not common:
        return None
    out = {}
    for key, fn in (("solve", lambda r: r["solved"]), ("nopatch", lambda r: r["patch"] == 0), ("timeend", lambda r: r["end"] == "time"),
                    ("edited", lambda r: r["edited"]), ("agent_s", lambda r: r["agent_s"]), ("capped", lambda r: r["capped"]),
                    ("s_reply", lambda r: r["s_reply"])):
        da = [st.mean(fn(r) for r in ta[t]) for t in common]
        do = [st.mean(fn(r) for r in to[t]) for t in common]
        out[key] = (st.mean(da), st.mean(do))
    wins = sum(st.mean(r["solved"] for r in ta[t]) > st.mean(r["solved"] for r in to[t]) for t in common)
    losses = sum(st.mean(r["solved"] for r in ta[t]) < st.mean(r["solved"] for r in to[t]) for t in common)
    return len(common), sum(len(ta[t]) for t in common), sum(len(to[t]) for t in common), out, wins, losses


if __name__ == "__main__":
    big = sorted((a for a in A if len(A[a]) >= 20), key=lambda a: -len(A[a]))
    print("\n== agents with >= 20 runs (raw, not task-matched)")
    print(f"{'arm':14}{'n':>5}{'solve':>7}{'nopat':>7}{'edit':>6}{'time':>6}{'agt_s':>7}{'s/rep':>7}{'out':>6}{'cap/r':>6}{'>=3.5k':>7}{'comp':>5}{'nudg':>5}{'calls':>6}{'fe_md':>6}  sampling")
    for a in big:
        s = summ(A[a])
        r0 = A[a][0]
        print(f"{a:14}{s['n']:5}{s['solve']:7.0%}{s['nopatch']:7.0%}{s['edited']:6.0%}{s['timeend']:6.0%}{s['agent_s']:7.0f}{s['s_reply']:7.1f}"
              f"{s['out']:6.0f}{s['capped']:6.2f}{s['long']:7.1%}{s['comp']:5.1f}{s['nudges']:5.1f}{s['calls']:6.1f}{str(s['fe_med']):>6}  T{r0['temp']} think {r0['budget']} out {r0['max_out']} tools {r0['n_tools']}")
    print("\n== sk_a2 vs others, TASK-MATCHED (mean over common tasks of per-task rates): sk_a2 | other")
    for o in big:
        if o == "sk_a2":
            continue
        m = matched("sk_a2", o)
        if not m or m[0] < 4:
            continue
        nt, na, no, out, w, l = m
        print(f"  vs {o:13} tasks {nt:3} runs {na:4}/{no:4} | solve {out['solve'][0]:.0%}/{out['solve'][1]:.0%} (tasks better {w}, worse {l}) | nopatch {out['nopatch'][0]:.0%}/{out['nopatch'][1]:.0%}"
              f" | time {out['timeend'][0]:.0%}/{out['timeend'][1]:.0%} | edited {out['edited'][0]:.0%}/{out['edited'][1]:.0%} | agent {out['agent_s'][0]:.0f}/{out['agent_s'][1]:.0f}s"
              f" | s/reply {out['s_reply'][0]:.1f}/{out['s_reply'][1]:.1f} | capped/run {out['capped'][0]:.2f}/{out['capped'][1]:.2f}")
