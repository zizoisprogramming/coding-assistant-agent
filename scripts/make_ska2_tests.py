"""Grader-shaped checks on sk_a2 (docs/PLAN.md 'PLAN (not built) 2026-11-23: GRADER-SHAPED CHECKS agents'; user 2026-11-23: 'build it, all 3
arms but on 4 only for each'). Evidence: 52% of sk_a2-family wrong kept edits had a green own check (own_check_vs_hidden.py): the agent checks
its own reading, not the grader's; an existing test that uses the changed function exists for 33/104 tasks (shortest median 5 lines), most on
rich (test_template_precheck.py); hidden tests check variants in 45%.
  sk_a2tm = sk_a2 + a.py option 'tests': the first 'show FILE NAME' of a source function per run appends
            '>>> TESTS THAT USE NAME: file::test a-b, ...' (at most 4) + the shortest one (<= TEMPLATE_MAX numbered lines) as the template
            for the agent's check; nothing when no test uses it, never for test files; prompt scripts/agent_ska2tm/system.md (written in full;
            check = a copy of the template with the issue's case; worked example of the event).
  sk_a2tr = sk_a2tm + 'test the rule': the check runs the issue's case + 2 variants (the opposite / unchanged case, one more input);
            prompt scripts/agent_ska2tr/system.md (written in full; both worked examples show the variants).
a.py otherwise, tools, sampling, eval_config (240 s) = sk_a2 byte for byte. Run: python3 -I scripts/make_ska2_tests.py"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "submissions/sk_a2"
TEMPLATE_MAX = 12

BLOCK = '''

def tests_block(st, name, path=""):
    """sk_a2tm / sk_a2tr: the tests that use NAME, and the shortest one as a template for the agent's check (once per name);
    tests in the matching test file (test_text.py for pkg/text.py) come first, then the shortest."""
    leaf = name.split(".")[-1]
    done = st.setdefault("tests_done", [])
    if len(leaf) < 4 or leaf.startswith("__") or leaf in done:
        return ""
    done.append(leaf)
    out = run(f"git grep -l -w -F -e {q(leaf)} -- tests test '*test_*.py' '*_test.py'", 20)
    files = [f for f in out.split("\\n") if f.endswith(".py") and not f.startswith("(")][:8]
    hits = []
    stem = os.path.splitext(os.path.basename(path))[0].lstrip("_")
    for f in files:
        try:
            tree = ast.parse("\\n".join(file_lines(f)))
        except Exception:  # noqa: BLE001
            continue
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test"):
                if any((isinstance(x, ast.Name) and x.id == leaf) or (isinstance(x, ast.Attribute) and x.attr == leaf) for x in ast.walk(n)):
                    near = 0 if stem and stem in os.path.basename(f) else 1
                    start = min([d.lineno for d in n.decorator_list] + [n.lineno])  # parametrize values are the examples
                    hits.append((near, n.end_lineno - start + 1, f, n.name, start, n.end_lineno))
    if not hits:
        return ""
    st["tests_shown"] = st.get("tests_shown", 0) + 1
    hits.sort()
    listed = hits[:4]
    lines = [f">>> TESTS THAT USE {leaf}: " + ", ".join(f"{f}::{t} {a}-{b}" for _, _, f, t, a, b in listed)
             + (f" (+{len(hits) - 4} more)" if len(hits) > 4 else "")]
    _, _, f, t, a, b = hits[0]
    src = file_lines(f)
    b2 = min(b, a + TEMPLATE_MAX - 1, len(src))
    lines.append(f"the shortest, as the template for your check ({f}):")
    lines += [f"{i:6}| {src[i - 1]}" for i in range(a, b2 + 1)]
    return "\\n".join(lines)

'''


def sub(t, a, b):
    assert t.count(a) == 1, a[:80]
    return t.replace(a, b)


def patched_apy():
    a = (SRC / "skills/agent/scripts/a.py").read_text()
    a = sub(a, 'OPTIONS = {"banner", "reshow"}',
            f'OPTIONS = {{"banner", "reshow", "tests"}}  # sk_a2tm / sk_a2tr: + tests (TESTS THAT USE NAME + a template at show time)\nTEMPLATE_MAX = {TEMPLATE_MAX}')
    a = sub(a, '''    st["looks"] += 1
    st["reads"].append({"file": path, "a": a, "b": b})
    return extra + "\\n".join(f"{i:6}| {src[i - 1]}" for i in range(a, b + 1))
''', '''    st["looks"] += 1
    st["reads"].append({"file": path, "a": a, "b": b})
    body = extra + "\\n".join(f"{i:6}| {src[i - 1]}" for i in range(a, b + 1))
    if rest and not nums and "tests" in OPTS and not TEST_RE.search(path):
        tb = tests_block(st, rest[0], path)
        if tb:
            body += "\\n" + tb
    return body
''')
    a = sub(a, "\n\ndef cmd_note(st, args):", BLOCK + "\ndef cmd_note(st, args):")
    return a


ARMS = {"sk_a2tm": ("scripts/agent_ska2tm/system.md", "sk_a2 + a.py TESTS THAT USE event with a template for the check"),
        "sk_a2tr": ("scripts/agent_ska2tr/system.md", "sk_a2tm + test the rule (the issue's case + 2 variants)")}


def build():
    apy = patched_apy()
    c = (SRC / "skills/agent/scripts/commands.txt").read_text().split()
    assert "tests" not in c
    y0 = (SRC / "agent.yaml").read_text()
    assert y0.startswith("# sk_a2:")
    for arm, (prompt, why) in ARMS.items():
        out = ROOT / "submissions" / arm
        if out.exists():
            shutil.rmtree(out)
        shutil.copytree(SRC, out)
        (out / "skills/agent/scripts/a.py").write_text(apy)
        (out / "skills/agent/scripts/commands.txt").write_text(" ".join(c + ["tests"]) + "\n")
        p = (ROOT / prompt).read_text()
        assert "TESTS THAT USE" in p and "28 tool" in p and "{" not in p
        (out / "prompts/system.md").write_text(p)
        (out / "agent.yaml").write_text(f"# {arm} (2026-11-23): {why} (scripts/make_ska2_tests.py). " + y0.lstrip("# "))
        print("wrote", out.relative_to(ROOT), len(p.split()), "words")


if __name__ == "__main__":
    build()
