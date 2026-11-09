import collections, json, re, statistics as st, sys
TEST=re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")
def feats(r):
    c=r["calls"]; f=collections.OrderedDict()
    reads=[x for x in c if x["n"]=="read_file"]; cmds=[x for x in c if x["n"]=="run_command"]
    edits=[x for x in c if x["n"]=="edit_file" and "error" not in x["r"][:30] and "mandatory" not in x["r"]]
    src_edits=[x for x in edits if not TEST.search(str(x["a"].get("filepath",""))) and not str(x["a"].get("filepath","")).startswith("/tmp")]
    fe=src_edits[0]["t"] if src_edits else None
    f["first_edit_s"]=fe if fe is not None else 480
    f["calls"]=len(c)
    f["reads"]=len(reads)
    seen=collections.Counter(); rr=0
    for x in reads:
        k=(x["a"].get("filepath"),x["a"].get("start_line"),x["a"].get("end_line"))
        if seen[k]: rr+=1
        seen[k]+=1
    f["exact_rereads"]=rr
    f["files_read"]=len({x["a"].get("filepath") for x in reads})
    f["test_files_read"]=len({x["a"].get("filepath") for x in reads if TEST.search(str(x["a"].get("filepath","")))})
    cm=[str(x["a"].get("command","")) for x in cmds]
    f["grep_cmds"]=sum(bool(re.search(r"\bgrep\b|\brg\b",s)) for s in cm)
    f["python_runs"]=sum(bool(re.search(r"\bpython3?\b",s)) and "pytest" not in s and "pip" not in s for s in cm)
    f["pytest_runs"]=sum("pytest" in s for s in cm)
    f["git_cmds"]=sum(s.strip().startswith("git") or " git " in s for s in cm)
    f["cmds_before_edit"]=sum(1 for x in cmds if fe is None or x["t"]<fe)
    f["runs_after_edit"]=sum(1 for x in cmds if fe is not None and x["t"]>fe and re.search(r"python|pytest",str(x["a"].get("command",""))))
    f["edits_ok"]=len(src_edits)
    f["edit_files"]=len({x["a"].get("filepath") for x in src_edits})
    f["edit_fail"]=sum(1 for x in c if x["n"]=="edit_file" and ("error" in x["r"][:30]))
    f["new_str_chars"]=sum(x["alen"].get("new_string",0) for x in src_edits)
    f["old_str_chars"]=sum(x["alen"].get("old_string",0) for x in src_edits)
    q=[x for x in r["reqs"] if x["tools"]]
    f["out_tokens"]=sum(x["out"] or 0 for x in q)
    f["long_reqs"]=sum(x["s"]>=30 for x in q)
    f["max_req_s"]=max([x["s"] for x in q] or [0])
    f["out_before_edit"]=sum(x["out"] or 0 for x in q if fe is None or x["t"]<fe)
    f["out_after_edit"]=sum(x["out"] or 0 for x in q if fe is not None and x["t"]>=fe)
    f["compactions"]=sum(1 for a,b in zip(q,q[1:]) if b["nmsg"]<a["nmsg"]-2)
    f["budget_hit"]=int(any("budget exhausted" in x["r"].lower() or "Tool call budget" in x["r"] for x in c))
    f["submit"]=int(any(x["n"]=="submit_patch" for x in c))
    f["has_patch"]=int(r["patch"]>0)
    return f
rows=[json.loads(l) for l in open(sys.argv[1])]
rows=[r for r in rows if "e4b" not in r["folder"] and "probe" not in r["folder"] and "replay" not in r["folder"]]
only_patch = len(sys.argv)>2 and sys.argv[2]=="patch"
if only_patch: rows=[r for r in rows if r["patch"]>0]
grp=collections.defaultdict(list)
for r in rows: grp[r["task"],r["arm"]].append((r["resolved"],feats(r)))
mixed={k:v for k,v in grp.items() if any(a for a,_ in v) and not all(a for a,_ in v)}
print(f"runs {len(rows)}; (task,arm) groups with both outcomes: {len(mixed)}, runs in them {sum(len(v) for v in mixed.values())}, tasks {len({k[0] for k in mixed})}")
keys=list(next(iter(mixed.values()))[0][1].keys())
print(f"{'feature':18}{'solved':>9}{'failed':>9}{'diff':>8}{'groups s>f':>12}{'s<f':>6}")
for k in keys:
    d=[];w=[];sv=[];fv=[]
    for v in mixed.values():
        s=[f[k] for a,f in v if a]; fl=[f[k] for a,f in v if not a]
        d.append(st.mean(s)-st.mean(fl)); sv.append(st.mean(s)); fv.append(st.mean(fl))
    print(f"{k:18}{st.mean(sv):9.1f}{st.mean(fv):9.1f}{st.mean(d):+8.1f}{sum(x>0 for x in d):>12}{sum(x<0 for x in d):>6}")
