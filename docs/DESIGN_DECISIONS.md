# Design decisions — open and settled

Companion to `docs/PLAN.md`. Each open item: the question, the options, the evidence we have, a recommendation, and
what result would settle it. "Measure" means: change one thing, run it on the dev set (Kaggle 31B), compare with
`scripts/analyze.py`. Evidence labels: **verified** (harness/ADK source or our own runs), **forum** (other participants,
not checked by us), **12B** (Mac smoke test — behaviour only, not quality).

Last updated: 2026-10-06.

---

## Settled (for now)

| # | Decision | Why | Revisit when |
|---|----------|-----|--------------|
| S1 | Build two first agents: **1a** single agent, **1b** hybrid orchestrator (reader / executor / verifier helpers) and compare with Google's sample | Paper's first ablation; trade-off between short main context (1b) and hand-off/time cost (1a vs 1b) can only be measured | After the first Kaggle comparison |
| S2 | Thinking **off** (`include_thoughts: false`) | 09-27 run: thinking used most of the ~7k-token budget; no edits in 5 min (verified) | D9 |
| S3 | Sampling temperature 1.0, top_p 0.95, top_k 64 | Google's model card recommendation | D10 |
| S4 | `max_output_tokens: 2048` | prompt + max_output must fit 32,768; smaller cap = more room before overflow (verified) | If edits get cut off mid-reply |
| S5 | Declare the 3 graph tools on the root agent | An undeclared/hallucinated tool call ends the task and discards the patch (forum 745028); the task message advertises them | Host confirms the fix (D11) |
| S6 | No formatter agent; root agent uses unformatted helper replies as-is | Extra model call; cannot recover an empty reply | — |
| S7 | 1b delegates once `get_status.tool_calls_used ≥ 6` | Model cannot see its token count; get_status is free (verified) | D3 |
| S8 | Only the root agent calls `submit_patch` | Avoids a helper ending the task early | — |
| S9 | Budgets: 5 min/task, 240 s command timeout, 90 turns, 60 (1a) / 80 (1b) tool calls | ~120 tasks × ~5.3 min ≈ 10.6 h < 12 h hard limit | D12 |
| S10 | Shell commands use single quotes | 12B sent backslash-escaped quotes and re-ran failing greps (12B) | — |

---

## Open decisions

