"""sk_a2o2n = sk_a2 + the YOUR EDIT / SAME LINES ELSEWHERE output only (user 2026-11-24: 'make only sk_a2 and sk_a2o2n and on 4 tasks only').
r155: sk_a2o (= sk_a2 + a.py check + YOUR EDIT + EDIT MATERIAL) ran 67 scripts before its edits vs sk_a2 33 (the check wording revived
reproduce-first) and EDIT MATERIAL was followed 1/14. sk_a2o2n drops both: no a.py check, no EDIT MATERIAL, sk_a2's Step 3 verbatim.
  a.py: sk_a2's, plus edited_function (from scripts/make_ska2c.py) and _func_at / same_lines / edit_block (from scripts/make_ska2c2o.py);
        after a source change every a.py output adds 'YOUR EDIT: file function a-b. SAME LINES ELSEWHERE: ...'.
  prompt: scripts/agent_ska2o2n/system.md, written in full (sk_a2's + 'What a.py shows after your edit' + a no-experiments rule in Step 1;
        Examples: plain path; r155 rich_3278 failure (12 scripts, time-out) -> edit from the read; SAME LINES ELSEWHERE -> sibling edit;
        r155 rich_4079 failure (12 reads after STOP READING, no patch) -> edit now).
Run: python3 -I scripts/make_ska2o2n.py"""
import importlib.util
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC, OUT = ROOT / "submissions/sk_a2", ROOT / "submissions/sk_a2o2n"


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def sub(t, a, b):
    assert t.count(a) == 1, a[:80]
    return t.replace(a, b)


def build():
    c, o = load("make_ska2c"), load("make_ska2c2o")
    edited_fn = c.CHECK[:c.CHECK.index("def cmd_check(st, args):")]
    outputs = o.OUTPUTS[:o.OUTPUTS.index("def stop_material(st):")]
    assert "def edited_function():" in edited_fn and "def edit_block(st):" in outputs and "stop_material" not in outputs
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SRC, OUT)
    ap = OUT / "skills/agent/scripts/a.py"
    a = ap.read_text()
    a = sub(a, "\n\nHANDLERS = {", "\n\n" + edited_fn.rstrip() + "\n" + outputs + "\nHANDLERS = {")
    a = sub(a, """    save(st)
    warn = banner(st)
    if warn:
        print(warn)
    print(header(st))
    print(body)
    if warn:
        print(warn)
""", """    save(st)
    warn = banner(st)
    extra = edit_block(st)  # sk_a2o2n: after a source change, the edited function + SAME LINES ELSEWHERE
    if warn:
        print(warn)
    print(header(st))
    if extra:
        print(extra)
    print(body)
    if warn:
        print(warn)
""")
    ap.write_text(a)
    p = (ROOT / "scripts/agent_ska2o2n/system.md").read_text()
    assert "YOUR EDIT" in p and "a.py check" not in p and "EDIT MATERIAL" not in p and "28 tool" in p and "{" not in p
    (OUT / "prompts/system.md").write_text(p)
    y = (OUT / "agent.yaml").read_text()
    (OUT / "agent.yaml").write_text(sub(y, "# sk_a2: mix + the agent's reading tool",
                                        "# sk_a2o2n (2026-11-24): sk_a2 + YOUR EDIT / SAME LINES ELSEWHERE after an edit (scripts/make_ska2o2n.py). sk_a2 was: mix + the agent's reading tool"))
    print("wrote", OUT.relative_to(ROOT), len(p.split()), "words")


if __name__ == "__main__":
    build()
