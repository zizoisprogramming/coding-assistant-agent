"""Build the solved-example library for evex_f / evex_m (r95, user 2026-11-13 "build these yes").
Run: python3 -I scripts/agent_exemplar/build_library.py [OUT.json]   (default scripts/agent_exemplar/examples.json)

Source: Gemma 4 31B's own solved runs from the October generation run (Kaggle dataset ziad23samer/cell-samples,
selfdistill/datasets_ziadsamer_gen-extra-all: requests_selfdistill.jsonl + metrics.jsonl, downloaded to
data/exemplars/raw/, gitignored). Kept: verdict 'keep' (resolved, submitted once, no repeats / junk / scratch files /
test-file edits, real-fix file hit), domain != 'public' (no competition repository: the 24 public-task runs are
dropped, and any repo of data/tasks.jsonl is dropped again by name), at most MAX_CALLS calls.

Each example is rendered without any reasoning: the issue's first lines, then every call with a few lines of its
result (read_file: the range only; edit_file: the old and new lines; run_command: the command and the first lines of
its output), then 'hidden tests: passed'. Examples longer than MAX_CHARS after rendering are dropped. Also stored per
example: the words used for matching (issue words + the edited files' and functions' names)."""
import ast
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data/exemplars/raw/selfdistill/datasets_ziadsamer_gen-extra-all")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "scripts/agent_exemplar/examples.json")
MAX_CALLS = 20
MAX_CHARS = 3000
CMD_MAX = 160
OUT_LINES = 3
EDIT_LINES = 8  # per side
ISSUE_LINES = 3
ISSUE_CHARS = 320


def parse(x):
    if isinstance(x, (list, dict)) or x is None:
        return x
    try:
        return json.loads(x)
    except Exception:
        return ast.literal_eval(x)


def text_of(c):
    if isinstance(c, list):
        return "\n".join(x.get("text", "") if isinstance(x, dict) else str(x) for x in c)
    return str(c)


def cut(s, n):
    s = " ".join(str(s).split()) if "\n" not in str(s) else str(s)
    return s if len(s) <= n else s[: n - 3] + "..."


def issue_head(text):
    body = text.split("Problem Statement:", 1)[-1].split("## Task Budget", 1)[0]
    lines = [l.strip() for l in body.splitlines()]
    lines = [l for l in lines if l and not l.startswith("<!--") and not l.startswith("@")]
    head = "\n".join("  " + l[:150] for l in lines[:ISSUE_LINES])
    return head[:ISSUE_CHARS], body


def result_lines(content, n=OUT_LINES):
    try:
        d = json.loads(content)
    except Exception:
        d = {"stdout": str(content)}
    if not isinstance(d, dict):
        d = {"stdout": str(d)}
    status = d.get("status", "")
    text = d.get("stdout") or d.get("output") or d.get("message") or d.get("error") or ""
    if not text and d.get("stderr"):
        text = d["stderr"]
    lines = [l.rstrip() for l in str(text).splitlines() if l.strip()]
    shown = ["   | " + l[:140] for l in lines[:n]]
    if len(lines) > n:
        shown.append(f"   | ... ({len(lines) - n} more lines)")
    return status, shown, d


def render_call(name, args, content):
    out = []
    if name == "run_command":
        cmd = str(args.get("command", "")).strip().splitlines() or [""]
        out.append(f"$ {cut(cmd[0], CMD_MAX)}" + (f"  [+{len(cmd) - 1} more lines]" if len(cmd) > 1 else ""))
        status, shown, d = result_lines(content)
        if d.get("exit_code") not in (None, 0):
            out.append(f"   (exit code {d.get('exit_code')})")
        out.extend(shown or ["   | (no output)"])
    elif name == "read_file":
        rng = ""
        if args.get("start_line") or args.get("end_line"):
            rng = f" lines {args.get('start_line', 1)}-{args.get('end_line', 'end')}"
        out.append(f"read_file {args.get('filepath') or args.get('path')}{rng}")
    elif name == "edit_file":
        out.append(f"edit_file {args.get('filepath') or args.get('path')}")
        old = str(args.get("old_string", args.get("old_str", ""))).splitlines()
        new = str(args.get("new_string", args.get("new_str", ""))).splitlines()
        a = 0  # drop the lines both sides share at the start and the end, keep one of each as context
        while a < min(len(old), len(new)) and old[a] == new[a]:
            a += 1
        b = 0
        while b < min(len(old), len(new)) - a and old[-1 - b] == new[-1 - b]:
            b += 1
        lo, hi = max(0, a - 1), max(0, b - 1)
        for sign, side in (("-", old[lo:len(old) - hi]), ("+", new[lo:len(new) - hi])):
            for l in side[:EDIT_LINES]:
                out.append(f"   {sign} {l[:140]}")
            if len(side) > EDIT_LINES:
                out.append(f"   {sign} ... ({len(side) - EDIT_LINES} more lines)")
        status, _, d = result_lines(content, 0)
        if status and status != "ok":
            out.append(f"   -> {status}: {cut(d.get('message') or d.get('error') or '', 120)}")
    elif name == "write_file":
        txt = str(args.get("content", ""))
        out.append(f"write_file {args.get('filepath') or args.get('path')} ({len(txt.splitlines())} lines)")
    elif name == "submit_patch":
        out.append("submit_patch")
    elif name == "get_status":
        return []
    else:
        out.append(f"{name} {cut(json.dumps(args), 100)}")
    return out


WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")
STOP = set("the a an and or of to in for on with by from is are be this that it as at not no when if into via use uses using "
           "add adds added fix fixes fixed update updates support make allow docs doc test tests issue self none true false "
           "return def class import should would could can will also".split())


def words(s):
    out = []
    for w in WORD.findall(s):
        for p in [w.lower()] + [x.lower() for x in re.split(r"_|(?<=[a-z])(?=[A-Z])", w) if len(x) > 2]:
            if p not in STOP:
                out.append(p)
    return out


def main():
    comp_repos = set()
    tp = os.path.join(ROOT, "data/tasks.jsonl")
    if os.path.exists(tp):
        for l in open(tp):
            t = json.loads(l)
            comp_repos.add(t.get("repo", "").split("/")[-1].lower())
    metrics = [json.loads(l) for l in open(os.path.join(RAW, "metrics.jsonl"))]
    keep = {m["instance_id"] + "#a" + str(m["attempt"]): m for m in metrics
            if m["verdict"] == "keep" and m["domain"] != "public" and m["calls"] <= MAX_CALLS}
    last = {}
    for l in open(os.path.join(RAW, "requests_selfdistill.jsonl")):
        r = json.loads(l)
        if r["job"] in keep and (r["job"] not in last or len(r["request"]["messages"]) > len(last[r["job"]]["request"]["messages"])):
            last[r["job"]] = r
    lib, dropped = [], {"competition repo": 0, "too long": 0, "no edit": 0}
    for job, r in sorted(last.items()):
        msgs = r["request"]["messages"]
        user = next(m for m in msgs if m["role"] == "user")
        utext = text_of(user["content"])
        repo_line = re.search(r"for repository (\S+?)\.\n", utext)
        repo = repo_line.group(1) if repo_line else job.split("__")[0]
        if repo.split("/")[-1].lower() in comp_repos:
            dropped["competition repo"] += 1
            continue
        head, body = issue_head(utext)
        results = {m.get("tool_call_id"): text_of(m.get("content", "")) for m in msgs if m["role"] == "tool"}
        calls, edited, ident = [], [], []
        seq = [m for m in msgs if m["role"] == "assistant"]
        reply = parse(r["reply"]) or {}
        final = (reply.get("message") or {}) if isinstance(reply, dict) else {}
        if final.get("tool_calls"):
            seq.append({"role": "assistant", "tool_calls": final["tool_calls"]})
        n = 0
        for m in seq:
            for tc in parse(m.get("tool_calls")) or []:
                fn = tc["function"]["name"]
                args = parse(tc["function"].get("arguments")) or {}
                lines = render_call(fn, args, results.get(tc.get("id"), ""))
                if not lines:
                    continue
                n += 1
                calls.append(f"{n:>2}. " + lines[0])
                calls.extend("    " + l for l in lines[1:])
                if fn in ("edit_file", "write_file"):
                    p = args.get("filepath") or args.get("path") or ""
                    edited.append(p)
                    ident += WORD.findall(str(args.get("new_string", "")))[:20]
        if not edited:
            dropped["no edit"] += 1
            continue
        text = (f"A SOLVED EXAMPLE FROM ANOTHER REPOSITORY ({repo}). It is not about this repository and it is not evidence; "
                f"it shows how a run that passed the hidden tests went, call by call.\n"
                f"Its issue:\n{head}\nIts calls:\n" + "\n".join(calls) + "\nResult: the hidden tests passed.")
        if len(text) > MAX_CHARS:
            dropped["too long"] += 1
            continue
        lib.append({"job": job, "repo": repo, "calls": n, "chars": len(text), "text": text,
                    "words": sorted(set(words(body) + words(" ".join(edited)) + words(" ".join(ident))))})
    json.dump(lib, open(OUT, "w"), indent=1)
    print(f"kept {len(lib)} examples from {len(last)} runs; dropped {dropped}; chars median "
          f"{sorted(x['chars'] for x in lib)[len(lib) // 2] if lib else 0}; wrote {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main()