### D1. Context offloading to the filesystem — how far do we push it?
**Background (verified):** every `run_command` is a fresh `bash -c` in the task's container (cwd `/workspace`). Files
persist for the whole task (one container per task), survive ADK compaction (which keeps only *text* parts of the
history), and are shared by all agents of a task (1b's helpers run in the same container). Anything created in
`/workspace` ends up in the patch → scratch must live in `/tmp`. Tool output reaching the model is cut to the first
5,000 characters. Rejected alternative: elision of old tool output inside the history (needs ADK callbacks; the
harness registers none).

**Options (can combine):**
- **D1a — Notes file** (`/tmp/notes.md`): exact names/strings from the task, file:line facts, chosen interpretation.
  *Status:* already in both prompts. *Question:* does the 31B actually keep it? (the 12B wrote no text at all).
- **D1b — Save long output, show the tail:** `pytest … > /tmp/test.log 2>&1; tail -20 /tmp/test.log`, later
  `grep -n FAILED /tmp/test.log` instead of re-running. Fixes the "first 5,000 chars" problem (pytest's summary is at
  the end) and avoids re-running slow commands.
- **D1c — File hand-off between agents (1b):** reader writes `/tmp/findings.md` (LOCATION / EVIDENCE / FIX PLAN with
  verbatim lines), executor reads it; verifier writes `/tmp/verify.log`. The helper's final reply becomes
  "see /tmp/findings.md" + a 3-line summary. Reduces hand-off loss and protects against an empty final reply (the
  12B reader returned `{"raw": ""}` after 138 s — the file would still hold its work).
- **D1d — Command log to fight loops:** append every command tried and its one-line outcome to `/tmp/notes.md`;
  rule: "check notes before running a command".

**Cost / risk:** every write and read is a tool call (~5–25 s each on the 31B); reading a big file back puts it into
the prompt again → only read slices (`grep`, `tail`, `read_file` with line ranges).

**Recommendation:** add D1b to both prompts and D1c to 1b in the next prompt round; keep D1a; try D1d only if loops
persist on the 31B. **Settled by:** traces show notes/findings files written and read back, fewer repeated commands,
no lost helper work, without a big increase in calls per task.

### D2. Empty or unusable helper replies (1b)
**Evidence:** 12B reader worked 138 s and returned an empty final message; orchestrator re-asked and timed out (12B).
Forum: Gemma rarely writes text next to tool calls.
**Options:** (a) keep "re-ask once, narrower"; (b) never re-ask — continue alone; (c) hard tool cap in helper prompts
("after 6 tool calls, stop and write the final message"); (d) D1c file hand-off so work survives an empty reply.
**Recommendation:** (c) + (d), and switch the orchestrator rule to (b). **Settled by:** Kaggle 31B `format ok` column
and helper durations.

### D3. Delegation trigger for 1b
**Options:** keep `tool_calls_used ≥ 6`; lower (4) to protect context earlier; higher (8–10) to save hand-off time;
work-type rule ("big reads always go to the reader").
**Evidence so far:** 12B delegated at 4 calls (earlier than told). Calibration from 09-27: ~900 prompt tokens/step,
compaction at 14,336.
**Settled by:** peak prompt tokens and compaction counts of 1b vs 1a on the 31B.

### D4. Loop prevention
**Evidence:** 12B 1a repeated near-identical commands 22× in 5 min; forum reports up to 69× and more loops at
temperature 0.7 than 0.2 (forum, 10 tasks). The "never repeat a command" rule alone did not stop the 12B.
**Options:** D1d command log; stronger budget rule ("if 3 calls in a row taught you nothing new, change approach");
lower temperature (D10); in 1b, loops are bounded by helper tool caps.
**Settled by:** `repeat` column on the 31B.

### D5. "One progress line per reply" rule
**Why it exists:** text survives compaction, tool results do not (verified). **Evidence:** the 12B ignored it (every
step had an empty message). **Options:** keep, drop (saves tokens), or replace with D1a notes.
**Settled by:** whether the 31B writes the line and whether compaction-hit tasks recover.

### D6. Fix verification inside 1a
1a has no verifier; it relies on the prompt's "re-run repro + nearest tests". **Option:** give 1a the verifier as its
only helper (= ladder rung 2). **Settled by:** wrong-fix rate of 1a vs 1b.

### D7. Planner (`{plan}` re-injected every turn) and replanner
Ladder rungs 3–4 (PLAN.md). Planner = SequentialAgent [planner (output_key=plan) → executor with `{plan}` in its
instruction]. Paper evidence: planning helps weaker models (+11.6 pts for a 30B at tight budgets). **When:** after
D1–D4 are settled on the current agents.

### D8. Skills (our only custom code)
Candidates: repo map of the source package (fixes the hidden-package listing, forum 745220), async-aware symbol
search (graphs miss async code), test finder (nearest tests for a file). **Risk:** model passes `file_path` as a list
→ crash ends the task (forum 745028). **When:** after the prompt round; one skill at a time.

### D9. Thinking on + budget
Since the Sep 30 wheelhouse, thoughts are kept between tool calls and `thinking_budget` is forwarded (forum,
host-confirmed). Thinking may now help instead of re-deriving the task every step, but kept thoughts fill the 32k
context faster.
**How thoughts persist (Gemma 4 `chat_template.jinja`, HF main; Kaggle's copy may differ):** a past thought is
rendered only if it comes after the last *user* message. Tool results are not user messages, so within one task all
thoughts stay in the prompt; a harness nudge is a new user message and drops all earlier thoughts.
**We cannot strip thoughts ourselves:** no callbacks to edit history; `include_thoughts: false` disables thinking
entirely (no "think but don't keep" mode, forum 745059 unanswered).
**Options:** (a) thinking everywhere with `thinking_budget` 512/1024; (b) **thinking only in helpers (1b)** — each
agent has its own generate_content_config, and a helper's whole session (thoughts included) is discarded when it
returns, so reasoning costs time but not orchestrator context; (c) off (current).
**Cost:** ~25 tok/s → a 1,000-token thought ≈ 40 s per step.
**Measure:** 1a off vs 1a budget 512; 1b with thinking only in reader/verifier vs all off.

### D10. Temperature 1.0 vs 0.2
Google recommends 1.0; one forum test saw more loops at 0.7 than 0.2. **Measure** after the first comparison.

### D11. Graph tools
Declared only as crash insurance (S5); `search_similar_code` returned 0 results in 140/142 calls (forum) and was useless
on 09-27 (verified). **Decide:** remove once the host confirms unknown tool calls no longer end the task.

### D12. Per-task time budget
5 min is set by the 12 h total. If tasks often time out right before submitting, consider 5.5 min (≈ 11.5 h total,
tight) or per-task early stops. **Settled by:** time-to-first-edit and timeout rate.

### D13. Dev set size
Currently 4 gold-checked tasks (1 task = 25 %, directional only). **Plan:** grow to ~20 gold-checked tasks across
fastapi / rich / requests before trusting differences (~2 h Kaggle wall = ~4 h quota per config).

### D14. LoRA
Blocked: scorer loads adapters with zeroed weights (forum 743508); LoRA also shrinks KV cache. Training-data route
when unblocked: self-distillation from our own verified-pass 31B trajectories, or open-weight teachers
(Qwen3.6-27B, Apache 2.0). No Claude/GPT-generated training data.
