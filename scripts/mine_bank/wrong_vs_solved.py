"""Same-task comparison, patched runs only (solved vs wrong patch): which behaviours go with solving?"""
import re, collections, json, sys, statistics as st
src = open("scripts/mine_bank/big_slices.py").read()
src = src.replace('rows.append(dict(arm=g["arm"]', 'SEQ.append((g["arm"], iid, sl, [(n, a, o) for (n, a, o, t) in seq])); rows.append(dict(arm=g["arm"]')
src = src.split("\ndef report")[0]
SEQ = []
sys.argv = ["x"] + sys.argv[1:]
exec(src)
def is_test_run(a): return bool(re.search(r"pytest|unittest", str(a.get("command", ""))))
def is_py(a): c = str(a.get("command", "")); return bool(re.search(r"<<|python3? -c|python3? \S+\.py", c)) and not is_test_run(a)
def failing(o): return bool(o and re.search(r"\b\d+ failed|FAILED|Traceback|Error\b|AssertionError", o))
feats = collections.defaultdict(dict)
for arm, iid, sl, s in SEQ:
    if sl in ("patch, files not on disk", "no patch"): continue
    ed = [k for k, (n, a, o) in enumerate(s) if n in ("edit_file", "write_file") and o and not is_err(o) and path_of(a).endswith(".py") and not TEST.search(path_of(a)) and not path_of(a).startswith(".git")]
    if not ed: continue
    f0, fl = ed[0], ed[-1]
    after = s[fl + 1:]; before = s[:f0]
    v_after = [x for x in s[f0 + 1:] if x[0] == "run_command" and (is_py(x[1]) or is_test_run(x[1]))]
    F = {
        "python check before first edit (repro)": any(x[0] == "run_command" and is_py(x[1]) for x in before),
        "python check after last edit": any(x[0] == "run_command" and is_py(x[1]) for x in after),
        "pytest after last edit": any(x[0] == "run_command" and is_test_run(x[1]) for x in after),
        "existing test file read before first edit": any((x[0] == "read_file" and TEST.search(path_of(x[1]))) or (x[0] == "run_command" and re.search(r"(sed -n|cat|head)[^|;]*tests?/", str(x[1].get("command", "")))) for x in before),
        "last check after last edit shows an error": any(failing(x[2]) for x in [x for x in after if x[0] == "run_command" and (is_py(x[1]) or is_test_run(x[1]))][-1:]),
        ">= 3 source edits": len(ed) >= 3,
        "validation share >= 25% of calls": len([x for x in s if x[0] == "run_command" and (is_py(x[1]) or is_test_run(x[1]))]) / max(1, len(s)) >= 0.25,
        "edit -> check -> edit again (iterated)": any(k2 > k1 + 1 and any(x[0] == "run_command" and (is_py(x[1]) or is_test_run(x[1])) for x in s[k1 + 1:k2]) for k1, k2 in zip(ed, ed[1:])),
    }
    feats[iid].setdefault("runs", []).append((sl == "solved", F, arm, iid in RT))
names = list(next(iter(feats.values()))["runs"][0][1].keys())
print(f"patched runs with a made source edit: {sum(len(v['runs']) for v in feats.values())} on {len(feats)} tasks; solved {sum(r[0] for v in feats.values() for r in v['runs'])}")
for nm in names:
    better = worse = 0; dsum = []; nwith = nwo = 0
    for iid, v in feats.items():
        w = [r[0] for r in v["runs"] if r[1][nm]]; wo = [r[0] for r in v["runs"] if not r[1][nm]]
        nwith += len(w); nwo += len(wo)
        if len(w) >= 2 and len(wo) >= 2 and 0 < sum(r[0] for r in v["runs"]) < len(v["runs"]):
            d = sum(w) / len(w) - sum(wo) / len(wo); dsum.append(d)
            better += d > 0; worse += d < 0
    print(f"  {nm:46} runs with {nwith:4} / without {nwo:4} | same-task tasks {len(dsum):2}: solve rate diff {st.mean(dsum) if dsum else 0:+.2f}, tasks better {better} / worse {worse}")
