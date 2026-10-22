"""Assembly decisions for the final SWE-rebench task set, made locally from the builds' small files (reviewable before
any Kaggle time): which tasks, which text each one shows, and their labels. Writes data/rebench_final/selection.json,
which the offline verification notebook (make_rebench_verify_cells.py) embeds and applies.

    .venv/bin/python scripts/datasets/assemble_rebench.py           # training set -> data/rebench_final/
    .venv/bin/python scripts/datasets/assemble_rebench.py --test    # test set (repos in no training source) -> data/rebench_test/

Sources (usable = gold PASS + empty FAIL; the full builds also need gold to pass 3 times): pilot 2, full part 1,
part 1b, part 2. Decisions (user 2026-10-20):
  domains   80% public-like / 20% other: every public-like task is kept, other tasks are sampled (one per repo first)
            down to a quarter of the public-like count. Domains are re-classified with the fixed classifier (part 1 ran
            the first one) from each repo's GitHub topics/description (repos.jsonl; the pilot's repos are fetched here).
  text      each task shows its issue text or its PR text (title + description). Chosen together so the set matches the
            public tasks on three shares: leaking texts 34% (OOD-45 checker), PR-style texts 57%, unfair tests 12%
            (unfair_tests.unfair_names: the tests need a name the fix creates and the text never mentions), and
            short texts (< 80 characters once "Fixes #12" lines and template comments are removed; public: 15/129).
            A PR text needs >= 40 characters and a non-release title to be an option.
"""
import collections
import json
import random
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/datasets"))
import make_rebench_full_cells as M  # noqa: E402
from unfair_tests import unfair_names  # noqa: E402

RES = ROOT / "data/results"
SOURCES = {"pilot": RES / "2026-10-21_rebench_pilot2", "1": RES / "2026-10-21_rebench_full_new-data",
           "1b": RES / "2026-10-21_rebench_full_p1b", "2": RES / "2026-10-21_rebench_full_p2"}
OUT = ROOT / "data/rebench_final"
TARGET = {"leak": 0.34, "pr": 0.57, "unfair": 0.12}  # "short" is added from the public set in main()
MIN_PR_CHARS = 40
SHORT_CHARS = 80
RELEASE_RE = re.compile(r"\b(release|bump|version \d|v\d+\.\d+|changelog|merge (branch|pull))\b", re.I)
SEED = 20261022

_ns = {"re": re}
exec(M.CELL2B[M.CELL2B.index("DOMAINS = {"):M.CELL2B.index("REPO_LOG =")], _ns)
domain_of = _ns["domain_of"]


def repo_infos(repos):
    info = {}
    for src in SOURCES.values():
        p = src / "rebench/repos.jsonl"
        if p.exists():
            info.update({json.loads(l)["repo"]: json.loads(l)["info"] for l in open(p)})
    cache = ROOT / "data/swe_rebench/repo_info_extra.jsonl"
    if cache.exists():
        info.update({json.loads(l)["repo"]: json.loads(l)["info"] for l in open(cache)})
    for repo in sorted(set(repos) - set(info)):  # the pilot's repos: unauthenticated GitHub (60/hour is enough)
        try:
            req = urllib.request.Request(f"https://api.github.com/repos/{repo}", headers={"Accept": "application/vnd.github+json"})
            d = json.load(urllib.request.urlopen(req, timeout=30))
            got = {k: d.get(k) for k in ("full_name", "description", "topics", "archived", "fork")}
            if d.get("fork") and d.get("source"):
                got["topics"], got["description"] = d["source"].get("topics"), d["source"].get("description") or got["description"]
        except Exception as e:
            got = {"missing": True, "error": f"{type(e).__name__}: {e}"[:120]}
        info[repo] = got
        with open(cache, "a") as fh:
            fh.write(json.dumps({"repo": repo, "info": got}) + "\n")
        time.sleep(1)
    return info


