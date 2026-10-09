# Rung-1m (2026-10-09): 1a round 3 (free fixes + thinking on), 2 repeats

Config: commit 1652543 + thinking (7fd9680). Baseline = 1a_think from rung-1l (same thinking settings, reference
prompt): 1/4, 2/4. Round 3: **1/4, 1/4** (rich_3882 both). The 1-task gap is within noise; one loss
(fastapi_15589 r2) came from a new failure caused by the prompt (below).

## Fix usage vs 1a_think
| | 1a_think | round 3 |
|---|---|---|
| edit_file errors | 10 of 29 | **2 of 13** |
| read_file | 69 | 33 (+ 41 sed reads) |
| repro.py writes | 35 | 31 (cap of 2 ignored) |
| pytest runs | 10 | 5 |
| notes: resume cmd / appends / reads | – | 6 / 3 / 0 |
| text tool-call replies | 0 tasks | **3 of 8 tasks** |

## New failure: the step-1 command written as text
In 3 tasks the model's 1st or 2nd reply was the step-1 notes command written as **plain text**
("run_command: test -s /tmp/notes.md && cat ... || cat > /tmp/notes.md << 'EOF' ...") instead of a tool call;
fastapi_15589 r2 then kept writing calls as text (2,048-token replies, 2 "token limit while thinking" nudges) and
ended with no tool call at all. 1b round 7's rich_3882 failure (rung-1j) started the same way. The reference
prompt also has 6 "run_command: ..." examples and never triggered it; round 3 adds a multi-line block introduced
with "always exactly this form" → the model reproduces the block verbatim as text.
**Fix (proposed):** step 1 as two single-line calls: `cat /tmp/notes.md 2>/dev/null || echo NO_NOTES`, then the
heredoc only if NO_NOTES; never present a multi-line command as an exact form.
