"""r122: sb1h vs sbG (time-aware history-first gate) on 4 tasks; only engziadsamer/arms-again ran it (1 pass: 4 + 4 runs;
the other notebook's latest version is still r121's). Bars in docs/PLAN.md RUN BUILT r122.
Run: python3 -I scripts/mine_bank/r122.py
1. outcomes, ends, agent s, compactions, runs changing an existing source file;
2. sbG holds: each '== NOT EDITED YET' result, its commits (useful by 'DATE TITLE' labels), the next reply's words and call
   (a resend with the same / changed new text, the apply command, something else), and whether that function got an edit;
   every hold printed for hand reading."""
import ast, collections, glob, json, re, statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRS = sorted(glob.glob(str(ROOT / "data/results/2026-11-20_skill_r122_p*")))
ARMS = ("sb1h", "sbG")
HOLD = "== NOT EDITED YET"
LAB = json.loads((ROOT / "scripts/mine_bank/hist_useful_commits.json").read_text())
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")
HEREDOC = re.compile(r"cat > \.git/agent/old <<'OLD_TEXT'\n(.*?)OLD_TEXT\ncat > \.git/agent/new <<'NEW_TEXT'\n(.*?)NEW_TEXT\n", re.S)

print("#### 1. outcomes")
G = []
for d in DIRS:
    for l in open(f"{d}/results/gen_per_task.jsonl"):
        g = json.loads(l)
        g["p"] = d[-2:]
        G.append(g)
src = {}
for d in DIRS:
    for f in glob.glob(f"{d}/results/gen/patches/*.diff"):
        name = Path(f).name[:-len(".1.diff")]
        iid, arm = name.rsplit("__a", 1)
        t = open(f, errors="replace").read()
        files = re.findall(r"^diff --git a/(\S+) b/", t, re.M)
        new = set(re.findall(r"^diff --git a/(\S+) b/\S+\nnew file", t, re.M))
        src[(d[-2:], iid, arm)] = any(x.endswith(".py") and not TEST.search(x) and x not in new for x in files)
R = collections.defaultdict(list)
comp = collections.Counter()
for d in DIRS:
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        r = json.loads(l)
        arm = r["job"].split("#a")[1].split(".")[0]
        if len(r["request"]["messages"]) == 1:
            comp[arm] += 1
            continue
        R[(d[-2:], r["job"])].append(r)
for a in ARMS:
    A = [g for g in G if g["arm"] == a]
    print(f"  {a:5} runs {len(A)} | solved {sum(g['resolved'] in (True, 'True') for g in A)} | ends {dict(collections.Counter(g['end'] for g in A))}"
          f" | agent s mean {st.mean(g['agent_s'] for g in A):.0f} | tool calls mean {st.mean(g['tool_calls'] for g in A):.1f}"
          f" | compactions {comp[a]} ({comp[a] / len(A):.1f}/run) | changed an existing source file {sum(src.get((g['p'], g['instance_id'], a), False) for g in A)}"
          f" | no patch {sum(not g['patch_chars'] for g in A)}")
for t in sorted({g["instance_id"] for g in G}):
    print("   ", t[:30].ljust(30), " | ".join(f"{a} " + "".join(("S" if g["resolved"] in (True, "True") else ("E" if src.get((g['p'], t, a)) else "-")) for g in G if g["instance_id"] == t and g["arm"] == a) for a in ARMS))


def reply(r):
    try:
        m = ast.literal_eval(str(r["reply"])).get("message") or {}
    except Exception:
        m = {}
    calls = []
    for c in m.get("tool_calls") or []:
        try:
            calls.append((c["function"]["name"], json.loads(c["function"]["arguments"])))
        except Exception:
            calls.append((c["function"]["name"], {}))
    return ((m.get("reasoning_content") or "") + "\n" + (m.get("content") or "")).strip(), calls


print("\n#### 2. sbG holds")
nh = 0
kinds = collections.Counter()
for (p, job), rs in sorted(R.items()):
    if "#asbG." not in job:
        continue
    rs.sort(key=lambda r: float(r["t"]))
    t0 = float(rs[0]["t"])
    iid = job.split("#")[0]
    use = set(LAB.get(iid, {}).get("useful_titles", []))
    last_new = None
    edits = applied = 0
    for i, r in enumerate(rs):
        words, calls = reply(r)
        for n, a in calls:
            m = HEREDOC.search(a.get("command", "")) if n == "run_command" else None
            if m:
                last_new = m.group(2)
                edits += 1
        res = rs[i + 1]["request"]["messages"][-1] if i + 1 < len(rs) else {}
        t = str(res.get("content")).replace("\\n", "\n").replace('\\"', '"') if res.get("role") == "tool" else ""
        applied += bool(re.search(r"(?m)^EDITED ", t))
        if HOLD not in t:
            continue
        nh += 1
        held_new = last_new
        hist = t[t.find(HOLD):]
        titles = [(d + " " + s.strip())[:121] for d, s in re.findall(r"^commit [0-9a-f]{7,} (\S+) (.*)$", hist, re.M)]
        u = [x for x in titles if x in use]
        w2, c2 = reply(rs[i + 1]) if i + 1 < len(rs) else ("", [])
        kind = "other"
        for n, a in c2:
            cmd = a.get("command", "")
            if n == "run_command" and re.fullmatch(r"\s*python3 \.git/agent/step\.py \S+\s*", cmd):
                kind = "apply as it is"
            elif n == "run_command" and HEREDOC.search(cmd):
                kind = "resend, same new text" if HEREDOC.search(cmd).group(2) == held_new else "resend, CHANGED new text"
        kinds[kind] += 1
        print(f"\n  ## {p} {iid} | hold at {float(r['t']) + float(r.get('seconds') or 0) - t0:.0f} s | useful commit shown: {u or '-'} | next: {kind}")
        print("  HELD OUTPUT:\n" + "\n".join("    " + l for l in hist[:1600].splitlines()))
        print("  NEXT REPLY WORDS:\n" + "\n".join("    " + l for l in w2[:1200].splitlines()))
        print("  NEXT CALLS:", [(n, (a.get("command") or json.dumps(a))[:300]) for n, a in c2])
        if kind == "resend, CHANGED new text":
            print("  HELD NEW TEXT:\n" + "\n".join("    " + l for l in (held_new or "").splitlines()))
            print("  RESENT NEW TEXT:\n" + "\n".join("    " + l for l in HEREDOC.search([a for n, a in c2 if n == 'run_command'][0]["command"]).group(2).splitlines()))
    print(f"  run {p} {iid}: heredoc edits {edits}, EDITED results {applied}")
print(f"\n  holds {nh} | next call after a hold: {dict(kinds)}")