def load():
    cand = {json.loads(l)["instance_id"]: json.loads(l) for l in open(ROOT / "data/swe_rebench/candidates.jsonl")}
    pilot_leak = json.load(open(SOURCES["pilot"] / "leakage.json"))
    pilot_env = collections.defaultdict(bool)
    for l in open(SOURCES["pilot"] / "gate_env_install.jsonl"):
        r = json.loads(l)
        pilot_env[r["repo"]] |= bool(r["editable"]) and r["editable"][-1]["exit"] != 0
    rows = []
    for src, d in SOURCES.items():
        if src != "pilot":
            assert str(json.load(open(d / "rebench/part.json"))["part"]) == src, (src, d)
        for l in open(d / "rebench/tasks.jsonl"):
            t = json.loads(l)
            if not t["gate"].get("usable"):
                continue
            c = cand[t["instance_id"]]
            diff = c["meta"]["llm_score"]["difficulty_score"]
            rows.append({
                "id": t["instance_id"], "source": src, "repo": t["repo"], "row": t,
                "level": t.get("level") or ("large" if c["tier"] == "large" else f"core d{diff}"), "difficulty": diff,
                "leak_issue": (t.get("leak") or {}).get("issue") if src != "pilot" else pilot_leak["issue"].get(t["instance_id"], []),
                "leak_pr": (t.get("leak") or {}).get("pr") if src != "pilot" else pilot_leak["pr"].get(t["instance_id"]),
                "env_partial": bool(t.get("env_partial")) if src != "pilot" else pilot_env[t["repo"]],
            })
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids)), "a task appears in two sources"
    return rows


def substance(text):
    """The text minus what the agent cannot use: issue/URL references (Fixes #12) and HTML comments (PR templates)."""
    t = re.sub(r"<!--.*?-->", "", text or "", flags=re.S)
    t = re.sub(r"(?im)^\s*(fix(es|ed)?|close[sd]?|resolve[sd]?|refs?|see|related to)\s*:?\s*(#\d+|https?://\S+)[\s,.]*$", "", t)
    return t.strip()


def is_short(text):
    return len(substance(text)) < SHORT_CHARS


def choose_texts(sel, rng):
    """Local search over each task's text (issue or PR) so the shares of leaking, PR-style and unfair texts match the
    public targets. Objective = sum of |count - target count|."""
    for r in sel:
        t = r["row"]
        opts = [("issue", t["problem_statement"], bool(r["leak_issue"]))]
        if (t.get("pr") and len((t["pr"]["text"] or "").strip()) >= MIN_PR_CHARS and r["leak_pr"] is not None
                and not RELEASE_RE.search(t["pr"]["title"] or "")):  # a release PR's text is a changelog, not a task
            opts.append(("pr", t["pr"]["text"], bool(r["leak_pr"])))
        r["opts"] = [{"kind": k, "leak": lk, "unfair": unfair_names(t["patch"], t["test_patch"], txt), "short": is_short(txt)}
                     for k, txt, lk in opts]
        r["pick"] = rng.randrange(len(r["opts"]))
    n = len(sel)
    want = {k: round(v * n) for k, v in TARGET.items()}

    def counts():
        c = collections.Counter()
        for r in sel:
            o = r["opts"][r["pick"]]
            c["leak"] += o["leak"]
            c["pr"] += o["kind"] == "pr"
            c["unfair"] += bool(o["unfair"])
            c["short"] += o["short"]
        return c

    def cost(c):
        return sum(abs(c[k] - want[k]) for k in want)

    cur = counts()
    best = cost(cur)
    flex = [r for r in sel if len(r["opts"]) > 1]
    for _ in range(50000):
        if best == 0:
            break
        r = rng.choice(flex)
        old = r["pick"]
        r["pick"] = 1 - old
        c = counts()
        if cost(c) <= best:
            best, cur = cost(c), c
        else:
            r["pick"] = old
    return cur, want


def test_rows(rows, pub):
    """The TEST set (user 2026-10-22): every usable built task whose repo is in no training source: not in the final
    training set (data/results/2026-10-21_rebench_verify), not OOD-45's 17 repos, not the public tasks' 4. Tasks the
    offline verification already dropped (network tests, failed installs) stay out. No domain trim: all of them."""
    final = [json.loads(l) for l in open(RES / "2026-10-21_rebench_verify/rebench/tasks.jsonl")]
    dropped = json.load(open(RES / "2026-10-21_rebench_verify/rebench/dropped.json"))
    banned = {t["repo"] for t in final} | OOD45_REPOS | {t["repo"] for t in pub}
    return [r for r in rows if r["repo"] not in banned and r["id"] not in dropped]


