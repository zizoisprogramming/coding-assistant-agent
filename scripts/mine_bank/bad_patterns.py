"""The shape of each bad tool call (MINING 2026-11-11e): what exactly goes wrong, to judge what a few-shot example could fix.
Usage: python3 -I scripts/mine_bank/bad_patterns.py   (repo root; 31B runs, all folders with request logs)

Per kind:
  garbled_args    which argument went missing, the argument order, how the swallowing string ended (backtick?), escaped
                  newlines in the text, length, finish_reason, resent identically next?
  edit_nomatch    old_string vs earlier tool outputs in the same run: verbatim there (stale: the file was edited since),
                  equal after whitespace normalisation, carrying line-number prefixes, or found nowhere (from memory)
  read_range      start / end values (end = start - 1, end looks like a count, other)
  inline_py_syntax  the command form (python -c with nested quotes / f-string escapes / multi-line, heredoc, other)
  tool_as_shell   which tool name was typed into the shell
  write_outside   the path and what the file was (test / repro script)
  text_call       finish_reason (cut at max tokens?), tool written, length
  after_budget    which tool, and whether it was the run's first edit"""
import collections, glob, importlib.util, json, os, re

spec = importlib.util.spec_from_file_location("bc", os.path.join(os.path.dirname(os.path.abspath(__file__)), "bad_calls.py"))
bc = importlib.util.module_from_spec(spec); spec.loader.exec_module(bc)
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")
F = collections.defaultdict(collections.Counter)  # kind -> feature counter
N = collections.Counter(); EX = collections.defaultdict(list)


