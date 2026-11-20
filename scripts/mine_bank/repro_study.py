"""Direction 1 study: the model's own reproduce checks on the winnable core (user 2026-11-20: 'yes go deeper on direction 1').
Read-only: runs of data/analysis/failure_study.json with a requests log. A 'check' = a run_command that runs Python on the
model's own code (python3 - <<, python3 -c, cat > X.py + python3 X.py, python3 X.py; not pytest, not the edit heredoc). Per run:
  first check time; checks before the first edit; total checks;
  TARGET: the check calls a name the hidden test calls (the test's entry points, as in statement_content.py);
  SHOWN: a check's output shows a failure (Traceback / Error / assert) or the next reply says it reproduced the problem
         ('reproduced', 'confirms the bug', 'shows the bug', 'the bug is reproduced', 'fails as expected', 'we can see the issue');
  NOT SHOWN: the reply after a check says it works / no bug (as noedit_repro.py);
and the solve rate by these. Run: python3 -I scripts/mine_bank/repro_study.py"""
import ast, collections, json, re, statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
F = json.load(open(ROOT / "data/analysis/failure_study.json"))
T = {json.loads(l)["instance_id"]: json.loads(l) for l in open(ROOT / "data/tasks.jsonl")}
SKIP = set("""assert print len str int float dict list set tuple isinstance range repr type open sorted any all getattr setattr hasattr
super pytest raises mark parametrize fixture approx warns match get post put delete patch json""".split())


def calls(text):
    c = set(re.findall(r"\.(\w{3,})\(", text)) | set(re.findall(r"(?<![\w.])([A-Za-z_]\w{2,})\(", text))
    return {x for x in c if x not in SKIP and not x.startswith(("test", "_")) and not x.isupper()}


ENTRY = {i: calls("\n".join(l[1:] for l in t["test_patch"].splitlines() if l.startswith("+") and not l.startswith("+++"))) for i, t in T.items()}
CHECK = re.compile(r"python3? (- <<|-c |\S+\.py)|cat > \S+\.py <<")
SHOWN = re.compile(r"reproduc(ed|es) the (bug|issue|problem)|(issue|bug|problem) (is )?reproduced|confirms the (bug|issue|problem)|shows the (bug|issue|problem)|"
                   r"fails as expected|we can see the (issue|bug|problem)|successfully reproduced|the output (shows|confirms)", re.I)
NOBUG = re.compile(r"can(no|')t reproduce|not able to reproduce|did not reproduce|does(n't| not) reproduce|could(n't| not) reproduce|works correctly|"
                   r"works as expected|behaves as expected|no bug|seems to work|already (handled|works|correct)|bug is not (present|there)|not a bug", re.I)
logs = collections.defaultdict(list)
for d in {r["d"] for r in F}:
    p = ROOT / "data/results" / d / "requests/requests.jsonl"
    if p.exists():
        for l in open(p, errors="replace"):
            try:
                r = json.loads(l)
            except Exception:
                continue
            if len(r["request"]["messages"]) > 1:
                logs[(d, r["job"])].append(r)
rows = []
for f in F:
    rs = logs.get((f["d"], f"{f['iid']}#a{f['att']}"))
    if not rs:
        continue
    rs.sort(key=lambda x: float(x["t"]))
    t0 = float(rs[0]["t"])
    first_check = first_edit = shown_t = None
    n_checks = before_edit = nobug = 0
    target = False
    for i, x in enumerate(rs):
        try:
            m = ast.literal_eval(str(x["reply"])).get("message") or {}
        except Exception:
            continue
        words = (m.get("reasoning_content") or "") + " " + (m.get("content") or "")
        t = float(x["t"]) - t0
        if shown_t is None and SHOWN.search(words) and n_checks:
            shown_t = t
        nobug += bool(NOBUG.search(words)) and n_checks > 0
        for c in m.get("tool_calls") or []:
            try:
                a = json.loads(c["function"]["arguments"])
            except Exception:
                continue
            cmd = a.get("command", "") if c["function"]["name"] == "run_command" else ""
            if "OLD_TEXT" in cmd or c["function"]["name"] in ("edit_file", "write_file") and "test" not in str(a.get("filepath", "")) and "repro" not in str(a.get("filepath", "")):
                if first_edit is None:
                    first_edit = t
                continue
            if cmd and CHECK.search(cmd) and "pytest" not in cmd:
                n_checks += 1
                before_edit += first_edit is None
                if first_check is None:
                    first_check = t
                target |= bool(calls(cmd) & ENTRY[f["iid"]])
    rows.append(dict(ok=f["ok"], cls=f["cls"], iid=f["iid"], first_check=first_check, first_edit=first_edit, shown_t=shown_t, n_checks=n_checks,
                     before_edit=before_edit, target=target, nobug=nobug))


