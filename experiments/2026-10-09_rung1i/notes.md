# Rung-1i (2026-10-09): 1b round 6c (round 6b + temperature 1.0), stopped after repeat 1

Config: commit aec4173. Repeat 1 only (user stopped the run): rich_3882 solved (124 s); fastapi_15588 wrong fix
at timeout; fastapi_15589 and rich_3470 timeout with no patch.

## Repetition: gone
Longest identical back-to-back streak: 1 in every task (round 6b at 0.2: 10, 12, 57). repro.py writes ≤ 3.

## New: hidden output tokens make everything slow
- Output tokens 30,215 but the visible tool calls/text add up to ≈ 8,850 tokens: **3.4× hidden**. 31 of 117
  model steps had > 150 unexplained tokens, e.g. `head -20 fastapi/sse.py` = 2,596 output tokens (~70 s),
  `git log --oneline -15` = 2,070. ≈ 21,000 hidden tokens ≈ 590 s over 4 tasks → the 3 timeouts.
- Every earlier run had **1.0×** (no hidden tokens), including 1b at 1.0 (rungs 1b, 1c) and 1a at 1.0 (rung-1d),
  so temperature alone does not explain it.
- **The wheelhouse changed on 2026-10-08 19:18:** adk_submission 0.2.12 → 0.2.13 (swegemma 0.2.10 per forum
  747519). Diff (data/wheels/new_0213): `include_thoughts: false` still sends enable_thinking=false to the chat
  template, but 0.2.13 now also **strips `Part(thought=True)` and reasoning_content** from responses before they
  reach the session (and so the trace). Our vLLM runs with reasoning_parser='gemma4'.
- Most likely reading (unverified): the model now produces reasoning tokens that the parser routes to
  reasoning_content and 0.2.13 deletes, so they cost time but are invisible. Not known: which wheelhouse version
  each of our runs installed (the notebook does not print it), and why thinking happens with enable_thinking=false.

## Next
1. Notebook prints installed adk_submission / swegemma / google-adk versions.
2. Diagnostic cell: one direct vLLM chat call with enable_thinking=false at T 0.2 and 1.0, printing the length of
   reasoning_content vs content → shows whether the model thinks despite the flag.
3. This also affects the leaderboard: the scorer uses the current wheelhouse.