def ws(x):
    return re.sub(r"\s+", " ", x).strip()


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
        q.sort(key=lambda r: r["t"])
        seen_out = []  # earlier tool outputs (flattened) in this run, with the index of the call
        edits_ok = collections.defaultdict(list)  # file -> call indices of successful edits
        prev_raw = None; i = 0; worked = False
        for r in q:
            msg = r["reply"]["message"]; calls = msg.get("tool_calls") or []; fin = r["reply"].get("finish_reason")
            toks = (r["reply"].get("usage") or {}).get("completion_tokens") or 0
            maxt = (r["request"].get("kwargs") or {}).get("max_completion_tokens") or 0
            if not calls:
                txt = str(msg.get("content") or "")
                if bc.TEXT_CALL.search(txt):
                    N["text_call"] += 1; f = F["text_call"]
                    f[f"finish_reason={fin}"] += 1
                    f["completion tokens >= 95% of max"] += bool(maxt and toks >= 0.95 * maxt)
                    m = re.search(r"call:(\w+)|(edit_file|run_command|read_file|write_file|submit_patch|run_skill_script)\s*[({]", txt)
                    f["tool " + (m.group(1) or m.group(2) if m else "?")] += 1
                    f["text length > 4000 chars"] += len(txt) > 4000
                    f["closing <tool_call|> token present"] += "<tool_call|>" in txt
                    if len(EX["text_call"]) < 3: EX["text_call"].append(f"fin={fin} toks={toks}/{maxt} | {txt[:160]!r} ... {txt[-120:]!r}")
                continue
            for c in calls:
                i += 1
                name = c["function"]["name"]; raw = c["function"].get("arguments") or ""; res = res_of.get(c.get("id"), "")
                try: a = json.loads(raw)
                except Exception: a = {}
                k = bc.kind_of(name, raw, res, "")
                fp = str(a.get("filepath") or "")
                if k == "garbled_args":
                    N[k] += 1; f = F[k]
                    missing = re.findall(r"present:\\n(\w+)|present:\n(\w+)", res)
                    miss = [x for t in missing for x in t if x] or re.findall(r"\b(old_string|new_string|filepath|content)\b", res.split("present", 1)[-1][:80])
                    f["missing " + "+".join(sorted(set(miss))[:2] or ["?"])] += 1
                    f["first key " + (list(a)[0] if a else "?")] += 1
                    f["extra keys (args swallowed into a name)"] += any(x not in ("filepath", "old_string", "new_string", "content") for x in a)
                    vals = [v for v in a.values() if isinstance(v, str)]
                    f["a string value contains a backtick followed by comma/name (`,)"] += any(re.search(r"`\s*,\s*\w+\s*:", v) for v in vals)
                    f["a string value ends with a backtick"] += any(v.rstrip().endswith("`") for v in vals)
                    f["text has escaped \\n (backslash-n instead of newline)"] += any("\\n" in v for v in vals)
                    f["args > 1500 chars"] += len(raw) > 1500
                    f[f"finish_reason={fin}"] += 1
                    f["same call resent next"] += 0  # filled below
                    if prev_raw == raw: f["identical to the previous call"] += 1
                    if len(EX[k]) < 3: EX[k].append(raw[:260])
                elif k == "edit_nomatch":
                    N[k] += 1; f = F[k]; old = str(a.get("old_string") or "")
                    if not old.strip():
                        f["old_string empty"] += 1
                    else:
                        verb = [j for j, o in seen_out if old in o]
                        if verb:
                            stale = any(e > verb[-1] for e in edits_ok.get(fp, []))
                            f["verbatim in an earlier output, file edited since (stale)" if stale else "verbatim in an earlier output, file not edited since (other file? path?)"] += 1
                        elif re.search(r"(^|\n)\s*\d+[:|]\s", old) or re.search(r"(^|\n)\s*\d+\t", old):
                            f["carries line-number prefixes (copied from numbered output)"] += 1
                        elif any(ws(old) in ws(o) for _, o in seen_out[-40:]):
                            f["only whitespace / indentation differs"] += 1
                        elif any(ws(old.splitlines()[0]) in ws(o) for _, o in seen_out[-40:] if old.splitlines() and len(ws(old.splitlines()[0])) > 10):
                            f["first line seen, later lines differ (from memory / paraphrased)"] += 1
                        else:
                            f["found nowhere in earlier outputs (from memory)"] += 1
                    f["old_string > 15 lines"] += old.count("\n") >= 15
                    if len(EX[k]) < 2: EX[k].append(old[:200])
                elif k == "read_range":
                    N[k] += 1; f = F[k]
                    s_, e_ = a.get("start_line"), a.get("end_line")
                    try: s_, e_ = int(s_), int(e_)
                    except Exception: s_ = e_ = None
                    if s_ is None: f["non-integer lines"] += 1
                    elif e_ == s_ - 1: f["end = start - 1"] += 1
                    elif e_ < s_ and e_ <= 200 and s_ > e_ * 2: f["end looks like a line COUNT (end < start / 2)"] += 1
                    elif e_ < s_: f["end < start, other"] += 1
                    else: f["start beyond file end / other ValueError"] += 1
                    if len(EX[k]) < 3: EX[k].append(f"{s_}-{e_} {res[:120]}")
                elif k == "inline_py_syntax":
                    N[k] += 1; f = F[k]; cmd = str(a.get("command") or raw)
                    if "<<" in cmd: f["heredoc"] += 1
                    elif re.search(r"python3? -c", cmd):
                        body = cmd.split("-c", 1)[1]
                        f["python -c"] += 1
                        f["  with f-string"] += bool(re.search(r"\bf['\"]", body))
                        f["  with escaped quotes inside (\\' or \\\")"] += ("\\'" in body or '\\"' in body)
                        f["  multi-line (newline or ; with block)"] += ("\n" in body or bool(re.search(r";\s*(for|if|with|def|class|try)\b", body)))
                    else: f["other form"] += 1
                    err = re.search(r"(SyntaxError|IndentationError)[^\\\n]{0,60}", bc.flat(res))
                    f["error: " + (err.group(0)[:50] if err else "?")] += 1
                    if len(EX[k]) < 3: EX[k].append(cmd[:200])
                elif k == "tool_as_shell":
                    N[k] += 1; m = re.search(r"\b(read_file|edit_file|write_file|submit_patch|get_status|run_command): command not found", res)
                    F[k]["typed " + (m.group(1) if m else "?")] += 1
                    if len(EX[k]) < 3: EX[k].append(str(a.get("command") or raw)[:160])
                elif k == "write_outside":
                    N[k] += 1; f = F[k]
                    f["path in /tmp" if fp.startswith("/tmp") else "other path"] += 1
                    f["a test or repro script" if re.search(r"test|repro|check|debug|verify", fp, re.I) else "other file"] += 1
                    f["model wrote write_file again after the refusal"] += 0
                elif k == "after_budget":
                    N[k] += 1; f = F[k]
                    f["tool " + name] += 1
                    if name in ("edit_file", "write_file"): f["  an edit, with no working edit before (the run's first)" if not worked else "  an edit, after a working edit"] += 1
                if name in ("edit_file", "write_file") and '"status": "ok"' in res[:30] and fp and not TEST.search(fp):
                    edits_ok[fp].append(i); worked = True
                prev_raw = raw
                if res:
                    seen_out.append((i, bc.flat(res)))

for k in ("garbled_args", "edit_nomatch", "read_range", "inline_py_syntax", "tool_as_shell", "write_outside", "text_call", "after_budget"):
    print(f"\n== {k}: {N[k]} calls")
    for feat, v in F[k].most_common():
        if v: print(f"   {v:5d} ({v / max(1, N[k]):5.1%})  {feat}")
    for e in EX[k]: print(f"   e.g. {e!r}"[:300])
