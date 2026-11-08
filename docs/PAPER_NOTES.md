# Paper notes (paper track, due 2026-11-12)

## Predictions, written before the results of r45 and r46 (2026-11-04)
r45 information test (same agent, same run, 38 tasks):
1. Added test lines raise solves clearly on the 19 flagged tasks (from ~0 to at least 6 of 19).
2. Linked reports raise solves on the 19 short issues, but less (by 2 to 5), because finding the fix stays hard.
r46 replay probe:
3. Compliance falls gradually with distance, with no sharp step at 1024 tokens.
4. System-prompt rules are followed at least as often as far tool or user text.
5. In a conflict the model believes the tool result more often than its own claim, and the most recent source gains.
6. It believes its own claim more often than the same claim from a teammate.
These are guesses to be scored honestly; a wrong one gets reported as wrong.

### Score of the predictions (2026-11-05)
1. Test lines at least 6/19: WRONG, 5/19. 2. Reports +2 to +5: WRONG, +9. 3. Gradual fall, no step at 1024: step part right, fall WRONG (no fall). 4. System at least as strong as far tool/user: UNCLEAR (wide intervals).
5. Believes the tool more: RIGHT; recency gain: not seen. 6. Own claim over a teammate's: WRONG (0/33 vs 3/46).

Update with replay 2 (pooled): prediction 3: still no fall and no step. Prediction 4: system 50/87 (57%) vs far tool 20/34 (59%), far user 28/41 (68%): not supported as stated.

## Self-written report vs real report (r49 + r50, 2026-11-05)
Same agent family with the model writing its own bug report first, against a same-run control, 2 runs, 38 tasks each: all tasks 12 vs 14 of 76, short issues 8 vs 8 of 56. The real public report in r45 (one pass so far, different arms): reports group 1/19 to 10/19. The model's report does not replace the missing information. Caveat: the srep arms also had a 7-minute cap against the control's 8, and the report used about a third of the time, so this is a test of the whole design, not of report content alone. Its own label does not separate outcomes in r50: SHOWN yes 1/15, no 3/21.

## Closest related work (found 2026-11-04). "Abstract" = only the abstract page was read; read the full text before citing details.
- OpenAI, "Separating signal from noise in coding evaluations" and "Why we no longer evaluate SWE-bench Verified": audits finding broken tasks, including underspecified prompts (about 30% of SWE-Bench Pro per secondary coverage; the primary page returned 403 to our fetcher, so read it by hand).
- Vijayvargiya et al., Ambig-SWE / "Interactive Agents to Overcome Underspecificity in Software Engineering" (arXiv 2502.13069): removes details from good issues, tests clarifying questions. Summary only.
- Bruno et al., "Writing Bug Reports for Software Repair Agents" (arXiv 2607.09553), and "What Makes a Good Bug Report for an AI Agent?" (arXiv 2607.07593): which report features predict success. Summary only.
- Bjarnason, Silva, Monperrus, "On Randomness in Agentic Evals" (arXiv 2602.07150): 60,000 trajectories, run-to-run noise, 2-3 point gains may be noise. Abstract.
- Zhang et al., "Stop Comparing LLM Agents Without Disclosing the Harness" (arXiv 2605.23950): argues the harness can outweigh the model. Abstract. Our plateau is a counterpoint on hard tasks for one small model.
- Toeda, "Scaffolding Helps the Smallest Gemma 4 Agent, Not the Larger Ones" (Zenodo 23813680, same paper track): pre-registered, 4,056 runs, E4B +5 points, 12B and 26B no reliable effect. Record page.
- Shin, "The Compliance Gap" (arXiv 2605.01771): frontier models, process instructions, 2,031 sessions. Abstract.
- McMillan, "Instruction Adherence in Coding Agent Configuration Files" (arXiv 2605.10039): 1,650 Claude Code sessions, position no detectable effect, compliance falls within a session. Abstract.
- arXiv 2604.08281 (tool trust in math reasoning) and alphaxiv 2601.09760 (tool-memory conflict): model vs tool conflicts. Summary only.
- Gemma 3 Technical Report (arXiv 2503.19786): 5:1 local-to-global layers, 1,024-token window. Gemma 4 values: re-verify in its own report before citing.

## What looks new (absence from a few searches is not proof)
- Real, naturally thin issues with the real linked report added, under a same-run control, on a small local model.
- A plateau across 35 agent designs measured against the spread identical agents would give.
- A controlled distance test around a local-attention window with dormant rules; own text vs tool vs teammate conflict in a coding agent's real context.

## Information test pass 2 (r61, 2026-11-08)
Prediction written before the result: info >= base + 8 of 38; reports beat test lines again. Result: base 4/38, info 15/38 (+11): RIGHT. Pooled 2 passes: 6/76 vs 30/76, only info 27 vs only base 3, sign p 0.00001; info solved the same 13 tasks in both passes. Group split still to redo with r45's grouping.
