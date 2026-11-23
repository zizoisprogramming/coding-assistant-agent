"""r149: sk_a2 (control) vs sk_a2tm (a.py TESTS THAT USE template) vs sk_a2tr (+ test the rule) on rich_3521 / 3480 / 3278 / fastapi_15589 x 2
accounts (bars in docs/PLAN.md RUN BUILT r149). Per run: outcome, time, first source edit call, TESTS THAT USE blocks received (name), the
agent's check scripts after the edit (write_file .git/agent/check.py or a heredoc): number of asserts, whether a template name is used, the last
own check green / red, compactions. Run: python3 -I scripts/mine_bank/r149.py"""
import ast, collections, glob, json, re, statistics as st
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SRC = re.compile(r"(repro|check|debug|scratch|\.git/agent|/tmp/|test)")


def parse(x):
    if isinstance(x, dict): return x
    try: return ast.literal_eval(str(x))
    except Exception:
        try: return json.loads(str(x))
        except Exception: return {}


rows = []
for d in sorted(glob.glob(str(ROOT / "data/results/2026-11-2[34]_skill_r149_s*"))):
    G = {}
    for l in open(f"{d}/results/gen_per_task.jsonl"):
        g = json.loads(l); G[g["instance_id"] + "#a" + g["attempt"]] = g
    by = collections.defaultdict(list)
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        r = json.loads(l); by[r["job"]].append(r)
    for job, rs in by.items():
        g = G.get(job)
        if not g: continue
        allr = sorted(rs, key=lambda r: float(r["t"]))
        rs = [r for r in allr if len(r["request"]["messages"]) > 1]
        res = {}
        for r in rs:
            for m in r["request"]["messages"]:
                if m.get("role") == "tool": res[m.get("tool_call_id")] = str(m.get("content"))
        seq, edited, fe, blocks, checks, last, comp, lp = [], False, None, [], [], None, 0, 0
        for r in rs:
            rep = parse(r.get("reply")) or {}
            p = (rep.get("usage") or {}).get("prompt_tokens") or 0
            if lp and p < 0.7 * lp: comp += 1
            lp = p
            for c in (rep.get("message") or {}).get("tool_calls") or []:
                fn = c.get("function") or {}
                try: a = json.loads(fn.get("arguments") or "{}")
                except Exception: a = {}
                if not isinstance(a, dict): a = {}
                n, cmd, out = fn.get("name"), str(a.get("command", "")), res.get(c.get("id"), "")
                for m in re.finditer(r">>> TESTS THAT USE (\w+)", out): blocks.append(m.group(1))
                src_edit = (n == "edit_file" and not SRC.search(str(a.get("filepath", "")))) or (("OLD_TEXT" in cmd or ".replace(" in cmd) and "a.py" not in cmd and "check" not in cmd)
                if src_edit and "BudgetExceeded" not in out and '"status": "error"' not in out:
                    if not edited: fe = len(seq)
                    edited = True; seq.append("EDIT"); continue
                if n == "write_file" and "check" in str(a.get("filepath", "")):
                    body = str(a.get("content", ""))
                    checks.append(dict(after=edited, asserts=len(re.findall(r"\bassert\b", body)), names=body)); seq.append("write_check"); continue
                if "a.py" in cmd: seq.append(cmd.split("a.py", 1)[1].split()[0]); continue
                if "pytest" in cmd or "python" in cmd:
                    if "<<" in cmd and edited: checks.append(dict(after=True, asserts=len(re.findall(r"\bassert\b", cmd)), names=cmd))
                    if edited:
                        last = "red" if re.search(r"\b\d+ failed\b|Traceback|AssertionError|Error:|\"exit_code\": [1-9]", out) else "green"
                    seq.append("pytest" if "pytest" in cmd else "RUN"); continue
                seq.append(n[:6] if n else "?")
        post = [c for c in checks if c["after"]]
        reuse = any(b in c["names"] for c in post for b in blocks) if blocks else None
        rows.append(dict(s=Path(d).name[-2:], arm=g["arm"], task=g["instance_id"], ok=g.get("resolved") in (True, "True"), end=g["end"], agent=float(g["agent_s"]),
                         patch=int(g.get("patch_chars") or 0), fe=fe, blocks=blocks, n_post=len(post), max_asserts=max([c["asserts"] for c in post], default=0),
                         reuse=reuse, last=last, comp=comp, seq=seq))
for r in sorted(rows, key=lambda r: (r["arm"], r["task"], r["s"])):
    print(f"{r['arm']:8}{r['task']:14}{r['s']} {'SOLVED' if r['ok'] else 'failed':7}{r['end']:5}{r['agent']:4.0f}s patch {r['patch']:4} fe {str(r['fe']):4} TESTS {','.join(r['blocks']) or '-':22}"
          f" post-edit checks {r['n_post']} max asserts {r['max_asserts']} reuse {r['reuse']!s:5} last {r['last']}")
print()
for arm in ("sk_a2", "sk_a2tm", "sk_a2tr"):
    R = [r for r in rows if r["arm"] == arm]
    E = [r for r in R if r["patch"] > 0]
    W = [r for r in R if r["patch"] > 0 and not r["ok"]]
    B = [r for r in R if r["blocks"]]
    print(f"{arm:8} solved {sum(r['ok'] for r in R)}/{len(R)} | mean agent {st.mean(r['agent'] for r in R):.0f}s | time ends {sum(r['end'] == 'time' for r in R)} | comp {st.mean(r['comp'] for r in R):.2f}"
          f" | template shown in {len(B)} runs, reused {sum(bool(r['reuse']) for r in B)} | edited runs with a >= 2-assert check {sum(r['max_asserts'] >= 2 for r in E)}/{len(E)}"
          f" | wrong kept edits {len(W)}, own check green {sum(r['last'] == 'green' for r in W)}")
