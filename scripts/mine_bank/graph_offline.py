"""Do call-graph neighbours reach the real fix's function? (2026-11-12, offline check before the evgraph arm.)
Run: python3 -I scripts/mine_bank/graph_offline.py SNAPSHOT_DIR [SNAPSHOT_DIR ...]

Per public task whose base is found in a local snapshot: names = the real evidence stage's choice (bank logs) or
code-like names from the issue that the source contains (file_map_offline.repo_names). The r86 evidence script runs at
the base twice, GRAPH off and on (otherwise identical). 'Names the real fn' = a 'path:line' in the output inside the
innermost def around a real-fix line, or a 'path:first-last' that is exactly that def's range. Reported:
GRAPH off vs on, how many tasks only the graph reaches, the graph lines' size, and the time."""
import importlib.util, json, os, re, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))


def mod(name, file):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, file))
    m = importlib.util.module_from_spec(spec)
    old = sys.argv
    sys.argv = [old[0], "/dev/null"]
    try:
        spec.loader.exec_module(m)
    finally:
        sys.argv = old
    return m


fla = mod("fla", "fix_line_age.py")
ep = mod("ep", "edit_place.py")
eo = mod("eo", "evidence_offline.py")
fmo = mod("fmo", "file_map_offline.py")
T = {json.loads(l)["instance_id"]: json.loads(l) for l in open("data/tasks.jsonl")}
SRC = open("scripts/agent_evidence/evidence_r86.py").read()


def variant(graph):
    s = re.sub(r"^GRAPH = \S+", f"GRAPH = {graph!r}", SRC, count=1, flags=re.M)
    f = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, dir=tempfile.gettempdir())
    f.write(s); f.close()
    return f.name


def points_inside(out, gold_lines, gold_fns):
    """True if OUT names the real fn: a 'path:line' inside one of its spans, or a 'path:first-last' that IS one of them
    (the same rule for single lines and ranges, so a wide class range does not count)."""
    for f in gold_lines:
        spans = gold_fns.get(f, set())
        for m in re.finditer(rf"{re.escape(f)}:(\d+)(?:-(\d+))?", out):
            a = int(m.group(1))
            if m.group(2):
                if any(s[0] == a and s[1] == int(m.group(2)) for s in spans):
                    return True
            elif any(s[0] <= a <= s[1] for s in spans):
                return True
    return False


def main(dirs):
    snap = fla.snapshots(dirs)
    real = eo.stage_names()
    off_s, on_s = variant(False), variant(True)
    rows = []
    for iid, t in sorted(T.items()):
        repo = iid.split("_")[0]
        if repo not in snap:
            continue
        top, _, tip = snap[repo]
        base = fla.find_base(top, t, tip)
        if not base:
            continue
        ch = {f: v for f, v in ep.changed_lines(t).items() if f.endswith(".py")}
        gold_fns = {}
        for f, lines in ch.items():
            sp = fmo.spans(fla.git(top, "show", f"{base}:{f}"))
            gold_fns[f] = {fmo.innermost(sp, x) for x in lines} - {None}
        if not any(gold_fns.values()):
            continue
        names = [n.rsplit(".", 1)[-1] for n in (real.get(iid) or fmo.repo_names(top, base, t)) if re.fullmatch(r"[A-Za-z_][\w.]*", n)]
        if not names:
            continue
        outs = {}
        for lab, sc in (("off", off_s), ("on", on_s)):
            subprocess.run(["git", "-C", top, "checkout", "-q", "-f", base], capture_output=True)
            subprocess.run(["rm", "-rf", os.path.join(top, ".git", "agent")], capture_output=True)
            t0 = time.time()
            r = subprocess.run([sys.executable, "-I", sc, *names], cwd=top, capture_output=True, text=True, errors="replace", timeout=60)
            outs[lab] = (r.stdout, time.time() - t0, r.returncode)
        gl = [l for l in outs["on"][0].splitlines() if l.startswith(("called from:", "it calls:"))]
        row = dict(iid=iid, real=iid in real, names=names, off=points_inside(outs["off"][0], ch, gold_fns), on=points_inside(outs["on"][0], ch, gold_fns),
                   glines=len(gl), gchars=sum(len(l) for l in gl), t_on=outs["on"][1], rc=outs["on"][2], deep=min(min(v) for v in ch.values()) > 150)
        rows.append(row)
        print(f"{iid:15s} {'(stage)' if row['real'] else '(issue)'} {names} | evidence inside real fn: without graph {'Y' if row['off'] else '-'}, with graph {'Y' if row['on'] else '-'} "
              f"| graph lines {row['glines']} ({row['gchars']} chars) | {row['t_on']:.1f} s rc {row['rc']}", flush=True)
    for top, _, tip in snap.values():
        subprocess.run(["git", "-C", top, "checkout", "-q", "-f", tip], capture_output=True)
    for lab, g in (("all", rows), ("real stage names", [r for r in rows if r["real"]]), ("real-fix lines past line 150", [r for r in rows if r["deep"]])):
        if g:
            n = len(g)
            print(f"{lab:30s} tasks {n:3d} | inside real fn: without graph {sum(r['off'] for r in g)} ({100 * sum(r['off'] for r in g) / n:.0f}%), "
                  f"with graph {sum(r['on'] for r in g)} ({100 * sum(r['on'] for r in g) / n:.0f}%), only with graph {sum(r['on'] and not r['off'] for r in g)} "
                  f"| crashes {sum(r['rc'] != 0 for r in g)} | max time {max(r['t_on'] for r in g):.1f} s | median graph chars {sorted(r['gchars'] for r in g)[n // 2]}")
    os.unlink(off_s); os.unlink(on_s)


if __name__ == "__main__":
    main(sys.argv[1:])
