"""Per-task behaviour profile from traces: tool mix, output tokens per step, step time, reads/searches before the
first edit, read sizes, test runs, scratch scripts, failed calls, repeated submits.

    python3 scripts/behaviour.py data/results/<run>/<config> [...]
"""
import ast, glob, json, os, re, statistics, sys


def _d(v):
    return ast.literal_eval(v) if isinstance(v, str) else (v or {})


def is_edit(tc):
    return ("'edit_file'" in tc or "sed -i" in tc or ".write(s.replace" in tc
            or ("'write_file'" in tc and "/tmp" not in tc and "test" not in tc.lower()))


def main():
    for d in sys.argv[1:]:
        for f in sorted(glob.glob(d + "/traces/*.json")):
            steps = [x for x in json.load(open(f))["steps"] if x.get("source") == "agent"]
            n = len(steps)
            out = [(_d(x.get("metrics")).get("completion_tokens") or 0) for x in steps]
            tcs = [str(x.get("tool_calls") or "") for x in steps]
            obs = [str(x.get("observation") or "") for x in steps]
            mix = {}
            for tc in tcs:
                m = re.search(r"'function_name': '(\w+)'", tc)
                if m:
                    mix[m.group(1)] = mix.get(m.group(1), 0) + 1
            first = next((i for i, tc in enumerate(tcs) if is_edit(tc)), None)
            pre = tcs[:first] if first is not None else tcs
            reads = sum("'read_file'" in t or "sed -n" in t or "cat -n" in t for t in pre)
            searches = sum("grep" in t for t in pre)
            spans = [int(b) - int(a) for a, b in re.findall(r"'end_line': (\d+), 'filepath': '[^']+', 'start_line': (\d+)", ' '.join(tcs))]
            spans = [-s for s in spans]  # (end, start) order in the dicts
            spans += [int(b) - int(a) for a, b in re.findall(r"'start_line': (\d+), 'end_line': (\d+)", ' '.join(tcs))]
            tests = sum("pytest" in t for t in tcs)
            scripts = sum(("cat > /tmp" in t or "python3 - <<" in t or "python - <<" in t or "python3 -c" in t) for t in tcs)
            failed = sum('"status": "error"' in o for o in obs)
            submits = mix.get("submit_patch", 0)
            print(f"{os.path.basename(d):13} {f.split('trace_')[1][:-5]:14} steps {n:3} out/step {statistics.mean(out):5.0f} "
                  f"edit@step {first if first is not None else '—':>3} pre-edit reads {reads:2} greps {searches:2} "
                  f"read span med {statistics.median(spans) if spans else 0:4.0f} tests {tests:2} scripts {scripts:2} "
                  f"failed {failed:2} submits {submits:2}  mix {dict(sorted(mix.items(), key=lambda kv: -kv[1]))}")


if __name__ == "__main__":
    main()
