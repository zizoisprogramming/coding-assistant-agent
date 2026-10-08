# Rung-1g (2026-10-08): 1b round 6 (round 4 arch + short requests + tagged notes / repro cap / helper FILES)

Config: commit a18e48c. Same 4 tasks, temperature 0.2, 3 repeats. Result **1 / 1 / 1 → mean 1.0** (round 4: 2.0).
Per task (of 3): fastapi_15588 0, fastapi_15589 0, rich_3882 3, rich_3470 0.

## Did the new parts get used?
| Part | Used? |
|---|---|
| Orchestrator appends to notes | partly: 17 appends (LOC 13, FILE 10, BASE 3, **TRIED 0**), 25 reads |
| Orchestrator `cat > /tmp/notes.md` | 21 times in 12 tasks: it **rewrites (wipes) the notes** after every compaction |
| Helpers read notes first | **1 of 34** helper calls |
| Requests point to the notes | 1 |
| Helpers' FILES line | yes, in the replies seen |
| Repro written at most twice | **no**: 4, 4, 33, 10, 6, 12, 0, 0, 0, 6, 9, 0 (84 total; round 4: 82) |
| Progress line (text) before each call | **0 of 380** orchestrator steps (round 4: 0 of 308) |

Helper speed was fine: reader 36 s, executor 23 s, verifier 23 s per call.

## Key mechanism found: compaction = amnesia + restart
- The orchestrator never writes text, only tool calls. ADK compaction summarizes **text parts only**
  (llm_event_summarizer.py:79), so the summary is near-empty; afterwards it keeps the task + last 5 events.
- fastapi_15589 r2: after each of 3 compactions (161 s, 209 s, 290 s) it restarts at Phase A step 1: rewrites
  notes.md with cat > (wiping LOC/FILE lines), git grep, sed the same lines, repro again. It never called a helper.
- So the "progress line survives compaction" idea cannot work as long as the model writes no text, and notes only
  help if step 1 does not overwrite them.

## Identical back-to-back command streaks are growing
Longest streak per task (≥5 count): 1b T1.0 rung-1b/1c: max 2 (0 of 8 tasks) · 1b T0.2 rung-1d 13 (2/12), rung-1e 15
(3/12), rung-1f 34 (4/12), **rung-1g 43 (4/12)**. Examples: orchestrator `sed -n '530,540p'` 22× in a row, ~1.3 s
apart; executor a malformed sed (`sed -n '260,270p rich/prompt.py'`, quote misplaced) 44×; repro rewritten 28×
identically. 1a at T1.0 also had streaks (20, 22, 73 in rung-1d) but those were error retries (malformed
edit_file). Low temperature is a known cause of repetition loops (Holtzman et al., "The Curious Case of Neural Text
Degeneration", ICLR 2020); our 1b data at 1.0 is small (8 task runs) and from older prompts → suggestive, not proven.
