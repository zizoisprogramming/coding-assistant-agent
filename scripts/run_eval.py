"""Run the official swegemma Evaluator on a submission, configured like the scorer.

Mirrors the host's getting-started notebook (budgets from the submission's eval_config.yaml, competition limits and
generation constraints, events compaction at 14,336 tokens, context caching) instead of the `swegemma eval` CLI,
which ignores eval_config.yaml and compaction. The same function runs locally (Docker sandbox + Ollama) and on Kaggle
(subprocess sandbox + vLLM).

Local usage:
    uv run scripts/run_eval.py submissions/1a --tasks fastapi_15588,rich_3469
    uv run scripts/run_eval.py submissions/1b --tasks rich_3469 --results results/1b_smoke
"""

import argparse
import asyncio
import time
from pathlib import Path

import yaml
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.apps._configs import EventsCompactionConfig
from swegemma.config import EvalConfig, build_submission_limits
from swegemma.evaluate import Evaluator
from swegemma.models.registry import setup_gemma_model_registry

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def read_eval_config(submission_dir):
    """The four eval_config.yaml keys the scorer reads (defaults as in the host notebook)."""
    path = Path(submission_dir) / "eval_config.yaml"
    raw = yaml.safe_load(path.read_text()) if path.exists() else {}
    section = (raw or {}).get("evaluation", raw or {})
    return {
        "timeout_seconds": int(section.get("timeout_seconds", 300)),
        "max_tool_calls": section.get("max_tool_calls"),
        "max_time_minutes": float(section.get("max_time_minutes", 5.0)),
        "max_turns": section.get("max_turns"),
    }


def build_config(submission_dir, task_ids, results_dir, models, data_dir=DATA, sandbox="docker",
                 adapter_manifest=None, display_mode="single"):
    limits, gen_constraints = build_submission_limits()
    budgets = read_eval_config(submission_dir)
    return EvalConfig(
        tasks_path=Path(data_dir) / "tasks.jsonl",
        snapshots_dir=Path(data_dir) / "snapshots",
        results_dir=Path(results_dir),
        submission_dir=Path(submission_dir),
        models=models,
        sandbox=sandbox,
        wheels_dir=Path(data_dir) / "wheels",
        graph_dir=str(Path(data_dir) / "graphs"),
        embeddings_dir=str(Path(data_dir) / "embeddings"),
        task_ids=list(task_ids),
        limits=limits,
        generation_constraints=gen_constraints,
        adapter_manifest=adapter_manifest,
        context_cache_config=ContextCacheConfig(min_tokens=2048, ttl_seconds=1800, cache_intervals=10),
        events_compaction_config=EventsCompactionConfig(
            compaction_interval=5, overlap_size=2, token_threshold=14336, event_retention_size=5,
        ),
        display_mode=display_mode,
        **budgets,
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("submission_dir")
    ap.add_argument("--tasks", required=True, help="comma-separated instance ids")
    ap.add_argument("--results", help="results dir (default results/<submission>_<timestamp>)")
    ap.add_argument("--models-yaml", default=str(ROOT / "configs" / "ollama.yaml"))
    ap.add_argument("--display", default="single", choices=["auto", "dashboard", "single", "quiet"])
    args = ap.parse_args()

    sub = Path(args.submission_dir).resolve()
    results = Path(args.results or ROOT / "results" / f"{sub.name}_{time.strftime('%Y%m%d_%H%M%S')}")
    models = setup_gemma_model_registry(models_yaml_path=args.models_yaml)
    config = build_config(sub, args.tasks.split(","), results, models, display_mode=args.display)
    result = asyncio.run(Evaluator(config).run())
    print(f"{sub.name}: {result.resolved}/{result.total} resolved — results in {results.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
