"""Validate a submission directory with the competition's own checks and zip it.

Usage:
    uv run scripts/pack.py submissions/1a            # -> dist/1a.zip
    uv run scripts/pack.py submissions/1b --no-zip   # validate only

Checks (all from the official packages): allowed file extensions and total size, exactly one declared base model,
and that adk_submission.compile_submission() builds the agent tree with the competition's limits, generation
constraints and model aliases. Tools are stand-ins with the real names (the real ones need a live sandbox).
"""

import argparse
import sys
import zipfile
from pathlib import Path

from adk_submission import compile_submission
from swegemma.config import ALLOWED_SUBMISSION_EXTENSIONS, MAX_SUBMISSION_SIZE_BYTES, build_submission_limits
from swegemma.models.discovery import validate_single_declared_model
from swegemma.models.registry import setup_gemma_model_registry

ROOT = Path(__file__).resolve().parent.parent

# The competition's closed tool registry (swegemma tools); stand-ins only need the right names.
TOOL_NAMES = [
    "run_command", "read_file", "edit_file", "write_file", "get_status", "submit_patch",
    "search_similar_code", "get_code_neighbors", "get_code_subgraph",
]


def stand_in(name):
    def tool(**kwargs) -> str:
        """Stand-in tool used only for compile validation."""
        return "{}"

    tool.__name__ = name
    return tool


def describe(agent, depth=0):
    """Print the compiled agent tree: agents, their tools and helper agents."""
    tools = []
    for t in getattr(agent, "tools", []) or []:
        sub = getattr(t, "agent", None)
        tools.append(f"agent_tool:{sub.name}" if sub else getattr(t, "name", None) or getattr(t, "__name__", str(t)))
    print(f"{'  ' * depth}- {type(agent).__name__} {agent.name}: {', '.join(tools)}")
    for t in getattr(agent, "tools", []) or []:
        if getattr(t, "agent", None):
            describe(t.agent, depth + 1)
    for sub in getattr(agent, "sub_agents", []) or []:
        describe(sub, depth + 1)


def validate(sub_dir):
    files = [p for p in sub_dir.rglob("*") if p.is_file()]
    bad = [p for p in files if p.suffix.lower() not in ALLOWED_SUBMISSION_EXTENSIONS]
    if bad:
        sys.exit(f"Disallowed file types: {[str(p.relative_to(sub_dir)) for p in bad]}")
    total = sum(p.stat().st_size for p in files)
    if total > MAX_SUBMISSION_SIZE_BYTES:
        sys.exit(f"Submission too large: {total} bytes")
    if not (sub_dir / "agent.yaml").exists():
        sys.exit("agent.yaml must be at the submission root")

    model = validate_single_declared_model(sub_dir)
    limits, gen_constraints = build_submission_limits()
    models = setup_gemma_model_registry(api_base="http://127.0.0.1:8000/v1", api_key="EMPTY")
    agent = compile_submission(
        submission_dir=sub_dir,
        tool_registry={name: stand_in(name) for name in TOOL_NAMES},
        model_registry=models,
        limits=limits,
        generation_constraints=gen_constraints,
    )
    print(f"OK: {sub_dir.relative_to(ROOT)} — {len(files)} files, {total / 1024:.1f} KiB, model {model}")
    describe(agent)
    return files


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("submission_dir")
    ap.add_argument("--no-zip", action="store_true")
    args = ap.parse_args()
    sub_dir = Path(args.submission_dir).resolve()
    files = validate(sub_dir)
    if not args.no_zip:
        out = ROOT / "dist" / f"{sub_dir.name}.zip"
        out.parent.mkdir(exist_ok=True)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for p in sorted(files):
                z.write(p, p.relative_to(sub_dir).as_posix())
        print(f"Wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
