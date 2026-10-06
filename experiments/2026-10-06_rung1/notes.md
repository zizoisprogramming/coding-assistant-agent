# 2026-10-06 — Rung 1: Google sample vs 1a (single agent) vs 1b (orchestrator)

**Setup:** Kaggle L4×4, real `gemma-4-31b-it-qat-w4a16-ct` on vLLM 0.19.1, wheelhouse v28 (adk_submission 0.2.12),
pinned Python 3.12 environment (copy of the host notebook). Notebook: `kaggle/eval_compare.ipynb` at commit 59d00cd
(+ `DATA = DATA_DIR` fix). Dev tasks (gold patch verified locally): fastapi_15588, fastapi_15589, rich_3882, rich_3470.
Submissions: sample = Google's sample_submission without adapters (thinking on, temp 0.2, 16k output, 5 min / 100
tools); 1a / 1b = `submissions/` at that commit (thinking off, temp 1.0, top_k 64, 2048 output, 5 min, 60 / 80 tools).
Raw results: `data/results/2026-10-06_rung1/` (gitignored). Full table: `analyze.txt`.

**Score:** sample 1/4, 1a 1/4, 1b 1/4 — all solved only rich_3882. 4 tasks → directional only.

| | sample | 1a | 1b |
|---|---|---|---|
| Time on solved task (rich_3882) | 93 s | **66 s** | 79 s |
| Output tokens per task (avg) | ~6,000 | **~2,900** | ~4,700 |
| Timeouts | 2/4 | **0/4** | 1/4 |
| Patches touching scratch/test files | 3/4 | 3/4 (repro.py) | 0/4 |

## Findings
1. **Thinking off is much faster.** 1a never timed out; sample timed out on 2/4 and used ~2× the output tokens.
2. **Scratch files leak into the patch (biggest bug, ours too).** `write_file` cannot write to `/tmp`
   ("Path traversal detected: '/tmp/repro.py' escapes workspace") → 1a wrote `repro.py` into `/workspace`
   (patches of 3/4 tasks contain it; on 2 tasks the patch was *only* repro.py). Sample did the same
   (`verify_sse.py`, `reproduce_issue.py`, `test_starlette_headers.py`). 1b's patches were clean.
3. **Near-miss on fastapi_15588 (1a, 1b, sample all edited fastapi/sse.py correctly in behaviour):** hidden test
   expects the exact message `SSE '<field>' must be a single line` and `\r` handling; the existing check in the same
   file already uses the `SSE '<field>' …` style. → prompt rule: reuse existing message/naming conventions;
   handle `\r` with `\n`.
4. **Malformed tool calls** (raw `<|tool_call>call:…` as text): 1a fastapi_15589 (4) and rich_3470 (9) — e.g. the
   shell command used as the tool name (`call:git grep …`) → harness treats it as a cut-off reply → token-limit
   nudges (3 and 8) → task ends. 1b verifier returned a broken call as its final text on rich_3882.
5. **Backtick-closed arguments (1b):** fastapi_15589 had 77 read_file calls, 75 errors — reader's `filepath` closed
   with a backtick swallowed `start_line` (`rich/prompt.py`,start_line:2…`). Orchestrator requests are full of
   markdown backticks; helpers copy them (hypothesis). Matches forum 744272 (backtick-closed strings lose arguments).
6. **Helper formats:** executor followed `CHANGED / CHECK` (2/2); reader 2/4 in format but useful as free text;
   verifier returned a broken tool call once.
7. Compaction fired in most long tasks (peak prompt ~14.4–15.3k), never overflowed.

## Next changes (one prompt round, then re-run the same 4 tasks)
- Scratch files: "/tmp files only via run_command heredoc; write_file/edit_file only for repository files; before
  submitting, delete any file you created in /workspace" (+ git status check already there).
- Tool-call hygiene: examples written as `run_command: git grep …`; "never write tool calls as text";
  no backticks in tool arguments or helper requests.
- Conventions: "match existing error messages, names and style in the same file".
- Then decide D2/D6b (1b helpers) with clean runs.
