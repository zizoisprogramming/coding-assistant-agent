"""Bad tool calls over the whole run bank (31B runs): every malformed or misused call, by kind, by arm, and with / without
the prompt rule written against it. Usage: python3 -I scripts/mine_bank/bad_calls.py [OUT.json]   (repo root; ~5 min)

Kinds (from the tool result the harness sent back, or the reply itself):
  garbled_args    edit_file / write_file "mandatory input parameters are not present" (a string ended with a backtick or a
                  stray quote and swallowed the next argument)
  skill_args      run_skill_script without skill_name / file_path ("Argument 'skill_name' is required")
  after_budget    any call after "Tool call budget exhausted" (the harness refuses it)
  edit_nomatch    edit_file old_string not found in the file
  read_range      read_file start_line > end_line or another read_file ValueError
  write_outside   write_file outside /workspace ("Path traversal detected", e.g. /tmp/repro.py)
  tool_as_shell   a tool name run as a shell command ("read_file: command not found", "edit_file: command not found")
  code_as_shell   Python run as bash ("from: command not found", "import: command not found", "def: command not found")
  shell_quote     bash syntax errors ("syntax error near unexpected token", "unexpected EOF while looking for matching")
  inline_py_syntax  python -c / heredoc code that does not parse (File "<string>" ... SyntaxError / IndentationError)
  unknown_tool    a call to a tool the agent does not have
  text_call       a reply with no tool call whose text is a tool call written out (the call never runs)
  same_failed_again  the exact call (name + arguments) repeated right after it failed
Rules checked (system prompt text): garble rule ("mandatory input parameters are not present"), /tmp rule ("write_file only
writes inside /workspace"), budget line ("tool calls and"), read_file / sed reading rules are not checked."""
import collections, glob, json, os, re, sys

KINDS = ["garbled_args", "skill_args", "after_budget", "edit_nomatch", "read_range", "write_outside", "tool_as_shell",
         "code_as_shell", "shell_quote", "inline_py_syntax", "unknown_tool", "text_call", "same_failed_again"]
TOOLS = {"run_command", "read_file", "edit_file", "write_file", "get_status", "submit_patch", "run_skill_script", "load_skill",
         "load_skill_resource", "list_skills", "search_similar_code", "get_code_neighbors", "get_code_subgraph", "transfer_to_agent"}
TEXT_CALL = re.compile(r"(^|\n)\s*(```(tool_code|json|python)?\s*\n\s*)?(edit_file|run_command|read_file|write_file|submit_patch|run_skill_script)\s*\(|"
                       r"\"name\"\s*:\s*\"(edit_file|run_command|read_file|write_file|submit_patch|run_skill_script)\"|<\|?tool_call|call:(edit_file|run_command|read_file)")


def flat(res):
    """tool results arrive as JSON text: unescape their string fields so newlines and quotes are real."""
    try:
        d = json.loads(res)
    except Exception:
        return res
    out = []

    def walk(v):
        if isinstance(v, dict):
            for x in v.values(): walk(x)
        elif isinstance(v, list):
            for x in v: walk(x)
        elif isinstance(v, str):
            out.append(v)
    walk(d)
    return res[:200] + "\n" + "\n".join(out)


