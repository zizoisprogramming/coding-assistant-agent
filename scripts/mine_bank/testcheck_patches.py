"""Patches for the CPU test check (user 2026-11-17: 'yes build the CPU check'). Imported by
scripts/train/make_testcheck_cells.py and scripts/mine_bank/testcheck_local.py; run alone it prints the counts:
    python3 -I scripts/mine_bank/testcheck_patches.py

Every non-empty agent patch in data/results/2026-1* on the 24 SWE-rebench test tasks (public data; no competition
task), deduplicated per task by text, labelled solved / wrong from gen_per_task.jsonl. Per task at most MAX_WRONG
wrong and MAX_SOLVED solved patches, the current line (pub024, sa2, sb1) first, then the rest in a fixed order.
Each wrong patch also says whether it touches a real-fix source file (else it is a scratch-only or wrong-file patch)."""
import glob, json, os, re

MAX_WRONG, MAX_SOLVED, MAX_CHARS = 10, 5, 30000
CURRENT = ("pub024", "sa2", "sb1")
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$")


def rt_ids():
    ids = set()
    for per in glob.glob("data/results/2026-11-1*_skill_sb1rt_p*/**/gen_per_task.jsonl", recursive=True):
        ids |= {json.loads(l)["instance_id"] for l in open(per)}
    assert len(ids) == 24, len(ids)
    return sorted(ids)


def src_files(patch):
    return {f for f in re.findall(r"^diff --git a/\S+ b/(\S+)", patch, re.M) if f.endswith(".py") and not TEST.search(f)}


def collect():
    ids = set(rt_ids())
    gold = {}
    for l in open("data/swe_rebench/candidates.jsonl"):
        j = json.loads(l)
        if j["instance_id"] in ids:
            gold[j["instance_id"]] = j
    seen, cands = set(), []
    for per in sorted(glob.glob("data/results/2026-1*/**/gen_per_task.jsonl", recursive=True)):
        pdir = os.path.dirname(per)
        for l in open(per):
            g = json.loads(l)
            iid = g["instance_id"]
            if iid not in ids or not g.get("arm"):
                continue
            pf = os.path.join(pdir, "gen/patches", f"{iid}__a{g.get('attempt')}.diff")
            if not os.path.exists(pf):
                continue
            p = open(pf, errors="replace").read()
            key = (iid, re.sub(r"^index .*$", "", p, flags=re.M).strip())
            if not p.strip() or key in seen or len(p) > MAX_CHARS:  # >30k: data files (whatshap .bam 1.6 MB, a .png)
                continue
            seen.add(key)
            solved = g.get("resolved") in (True, "True")
            gf = src_files(gold[iid]["patch"])
            cands.append(dict(iid=iid, kind="solved" if solved else "wrong", arm=g["arm"], run=f"{per.split('/')[2]}:{g.get('attempt')}",
                              touches_fix=bool(src_files(p) & gf), patch=p))
    out = []
    for iid in sorted(ids):
        for kind, cap in (("wrong", MAX_WRONG), ("solved", MAX_SOLVED)):
            xs = [c for c in cands if c["iid"] == iid and c["kind"] == kind]
            xs.sort(key=lambda c: (c["arm"] not in CURRENT, c["run"]))
            out += xs[:cap]
    return out, gold


if __name__ == "__main__":
    out, gold = collect()
    print(f"{len(out)} patches on {len({c['iid'] for c in out})} tasks | wrong {sum(c['kind'] == 'wrong' for c in out)} (touch a real-fix file "
          f"{sum(c['kind'] == 'wrong' and c['touches_fix'] for c in out)}) | solved {sum(c['kind'] == 'solved' for c in out)} | chars {sum(len(c['patch']) for c in out)}")
    for iid in sorted(gold):
        print(f"  {iid[:48]:48} wrong {sum(c['iid'] == iid and c['kind'] == 'wrong' for c in out):2} solved {sum(c['iid'] == iid and c['kind'] == 'solved' for c in out):2}")
