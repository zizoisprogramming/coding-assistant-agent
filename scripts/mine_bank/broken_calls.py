"""Broken tool calls ('mandatory input parameters are not present') across the bank (2026-11-19; user: 'explain the
cut-apart ... before trying 1.0 see where we can change'). Run: python3 -I scripts/mine_bank/broken_calls.py (repo root)
Gemma 4 wraps every string argument in one special token <|"|> (Google, Gemma 4 prompt formatting); vLLM's presence
penalty subtracts from every token already in the reply's output, special tokens not excluded (vllm
model_executor/layers/utils.py apply_penalties). Per arm (edit_file / write_file calls): broken share; the stray
character that closed a string instead of <|"|> (the char before ',<argname>:' inside a value); first edit call of a
run broken; a broken call followed by another broken call; which argument went missing; example style of the prompt."""
import collections, glob, json, re

REQ = {"edit_file": ["filepath", "old_string", "new_string"], "write_file": ["filepath", "content"]}
st = collections.defaultdict(collections.Counter)
fmt = {}
for d in sorted(glob.glob("data/results/2026-1*_*")):
    p = f"{d}/requests/requests.jsonl"
    if not glob.glob(p):
        continue
    seq = collections.defaultdict(list)
    for l in open(p, errors="replace"):
        try:
            r = json.loads(l)
        except Exception:
            continue
        m = re.search(r"#a([A-Za-z0-9_]+?)\.\d", r.get("job", ""))
        msgs = (r.get("request") or {}).get("messages") or []
        if not m or not msgs:
            continue
        arm = m.group(1)
        if arm not in fmt:
            s = str(msgs[0].get("content"))
            fmt[arm] = "fenced old_string" if re.search(r"old_string:\s*\n```", s) else ("old_string other" if "old_string" in s else "no edit example")
        last = msgs[-1]
        if last.get("role") != "tool":
            continue
        a = next((x for x in reversed(msgs) if x.get("role") == "assistant"), None)
        for c in (a or {}).get("tool_calls") or []:
            n = c["function"]["name"]
            if n not in REQ:
                continue
            broken = "mandatory input parameters" in str(last.get("content"))
            seq[(arm, r["job"])].append((float(r["t"]), broken))
            st[arm]["calls"] += 1
            if broken:
                st[arm]["broken"] += 1
                s = c["function"]["arguments"]
                mm = re.search(r"(.)(?:\\n)?,(?:filepath|old_string|new_string|content):", s)
                ch = mm.group(1) if mm else None
                st[arm]["closer " + {"`": "backtick", "'": "single quote", '"': "double quote"}.get(ch, "other" if ch else "none")] += 1
                try:
                    keys = list(json.loads(s).keys())
                except Exception:
                    keys = []
                st[arm]["missing " + ",".join(k for k in REQ[n] if k not in keys)] += 1
    for (arm, job), xs in seq.items():
        xs.sort()
        st[arm]["runs with an edit"] += 1
        st[arm]["first edit broken"] += xs[0][1]
        for (_, b1), (_, b2) in zip(xs, xs[1:]):
            if b1:
                st[arm]["after broken"] += 1
                st[arm]["after broken, broken again"] += b2
print(f"{'arm':12} {'example style':18} {'calls':>6} {'broken':>7} {'first edit broken':>18} {'again after broken':>19}  stray closers / missing")
for arm, c in sorted(st.items(), key=lambda kv: -kv[1]["calls"]):
    if c["calls"] < 40:
        continue
    closers = {k[7:]: v for k, v in c.items() if k.startswith("closer ")}
    missing = {k[8:]: v for k, v in c.items() if k.startswith("missing ")}
    print(f"{arm:12} {fmt.get(arm, '?'):18} {c['calls']:6} {100 * c['broken'] / c['calls']:6.1f}% {c['first edit broken']:6}/{c['runs with an edit']:<4} ({100 * c['first edit broken'] / max(1, c['runs with an edit']):3.0f}%)"
          f" {100 * c['after broken, broken again'] / max(1, c['after broken']):12.0f}%       {closers} / {missing}")
