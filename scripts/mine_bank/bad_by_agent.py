"""Bad tool calls PER AGENT (MINING 2026-11-11e): for each agent, each kind of bad call with the share of its runs hit,
calls, model seconds per run, and the kind's dominant pattern in that agent. Usage:
    python3 -I scripts/mine_bank/bad_by_agent.py [MIN_RUNS] [agent ...]   (repo root; default: >= 40 runs + the current line)
Patterns: garbled = a backtick where the string should close ('`,old_string:'), resent identically next; edit no-match =
old_string written from memory (not copied from an earlier output); inline python = python -c with escaped quotes /
f-string / several statements; read range = end = start - 1; text call = cut at the output-token limit; after budget = the
refused call was the run's first edit."""
import collections, glob, importlib.util, json, os, re, sys

spec = importlib.util.spec_from_file_location("bc", os.path.join(os.path.dirname(os.path.abspath(__file__)), "bad_calls.py"))
bc = importlib.util.module_from_spec(spec); spec.loader.exec_module(bc)
ARGS = [a for a in sys.argv[1:] if not a.isdigit()]
MIN_RUNS = int(next((a for a in sys.argv[1:] if a.isdigit()), 40))
ALWAYS = ["combo1", "evidc", "evidd", "evide"]
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")
KINDS = ["garbled_args", "skill_args", "edit_nomatch", "inline_py_syntax", "read_range", "write_outside", "tool_as_shell",
         "code_as_shell", "shell_quote", "text_call", "unknown_tool", "after_budget"]
LABEL = {"garbled_args": "garbled edit", "skill_args": "garbled skill call", "edit_nomatch": "edit text not in file",
         "inline_py_syntax": "inline python broken", "read_range": "read range reversed", "write_outside": "write_file to /tmp",
         "tool_as_shell": "tool name in shell", "code_as_shell": "python run as bash", "shell_quote": "shell quoting",
         "text_call": "call written as text", "unknown_tool": "tool it lacks", "after_budget": "calls after budget"}
PAT = {"garbled_args": "resent identically", "skill_args": "backtick closes a string", "edit_nomatch": "old_string from memory",
       "inline_py_syntax": "python -c w/ quotes/f-string", "read_range": "end = start-1", "text_call": "cut at token limit",
       "after_budget": "run's first edit refused", "write_outside": "test/repro script"}


def ws(x):
    return re.sub(r"\s+", " ", x).strip()


runs_of = collections.Counter(); hit = collections.defaultdict(set); calls = collections.Counter(); secs = collections.Counter()
pat = collections.Counter(); bt = collections.Counter()
for D in sorted(glob.glob("data/results/2026-*")):
    if any(k in D for k in ("e4b", "probe", "replay", "12b")):
        continue
    rq = D + "/requests/requests.jsonl"
    if not os.path.exists(rq):
        continue
    res_of, jobs = {}, collections.defaultdict(list)
    for l in open(rq):
        try: r = json.loads(l)
        except Exception: continue
        if not (isinstance(r.get("reply"), dict) and r.get("job")): continue
        if r["request"].get("model") and "31b" not in str(r["request"]["model"]): continue
        for m in r["request"]["messages"]:
            if m.get("role") == "tool": res_of.setdefault(m.get("tool_call_id"), str(m.get("content")))
        jobs[r["job"]].append(r)
    for job, q in jobs.items():
        arm = job.partition("#a")[2].rsplit(".", 1)[0]; key = D + job
        runs_of[arm] += 1
        q.sort(key=lambda r: r["t"]); seen = []; prev_raw = None; worked = False; budget_on = False
        for r in q:
            msg = r["reply"]["message"]; cl = msg.get("tool_calls") or []; sec = r.get("seconds") or 0
            if not cl:
                txt = str(msg.get("content") or "")
                if bc.TEXT_CALL.search(txt):
                    k = "text_call"; hit[(arm, k)].add(key); calls[(arm, k)] += 1; secs[(arm, k)] += sec
                    pat[(arm, k)] += r["reply"].get("finish_reason") == "length"
                continue
            for c in cl:
                name = c["function"]["name"]; raw = c["function"].get("arguments") or ""; res = res_of.get(c.get("id"), "")
                try: a = json.loads(raw)
                except Exception: a = {}
                k = bc.kind_of(name, raw, res, "")
                if name not in bc.TOOLS: k = k or "unknown_tool"
                if k:
                    hit[(arm, k)].add(key); calls[(arm, k)] += 1
                    if k != "after_budget" and not budget_on: secs[(arm, k)] += sec / len(cl)
                    if k == "after_budget":
                        if not budget_on: secs[(arm, k)] += 0
                        budget_on = True
                        if name in ("edit_file", "write_file") and not worked: pat[(arm, k)] += 1
                    elif k == "garbled_args":
                        pat[(arm, k)] += raw == prev_raw
                        bt[(arm, k)] += bool(re.search(r"`\s*,\s*\w+\s*:", raw))
                    elif k == "skill_args":
                        pat[(arm, k)] += bool(re.search(r"`\s*,\s*\w+\s*:|`\s*[,}\]]", raw))
                    elif k == "edit_nomatch":
                        old = str(a.get("old_string") or "")
                        pat[(arm, k)] += bool(old.strip()) and not any(old in o for o in seen)
                    elif k == "inline_py_syntax":
                        cmd = str(a.get("command") or raw)
                        body = cmd.split("-c", 1)[1] if "-c" in cmd else ""
                        pat[(arm, k)] += bool(body) and bool("\\'" in body or '\\"' in body or re.search(r"\bf['\"]", body) or ";" in body)
                    elif k == "read_range":
                        try: pat[(arm, k)] += int(a.get("end_line")) == int(a.get("start_line")) - 1
                        except Exception: pass
                    elif k == "write_outside":
                        pat[(arm, k)] += bool(re.search(r"test|repro|check|debug|verify", str(a.get("filepath") or ""), re.I))
                fp = str(a.get("filepath") or "")
                if name in ("edit_file", "write_file") and '"status": "ok"' in res[:30] and fp and not TEST.search(fp):
                    worked = True
                prev_raw = raw
                if res: seen.append(bc.flat(res))
            if budget_on:
                secs[(arm, "after_budget")] += sec  # the after-budget tail: every model request from the first refused call on

