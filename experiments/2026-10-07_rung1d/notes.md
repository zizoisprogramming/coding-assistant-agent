# 2026-10-07 — Rung 1d: 1a (3/4 version, control) ×3 vs 1b round 4 (fixes A–C, temperature 0.2) ×3

**Setup:** same 4 tasks; notebook run as Save & Run All (kernel ziad23samer/getting-started-gemma-4-developer-agent-4554ae),
output fetched with `kaggle kernels output`. Configs verified from the run's own output: 1a = commit 30a8c5b
(round-2 prompt, temperature 1.0); 1b = commit 8a645b5 (round 4, temperature 0.2). Raw: `data/results/2026-10-07_rung1d/`.

| | r1 | r2 | r3 | mean |
|---|---|---|---|---|
| 1a (unchanged) | 1/4 | 0/4 | 2/4 | **1.0/4** |
| 1b (round 4) | 3/4 | 2/4 | 1/4 | **2.0/4** |

1a over all 5 runs of this exact version (rung-1b, 1c, 1d ×3): 3, 1, 1, 0, 2 → mean 1.4/4.
Per task (solved / runs here): fastapi_15589 1a 1/3, 1b 2/3; rich_3882 1a 2/3, 1b 3/3; rich_3470 1a 0/3, 1b 1/3;
fastapi_15588 0/6 (unguessable message, see rung-1b).

## Findings
1. **Temperature 0.2 does not make runs repeatable:** 1b still swings 3 → 2 → 1. Variance stays large; compare means
   over ≥3 runs, never single runs.
2. **Fixes A–C worked in 1b:** malformed edit_file args 0 (1a: 30, 6, 0 in the same run), empty submits 0 (1a: 1, 1),
   no "no change needed" submits. The python fallback edit was used once.
3. **1a without fix A loses tasks to broken edits:** 1a_r2 rich_3882 called edit_file without old_string **81×** until
   the 90-turn limit (no patch); 1a_r1 rich_3882 26 such errors (still solved).
4. **New 1b failure:** 1b_r3 rich_3470 — the orchestrator rewrote /tmp/repro.py ~20× in Phase A and never called the
   executor → timeout, no patch (the D16 script-rewrite cost, now as a loop; the "delegate at 6 calls" rule ignored).
5. Fix C (one helper call per reply) still not obeyed: 6–12 multi-call replies per run (no harm seen this time).

## Next (one agent per round)
- 1a round: apply only fixes A–C (keep temperature 1.0) → tests whether they help 1a as they did 1b.
- 1b round: Phase-A loop guard (repro written at most twice, then delegate) + D16 script economy.
