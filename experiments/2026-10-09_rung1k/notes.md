# Rung-1k (2026-10-09): 1b round 7 at T 0.2, 2 repeats + sampling diagnostic (real first request)

Config: commit 2429c1b. adk-submission 0.2.13, swegemma 0.2.10. Result **1/4, 1/4** (rich_3882 both).

## Sampling diagnostic: model never thinks on a direct vLLM call
Real first orchestrator request (full prompt, harness task message without the workspace tree; 3.3–3.6k prompt
tokens), thinking off, 3 samples × 2 tasks per setting: T1.0/p.95/k64, T1.0/p.80/k20, T0.6, T0.4, T0.2 →
**0/30 with reasoning, 0/30 marker leaks, 30/30 proper tool calls**, 69–196 output tokens, 2–4 s.

## But the agent runs still have hidden tokens, at T 0.2 too
Output/visible tokens: 2.8× (rung-1j at T1.0: 3.0×). Text-only tool calls 2, thinking nudges 1.
**Dated by trace timestamps:** every run that started before the wheelhouse update (2026-10-08 19:18 UTC:
rungs 1d–1h, 5 runs) has 1.0–1.1×; every run after it (1i, 1j, 1k) has 2.8–3.4×, regardless of temperature or
prompt. → The hidden tokens come with the update and from the ADK/LiteLLM/adk_submission request path, not from
the model at our settings (direct calls are clean). Mechanism not found: for our config both 0.2.12 and 0.2.13
send enable_thinking=false; 0.2.13 additionally strips thought parts from responses (generation.py is the only
changed adk_submission file); swegemma 0.2.10 has no thinking-related change vs 0.2.7.

## Round 7 at T 0.2
Repetition back (streaks 22, 37 in r2), first handoff at 59–224 s, executor 53 s per call. Confounded by the hidden
tokens; does not judge the merge.

## Forum 746250 (Ayush Thakur, 129 local tasks, long time caps)
Thinking disabled 17.8 % vs thinking on (budget 4,096) 37–40 %; thought summaries off 27 %; T 0.4 = T 1.0;
graph tools no benefit. Kaggle 4×L4 calibration: 8.7 s per call with thinking; they plan 5.5 min/task.
Not at our 5-min budget, but the thinking-off penalty is the largest effect reported anywhere so far.
