# Rung-1x (2026-10-10): 1a round 4.1 (search+read in one git grep, large reads, keep /tmp), 2 tasks × 2

Config: commit 987f52d. fastapi_15589 1/2 (round 4: 0/2), rich_3470 0/2 (round 4: 2/2) — within noise.

| per task (2 hard tasks) | round 4 | round 4.1 |
|---|---|---|
| tool calls | 35.5 | 39.8 |
| git grep -W | – | 0.8 |
| plain grep | 12.8 | 16.0 |
| read_file | 14.0 | 14.5 |
| median read size | 23 lines | 25 lines |

The command templates were mostly ignored: the model keeps its own habit (many small greps, read_file in small
slices); rich_3470 spent 122–126 s on 26–29 searches. Together with the earlier rounds: neither behaviour rules
nor command templates in the prompt move these habits. What the model does use readily is a *tool* (read_file
despite the ban). Next options: a skill tool that does "find the symbol and show its whole definition" in one call
(D8; swegemma 0.2.10 now sanitizes skill args), the LoRA (user: after 0.15), or wait for the leaderboard result.
