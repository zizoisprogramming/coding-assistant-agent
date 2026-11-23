"""r150: sk_a2 (control) vs sk_a2ge (gatherer -> editor) on rich_3521 / 3480 / 3278 / fastapi_15589 x 2 accounts (bars in docs/PLAN.md RUN BUILT
r150). Per sk_a2ge run: gather stage (requests, tool calls, seconds, thinking tokens, READING CLOSED, edits / submits), the brief (length, file
named = a real-fix file?), the editor (start second, first call, calls, seconds), and the reply-time split. Run: python3 -I scripts/mine_bank/r150.py"""
import ast, collections, glob, json, re, statistics as st
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
GOLD = {json.loads(l)["instance_id"]: set(re.findall(r"^\+\+\+ b/(\S+)", json.loads(l)["patch"], re.M)) for l in open(ROOT / "data/tasks.jsonl")}


def parse(x):
    if isinstance(x, dict): return x
    try: return ast.literal_eval(str(x))
    except Exception:
        try: return json.loads(str(x))
        except Exception: return {}


rows = []
for d in sorted(glob.glob(str(ROOT / "data/results/2026-11-2[34]_skill_r150_s*"))):
    G = {}
    for l in open(f"{d}/results/gen_per_task.jsonl"):
        g = json.loads(l); G[g["instance_id"] + "#a" + g["attempt"]] = g
    by = collections.defaultdict(list)
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        r = json.loads(l); by[r["job"]].append(r)
    for job, rs in by.items():
        g = G.get(job)
        if not g or g["arm"] != "sk_a2ge": continue
        rs = sorted(rs, key=lambda r: float(r["t"]))
        t0 = float(rs[0]["t"])
        st_ = {"gather": dict(req=0, calls=[], s=0.0, out=[], end=None), "editor": dict(req=0, calls=[], s=0.0, out=[], start=None), "summary": dict(req=0, s=0.0)}
        brief = ""; closed = 0
        res = {}
        for r in rs:
            for m in r["request"]["messages"]:
                if m.get("role") == "tool": res[m.get("tool_call_id")] = str(m.get("content"))
        for r in rs:
            msgs = r["request"]["messages"]
            sysm = str(msgs[0].get("content")) if msgs and msgs[0].get("role") == "system" else ""
            stage = "editor" if "second of two engineers" in sysm else "gather" if "first of two engineers" in sysm else "summary"
            rep = parse(r.get("reply")) or {}
            secs = float(r.get("seconds") or 0)
            S = st_[stage]; S["req"] += 1; S["s"] += secs
            if stage == "summary": continue
            S["out"].append((rep.get("usage") or {}).get("completion_tokens") or 0)
            if stage == "editor" and S["start"] is None:
                S["start"] = float(r["t"]) - t0
                brief = sysm.split("## The BRIEF from your colleague", 1)[-1].strip()
            m = rep.get("message") or {}
            for c in m.get("tool_calls") or []:
                fn = c.get("function") or {}
                a = fn.get("arguments") or ""
                out = res.get(c.get("id"), "")
                if "READING CLOSED" in out: closed += 1
                k = fn.get("name")
                if k == "run_command":
                    k = "a.py " + a.split("a.py", 1)[1].split()[0].strip('"') if "a.py" in a else ("RUN" if "python" in a else "shell")
                S["calls"].append(k)
            if stage == "gather" and not m.get("tool_calls"): S["end"] = float(r["t"]) - t0 + secs
        bf = re.search(r"FILE:\s*(\S+)", brief)
        rows.append(dict(s=Path(d).name[-2:], task=g["instance_id"], ok=g.get("resolved") in (True, "True"), end=g["end"], agent=float(g["agent_s"]),
                         g_calls=len(st_["gather"]["calls"]), g_s=st_["gather"]["s"], g_end=st_["gather"]["end"], g_out=st_["gather"]["out"],
                         g_seq=st_["gather"]["calls"], closed=closed, brief_len=len(brief), brief_file=bf.group(1) if bf else None,
                         brief_gold=bool(bf and any(bf.group(1).lstrip("./").endswith(x) or x.endswith(bf.group(1).lstrip("./")) for x in GOLD[g["instance_id"]])),
                         e_start=st_["editor"]["start"], e_calls=st_["editor"]["calls"], e_s=st_["editor"]["s"], e_out=st_["editor"]["out"],
                         sum_req=st_["summary"]["req"], sum_s=st_["summary"]["s"]))
for r in sorted(rows, key=lambda r: (r["task"], r["s"])):
    print(f"\n{r['task']:14}{r['s']} {'SOLVED' if r['ok'] else 'failed'} {r['end']} agent {r['agent']:.0f}s")
    print(f"  GATHER: {r['g_calls']} calls, model time {r['g_s']:.0f}s, brief written at {r['g_end'] if r['g_end'] is None else round(r['g_end'])}s, READING CLOSED x{r['closed']},"
          f" thinking/output tokens per reply {r['g_out']}")
    print(f"     calls: {' '.join(r['g_seq'])}")
    print(f"  BRIEF: {r['brief_len']} chars, FILE {r['brief_file']} (real-fix file: {r['brief_gold']})")
    print(f"  EDITOR: started at {r['e_start'] if r['e_start'] is None else round(r['e_start'])}s, {len(r['e_calls'])} calls, model time {r['e_s']:.0f}s, tokens {r['e_out']}")
    print(f"     calls: {' '.join(r['e_calls'])}")
    print(f"  compaction summaries: {r['sum_req']} ({r['sum_s']:.0f}s)")
print("\nSUMMARY sk_a2ge:", f"editor reached {sum(r['e_start'] is not None for r in rows)}/{len(rows)};",
      f"brief by call 14: {sum(r['g_end'] is not None and r['g_calls'] <= 14 for r in rows)}/{len(rows)};",
      f"brief names a real-fix file {sum(r['brief_gold'] for r in rows)}/{len(rows)};",
      f"editor's first call an edit {sum(bool(r['e_calls']) and r['e_calls'][0] in ('edit_file',) for r in rows)}/{len(rows)};",
      f"gather edits/submits {sum(any(c in ('edit_file', 'write_file', 'submit_patch') for c in r['g_seq']) for r in rows)};",
      f"median brief at {st.median([r['g_end'] for r in rows if r['g_end']]):.0f}s")