def kind_of(name, args_raw, res, sysm):
    res = flat(res)
    low = res[:800]
    if "mandatory input parameters are not present" in low:
        return "skill_args" if name == "run_skill_script" else "garbled_args"
    if "Tool call budget exhausted" in low:
        return "after_budget"
    if name == "run_skill_script" and ("INVALID_ARGUMENTS" in low or "is required" in low):
        return "skill_args"
    if name not in TOOLS or re.search(r"(not found in the tools|Function \S+ is not found|Tool '?\S+'? not found|unknown tool)", low, re.I):
        return "unknown_tool"
    if name == "edit_file" and "old_string not found" in low:
        return "edit_nomatch"
    if name == "read_file" and ("ValueError" in low or "cannot be greater" in low):
        return "read_range"
    if name == "write_file" and ("Path traversal" in low or "outside" in low and "error" in low):
        return "write_outside"
    if name in ("run_command", "run_skill_script"):
        if re.search(r"\b(read_file|edit_file|write_file|submit_patch|get_status|run_command): command not found", res):
            return "tool_as_shell"
        if re.search(r"\b(from|import|def|class|print\(|if|for|assert): command not found|syntax error near unexpected token `\('", res) and "python" not in args_raw[:40]:
            return "code_as_shell"
        if re.search(r"syntax error near unexpected token|unexpected EOF while looking for matching|unexpected end of file", res):
            return "shell_quote"
        if re.search(r"File \"<(string|stdin)>\", line \d+[^\n]*\n(.*\n){0,3}?\s*(SyntaxError|IndentationError)", res) or \
                re.search(r"File \"<(string|stdin)>\", line \d+.{0,400}(SyntaxError|IndentationError)", res, re.S):
            return "inline_py_syntax"
    return None


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else None
    per_run = {}  # job key -> dict
    for D in sorted(glob.glob("data/results/2026-*")):
        if any(k in D for k in ("e4b", "probe", "replay", "12b")):
            continue
        rq = D + "/requests/requests.jsonl"
        if not os.path.exists(rq):
            continue
        res_of = {}; reqs = []
        for l in open(rq):
            try:
                r = json.loads(l)
            except Exception:
                continue
            if not (isinstance(r.get("reply"), dict) and r.get("job")):
                continue
            model = str(r["request"].get("model", ""))
            if model and "31b" not in model:
                continue
            for m in r["request"]["messages"]:
                if m.get("role") == "tool":
                    res_of.setdefault(m.get("tool_call_id"), str(m.get("content")))
            sysm = str(r["request"]["messages"][0].get("content") or "") if r["request"]["messages"] else ""
            tools = {t.get("function", {}).get("name") for t in r["request"].get("tools") or []}
            reqs.append((r["job"], r["t"], r["reply"]["message"], sysm, tools))
        reqs.sort(key=lambda x: (x[0], x[1]))
        last = {}
        for job, t, msg, sysm, tools in reqs:
            key = D.rsplit("/", 1)[1] + "|" + job
            arm = job.partition("#a")[2].rsplit(".", 1)[0] or "?"
            x = per_run.setdefault(key, dict(arm=arm, folder=D.rsplit("/", 1)[1], calls=collections.Counter(), bad=collections.Counter(),
                                             garble_rule=False, tmp_rule=False, budget_line=False, examples={}))
            x["garble_rule"] |= "mandatory input parameters are not present" in sysm
            x["tmp_rule"] |= "write_file only writes inside /workspace" in sysm  # combo1's fixed line
            x["tmp_line"] = x.get("tmp_line", False) or bool(re.search(r"[Ss]cratch[^.\n]{0,40}/tmp", sysm))  # pub024-style 'scratch files in /tmp'
            x["agent_names"] = x.get("agent_names", set()) | {m.group(1) for m in [re.search(r'internal name is "(\w+)"', sysm)] if m}
            x["budget_line"] |= bool(re.search(r"\d+ tool calls", sysm))
            calls = msg.get("tool_calls") or []
            if not calls:
                txt = str(msg.get("content") or "")
                if TEXT_CALL.search(txt):
                    x["bad"]["text_call"] += 1; x["examples"].setdefault("text_call", txt[:300])
                    x.setdefault("text_call_at", []).append(t)
                x["last_t"] = t
                continue
            x["last_t"] = t
            for c in calls:
                name = c["function"]["name"]; raw = c["function"].get("arguments") or ""
                x["calls"][name] += 1; x["calls"]["*"] += 1
                res = res_of.get(c.get("id"))
                if res is None:
                    continue
                k = kind_of(name, raw, res, sysm)
                if name not in TOOLS or (tools and name not in tools and name != "transfer_to_agent"):
                    k = k or "unknown_tool"
                if k:
                    x["bad"][k] += 1; x["examples"].setdefault(k, (name + " " + raw[:200] + " -> " + res[:200]))
                failed = (k not in (None, "after_budget")) or ('"status": "error"' in res[:40] and "CommandError" not in res[:80] and "BudgetExceeded" not in res[:80])
                sig = (name, raw)
                if failed and last.get(key) == (sig, True):
                    x["bad"]["same_failed_again"] += 1
                last[key] = (sig, failed)
        print(f"{D.rsplit('/', 1)[1]:45s} runs so far {len(per_run)}", file=sys.stderr)
    runs = list(per_run.values())
    n = len(runs); calls = sum(r["calls"]["*"] for r in runs)
    print(f"\n31B runs with tool calls: {n} | tool calls: {calls}")
    print(f"{'kind':18s} {'calls':>6s} {'per 1k calls':>12s} {'runs with it':>13s}  top arms (runs with it / runs)")
    arms = collections.Counter(r["arm"] for r in runs)
    for k in KINDS:
        c = sum(r["bad"][k] for r in runs); rr = [r for r in runs if r["bad"][k]]
        top = collections.Counter(r["arm"] for r in rr).most_common(4)
        print(f"{k:18s} {c:6d} {1000 * c / max(1, calls):12.1f} {len(rr):6d} ({len(rr) / max(1, n):5.1%})  " + ", ".join(f"{a} {v}/{arms[a]}" for a, v in top))
    # edit-call denominators for the rule comparisons
    def rate(rows, k, tool):
        b = sum(r["bad"][k] for r in rows); d = sum(r["calls"][tool] for r in rows)
        return f"{b}/{d} {tool} calls = {b / max(1, d):.1%}, runs {sum(1 for r in rows if r['bad'][k])}/{len(rows)} = {sum(1 for r in rows if r['bad'][k]) / max(1, len(rows)):.1%}"
    print("\nRule in the prompt vs not:")
    for flag, k, tool in (("garble_rule", "garbled_args", "edit_file"), ("tmp_rule", "write_outside", "write_file")):
        w = [r for r in runs if r[flag]]; wo = [r for r in runs if not r[flag]]
        print(f"  {k:14s} with {flag}: {rate(w, k, tool)} | without: {rate(wo, k, tool)}")
    # same task, same period: combo1-family vs pub024 (pub024 has no garble rule; combo1 = pub024 + rule)
    print("\nSame-run pairs (folders that ran both arms):")
    for a, b in (("pub024", "combo1"), ("pub024", "kf2"), ("combo1", "evidc"), ("evidc", "evidd")):
        F = {r["folder"] for r in runs if r["arm"] == a} & {r["folder"] for r in runs if r["arm"] == b}
        for k, tool in (("garbled_args", "edit_file"), ("write_outside", "write_file"), ("after_budget", "*"), ("edit_nomatch", "edit_file")):
            ra = rate([r for r in runs if r["arm"] == a and r["folder"] in F], k, tool)
            rb = rate([r for r in runs if r["arm"] == b and r["folder"] in F], k, tool)
            print(f"  {a} vs {b} ({len(F)} folders) {k:13s}: {a} {ra} | {b} {rb}")
    print("\n/tmp: write_file outside /workspace by prompt line (pub024-style 'scratch in /tmp' line, combo1's fix adds 'write_file only writes inside /workspace'):")
    for lab, sel in (("scratch-in-/tmp line WITHOUT the fix", lambda r: r.get("tmp_line") and not r["tmp_rule"]),
                     ("scratch-in-/tmp line WITH the fix", lambda r: r["tmp_rule"]),
                     ("no /tmp line", lambda r: not r.get("tmp_line") and not r["tmp_rule"])):
        rows = [r for r in runs if sel(r)]
        print(f"  {lab:40s} {rate(rows, 'write_outside', 'write_file')}")
    print("\nCurrent family (combo1, evidc, evidd, evide), per kind:")
    cur = [r for r in runs if r["arm"] in ("combo1", "evidc", "evidd", "evide")]
    cc = sum(r["calls"]["*"] for r in cur)
    print(f"  {len(cur)} runs, {cc} calls")
    for k in KINDS:
        c = sum(r["bad"][k] for r in cur); rr = sum(1 for r in cur if r["bad"][k])
        if c: print(f"  {k:18s} {c:5d} calls ({1000 * c / max(1, cc):.1f} per 1k) in {rr} runs ({rr / max(1, len(cur)):.1%})")
    tc = [r for r in runs if r["bad"]["text_call"]]
    ended = sum(1 for r in tc if r.get("text_call_at") and r["text_call_at"][-1] >= r.get("last_t", 0))
    print(f"\ntext_call: {len(tc)} runs; the written-out call was the run's last reply in {ended} (the agent stopped there)")
    print("\nExamples:")
    for k in KINDS:
        ex = next((r["examples"][k] for r in runs if k in r["examples"]), None)
        if ex: print(f"  [{k}] {ex[:330]!r}")
    if out_path:
        json.dump([{**r, "calls": dict(r["calls"]), "bad": dict(r["bad"]), "agent_names": sorted(r.get("agent_names", ()))} for r in runs], open(out_path, "w"))


if __name__ == "__main__":
    main()