agents = ARGS or sorted([a for a, n in runs_of.items() if n >= MIN_RUNS] + [a for a in ALWAYS if runs_of[a] < MIN_RUNS], key=lambda a: -runs_of[a])
for arm in agents:
    n = runs_of[arm]
    if not n: continue
    tot = sum(secs[(arm, k)] for k in KINDS) / n
    print(f"\n### {arm}: {n} runs | time lost to bad calls {tot:.0f} s/run")
    rows = []
    for k in KINDS:
        h = len(hit[(arm, k)])
        if not h: continue
        p = f"{PAT[k]} {pat[(arm, k)]}/{calls[(arm, k)]}" if k in PAT else ""
        if k == "garbled_args": p += f", backtick closes the text {bt[(arm, k)]}/{calls[(arm, k)]}"
        if k == "after_budget": p = f"{PAT[k]} in {pat[(arm, k)]} calls"
        rows.append((secs[(arm, k)] / n, h, k, p))
    for s_, h, k, p in sorted(rows, key=lambda x: (-x[1], -x[0])):
        print(f"  {LABEL[k]:22s} {h:4d} runs ({h / n:5.1%}) {calls[(arm, k)]:5d} calls {s_:5.1f} s/run | {p}")

# few-shot fit (our tests: an example reliably changes the FORM of a call: gate prefix 24% -> 100% (r76), heredoc use 4 -> 19
# (r69, with a side effect: longer scripts); it did not change a DECISION: the move after a refusal (r74, edit_file next 2/9))
FORM = ["edit_nomatch", "inline_py_syntax", "tool_as_shell", "code_as_shell", "shell_quote", "write_outside", "read_range"]
NOT = {"garbled_args": "native call syntax", "skill_args": "native call syntax", "after_budget": "counting / decision",
       "text_call": "output-token limit / parser", "unknown_tool": "rare"}
print(f"\n{'agent':12s} {'runs':>5s} {'lost s/run':>10s} {'few-shot-able s/run':>20s} {'not few-shot s/run':>19s}  biggest few-shot-able kinds (runs hit)")
for arm in agents:
    n = runs_of[arm]
    if not n: continue
    fs = sum(secs[(arm, k)] for k in FORM) / n; nf = sum(secs[(arm, k)] for k in NOT) / n
    top = sorted(((len(hit[(arm, k)]), k) for k in FORM if hit[(arm, k)]), reverse=True)[:3]
    print(f"{arm:12s} {n:5d} {fs + nf:10.1f} {fs:20.1f} {nf:19.1f}  " + ", ".join(f"{LABEL[k]} {h / n:.0%}" for h, k in top))