# OOD-45's repos (rodrigospalma/ood45-bugfix-split; urllib3 is its 17th, skipped by our runner), training data now.
OOD45_REPOS = {"apache/iceberg-python", "caronc/apprise", "feast-dev/feast", "fsspec/filesystem_spec", "has2k1/plotnine",
               "hgrecco/pint", "kedro-org/kedro", "kedro-org/kedro-viz", "pdm-project/pdm", "pola-rs/polars",
               "posit-dev/great-tables", "posit-dev/py-shiny", "pyjanitor-devs/pyjanitor", "tkem/cachetools",
               "tox-dev/tox", "wntrblm/nox", "urllib3/urllib3"}


def main():
    test = "--test" in sys.argv
    out_dir = ROOT / "data/rebench_test" if test else OUT
    rng = random.Random(SEED)
    pub = [json.loads(l) for l in open(ROOT / "data/tasks.jsonl")]
    TARGET["short"] = sum(is_short(t["problem_statement"]) for t in pub) / len(pub)
    rows = load()
    info = repo_infos({r["repo"] for r in rows})
    for r in rows:
        r["domain"] = domain_of(info.get(r["repo"]), r["repo"])[0]
        r["topics"] = (info.get(r["repo"]) or {}).get("topics") or []
    if test:
        rows = test_rows(rows, pub)
    match = [r for r in rows if r["domain"] != "other"]
    other = [r for r in rows if r["domain"] == "other"]
    n_other = len(other) if test else round(len(match) / 4)
    rng.shuffle(other)
    nth, seen = {}, collections.Counter()
    for r in other:
        seen[r["repo"]] += 1
        nth[r["id"]] = seen[r["repo"]]
    keep_other = sorted(other, key=lambda r: nth[r["id"]])[:n_other]  # one per repo first
    sel = sorted(match + keep_other, key=lambda r: r["id"])
    got, want = choose_texts(sel, rng)

    med = lambda xs: sorted(xs)[len(xs) // 2]  # noqa: E731
    chosen_len = [len(r["row"]["problem_statement"] if r["opts"][r["pick"]]["kind"] == "issue" else r["row"]["pr"]["text"]) for r in sel]
    print(f"usable {len(rows)} (sources {dict(collections.Counter(r['source'] for r in rows))}) | public-like {len(match)} "
          f"| other {len(other)} -> keep {len(keep_other)} | FINAL {len(sel)} tasks from {len({r['repo'] for r in sel})} repos")
    print("final by source", dict(collections.Counter(r["source"] for r in sel)), "| domain",
          dict(collections.Counter(r["domain"] for r in sel)), "| level", dict(sorted(collections.Counter(r["level"] for r in sel).items())))
    print("tasks per repo", dict(sorted(collections.Counter(collections.Counter(r["repo"] for r in sel).values()).items())),
          "| env_partial", sum(r["env_partial"] for r in sel), "| PR text possible", sum(len(r["opts"]) > 1 for r in sel))
    print(f"texts: leak {got['leak']}/{len(sel)} ({100 * got['leak'] / len(sel):.0f}%, target {want['leak']}) | PR-style "
          f"{got['pr']} ({100 * got['pr'] / len(sel):.0f}%, target {want['pr']}) | unfair {got['unfair']} "
          f"({100 * got['unfair'] / len(sel):.0f}%, target {want['unfair']}) | short (<{SHORT_CHARS} chars of substance) "
          f"{got['short']} ({100 * got['short'] / len(sel):.0f}%, target {want['short']})")
    print(f"text length median: ours {med(chosen_len)} chars | public {med([len(t['problem_statement']) for t in pub])} chars")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = [{"id": r["id"], "source": r["source"], "repo": r["repo"], "text": r["opts"][r["pick"]]["kind"],
            "leak": r["opts"][r["pick"]]["leak"], "short": r["opts"][r["pick"]]["short"], "unfair_names": r["opts"][r["pick"]]["unfair"], "domain": r["domain"],
            "topics": r["topics"], "level": r["level"], "difficulty": r["difficulty"], "env_partial": r["env_partial"]}
           for r in sel]
    (out_dir / "selection.json").write_text(json.dumps(out, indent=0))
    print("wrote", (out_dir / "selection.json").relative_to(ROOT), len(out))


if __name__ == "__main__":
    main()
