# Rung-1z (2026-10-11): 1a round 4 on gemma-4-12b-it-qat-w4a16-ct, 4 tasks × 2

Config: commit 078e402 (round 4, only `model:` changed; vLLM started with the host's --hf-overrides flag plus our
local-only "vision_embedder." skip-list patch, D22). Result **1/4, 1/4** — only rich_3882 (31B round 4: 2/4, 2/4).
6 of 8 tasks ended at the 5-min limit.

| | 31B round 4 (rung-1s) | 12B round 4 | E4B round 4 (rung-1y) |
|---|---|---|---|
| score | 2/4, 2/4 | 1/4, 1/4 | 0/4, 0/4 |
| output tokens/s (incl. tool time) | ~29 | ~48–62 | ~57–86 |
| output tokens per task | 3.1–9.2k | 3.7–15.8k (≈15k when it runs to the limit) | 2.9–8.9k |
| steps per task | 21–45 | 20–54 | 11–24 |
| first edit | 39–278 s (1 task none) | 43–188 s (3 tasks none) | 11–73 s |

**Why a faster model still times out:**
1. It writes about twice as much: ~1.8× the tokens/s of the 31B, but up to ~15k output tokens per task (visible
   thinking full of "Wait, I missed something…", re-reading the same code), so the speed is spent on words.
2. **Silent stalls (12B only):** in 3/8 tasks the trace stops and nothing happens until the limit (r2 fastapi_15589:
   last step 66 s → 236 s silent; r1 rich_3470: 120 s → 182 s; r2 rich_3470: 188 s → 114 s). Not seen in 34
   earlier run folders (31B, E4B). max_output_tokens 2048 at ~50 tok/s caps a generation at ~40 s, so this looks
   like a request that never returns. Unverified cause; candidates: the vLLM gemma4 tool-argument parser loop
   (forum 745138) on a malformed call, or something specific to serving the 12B through the override. Needs the
   vLLM server output (notebook cell 3) to tell.
Conclusion: 12B is worse than 31B on score and not faster per task. Stay on 31B.