def rate(xs):
    return f"{100 * sum(x['ok'] for x in xs) / len(xs):3.0f}% of {len(xs):4}" if xs else "   - of    0"


print(f"winnable-core runs with a log: {len(rows)} (solved {sum(r['ok'] for r in rows)}) | tasks {len({r['iid'] for r in rows})}")
print(f"  ran >= 1 own check: {sum(r['n_checks'] > 0 for r in rows)} | checks per run median {st.median(r['n_checks'] for r in rows):.0f}")
print("\nsolve rate by what the model's own checks did:")
print(f"  never ran a check                         {rate([r for r in rows if not r['n_checks']])}")
print(f"  check calls what the hidden test calls    {rate([r for r in rows if r['n_checks'] and r['target']])}")
print(f"  check calls something else                {rate([r for r in rows if r['n_checks'] and not r['target']])}")
print(f"  says the check SHOWED the problem         {rate([r for r in rows if r['shown_t'] is not None])}")
print(f"  never says it showed the problem          {rate([r for r in rows if r['n_checks'] and r['shown_t'] is None])}")
print(f"  says 'works / no bug' after a check 0x    {rate([r for r in rows if r['n_checks'] and not r['nobug']])}")
print(f"  ... 1-2x                                  {rate([r for r in rows if 1 <= r['nobug'] <= 2])}")
print(f"  ... 3+x                                   {rate([r for r in rows if r['nobug'] >= 3])}")
print("\ncombined (target x shown):")
for tg in (True, False):
    for sh in (True, False):
        print(f"  target {str(tg):5} shown {str(sh):5}             {rate([r for r in rows if r['n_checks'] and r['target'] == tg and (r['shown_t'] is not None) == sh])}")
S = [r for r in rows if r["shown_t"] is not None]
print(f"\nwhen the problem was shown: at median {st.median(r['shown_t'] for r in S):.0f} s; edit followed in {sum(r['first_edit'] is not None for r in S)}/{len(S)}"
      f" | runs that never showed it: never edited {sum(r['first_edit'] is None for r in rows if r['n_checks'] and r['shown_t'] is None)}/{sum(1 for r in rows if r['n_checks'] and r['shown_t'] is None)}")
for name, grp in (("solved", [r for r in rows if r["ok"]]), ("never changed the source", [r for r in rows if not r["ok"] and r["cls"] == "no source edit"])):
    fc = [r["first_check"] for r in grp if r["first_check"] is not None]
    sh = [r["shown_t"] for r in grp if r["shown_t"] is not None]
    print(f"  {name:26} first check median {st.median(fc) if fc else 0:4.0f} s | showed the problem {100 * len(sh) / len(grp):3.0f}% at median {st.median(sh) if sh else 0:4.0f} s"
          f" | checks before the first edit / in total median {st.median(r['before_edit'] for r in grp):.0f} / {st.median(r['n_checks'] for r in grp):.0f}"
          f" | own check targets the test's entry {100 * sum(r['target'] for r in grp) / len(grp):3.0f}%")
json.dump(rows, open(ROOT / "data/analysis/repro_study.json", "w"))
