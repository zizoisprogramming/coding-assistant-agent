# Run: python3 -I scripts/mine_bank/nopatch_edit_errors.py   (current line pub024, sa2, sb1; builds on big_slices.py)
import re, collections, json, sys
src = open("scripts/mine_bank/big_slices.py").read()
src = src.replace('rows.append(dict(arm=g["arm"]', 'EDITRES.append((g["arm"], iid, sl, [(n, o, a) for (n, a, o, t) in seq if n in ("edit_file", "write_file")])); rows.append(dict(arm=g["arm"]')
src = src.split("\ndef report")[0]
EDITRES = []
sys.argv = ["x", "pub024,sa2,sb1"]
exec(src)
def kind(o, a):
    if o is None: return "no result (last call / cut)"
    s = o[:600]
    if "mandatory input parameters" in s or "not present" in s: return "garbled call (missing parameter)"
    if "old_string not found" in s or "not found in" in s: return "old_string not found"
    if re.search(r"occurs \d+ times|multiple|more than once", s): return "old_string occurs several times"
    if "flexibl" in s: return "flexible match refused"
    if "Path traversal" in s: return "path outside workspace"
    if "budget" in s.lower(): return "budget exhausted"
    if re.search(r"'status': 'error'|\"status\": \"error\"|error_message", s): return "other error: " + re.sub(r"\s+", " ", s)[:90]
    return "ok"
by = collections.Counter(); runs = collections.Counter(); tasks = collections.Counter()
ok_np = collections.Counter()
for arm, iid, sl, eds in EDITRES:
    if sl != "no patch": continue
    ks = [kind(o, a) for n, o, a in eds]
    for k in ks: by[k] += 1
    if eds and all(k != "ok" for k in ks):
        runs[collections.Counter(ks).most_common(1)[0][0]] += 1
        tasks[iid] += 1
    if any(k == "ok" for k in ks):
        ok_np[iid] += 1
print("edit results in no-patch runs:", by.most_common())
print("no-patch runs where every edit failed, by main error:", runs.most_common())
print("those runs by task:", tasks.most_common(12))
print("no-patch runs with an 'ok' edit, by task:", ok_np.most_common(8))
# sample of 'ok' edits in no-patch runs
n = 0
for arm, iid, sl, eds in EDITRES:
    if sl == "no patch" and any(kind(o, a) == "ok" for n_, o, a in eds) and n < 4:
        n += 1
        for n_, o, a in eds:
            print("  ", arm, iid, n_, json.dumps(a)[:150], "->", (o or "")[:200].replace("\n", " "))
