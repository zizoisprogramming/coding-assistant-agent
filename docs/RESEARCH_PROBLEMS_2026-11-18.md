# Why the model ignores instructions, and the other failures we keep hitting (2026-11-18)

User request: "full research pass once more on the common mistakes the model fails like ignoring instructions, and look
at research passes we did before". Builds on docs/RESEARCH_PROBLEMS_2026-11-12.md (12 problems), docs/PAPER_NOTES.md
(two controlled replay probes, 11-04 / 11-05) and memory event-triggered-rules-only. "Ours" numbers come from the run
bank (docs/PLAN.md entries in brackets). Sources marked *secondary* were read only as summaries.

## 1. What the model follows and what it ignores (our bank, all channels side by side)

| Channel | Example | Followed | Source |
|---|---|---|---|
| Agent structure: a stage exists, a tool is missing | setup stage installs; history stage runs; fixer without submit hands over | 24/24, 8/8, 16-18/20 | r57, r113, sk_fr |
| Tool-output BLOCK (the tool refuses) | refusal -> edit next call | 5/7, 6/8 | 11-02 clock runs |
| Static prohibition in the prompt | no test-file edits, nothing outside /workspace | ~99% (0.6% test edits) | 11-12 check, 342 runs |
| Example format that matches work the model does anyway | heredoc check, pytest, plain-text edit blocks | 72%, 49% of runs; garbles 22 -> ~3/24 | sb1 x 162, sa2 |
| User-role text near the decision | replayed rule as user text | 83% | replay probe 11-05 |
| Tool-output instruction to do a specific next step | sb5 NEXT line | 2/3 | r110 |
| Tool-output soft advice | low-call warning -> edit within 2 calls | 15/67 (22%) | 11-02 |
| A new step written into the prompt or examples | history step, install first, finish steps | 1-5/162, 0/8, 1/24, skipped 19/24 | sb1, sb6 (r112), r55, sa2 |
| Stop / length / hand-over rule in a stage prompt | scouts "be quick, stop"; sb7 history "one call"; sb8 explorer hand-over | 129-242 s; stopped 2/8; handed over 3/8 | r60, r113 |

Pattern: the model does what it would do anyway, what the structure forces, and what a tool blocks. It drops any extra
step it does not itself see a need for, and any rule about its own pacing (stop, hand over, be brief). When it drops a
rule its reasoning almost never mentions the rule (1/143, replay 11-05). Distance in the context does not matter (no
decay, no step at 1,024 tokens, replay 11-05).

## 2. What the literature says about this

- **Extra instructions are dropped under task load ("prospective memory").** Instructions that must be remembered while
  a demanding task runs are lost; a salient reminder at the right moment restores 90-100% compliance
  ([Did You Forget What I Asked?, arXiv 2603.23530](https://arxiv.org/html/2603.23530)). Matches our table: the same step
  works as a tool-output line at the moment (NEXT 2/3) and fails as a prompt step (0-5%).
- **Reasoning pulls attention away from instructions.** Explicit chain of thought lowers instruction following; the
  thinking text attends less to the instruction tokens; selective reasoning recovers it
  ([When Thinking Fails, NeurIPS 2025, arXiv 2505.11423](https://arxiv.org/abs/2505.11423)). Our long replies are
  ~9,700 chars of thinking (r112), exactly where rules get lost.
- **Procedures are not executed faithfully even when understood** ([When LLMs Stop Following Steps, arXiv 2605.00817](https://arxiv.org/pdf/2605.00817), abstract).
- **Steering the thinking itself works** (insert instruction text into the reasoning: +6.7% instruction following,
  +15.4% instruction hierarchy, less overthinking; [Thinking Intervention, arXiv 2503.24370](https://arxiv.org/html/2503.24370v3)).
  Not open to us: the harness owns the request; we cannot write into the model's thinking.
- **Reminders re-injected during the run reduce plan violations** (16,991 SWE-agent trajectories, *secondary*:
  [agentpatterns.ai](https://agentpatterns.ai/patterns/agent-design/plan-compliance-in-agents/)); practitioners append
  instructions to tool results at key moments ([Ona](https://ona.com/stories/rethinking-the-todo-tool)). No rigorous
  ablation found.
- **Prohibitions vs required actions:** an ICML 2026 study found prohibitions decay over turns (11-12 pass, row 8). Not
  our case: ours hold; our ignored rules are required steps and pacing.

## 3. The other recurring failures (updated)

| # | Failure | Ours (latest) | Literature | Status |
|---|---|---|---|---|
| A | Hand-tracing code in very long replies instead of running it; no edit before the clock | replies >= 60 s = 11% of replies but 58% of model time in time-ended runs, ~11 'Wait / Actually' each, 20/24 end in another read (r112) | Overthinking / analysis paralysis ([2502.08235](https://arxiv.org/pdf/2502.08235)); suppressing reflection tokens ('Wait') cuts reasoning 27-51% with accuracy kept on R1-style models ([NoWait, arXiv 2506.08343](https://arxiv.org/abs/2506.08343v2)); cutting reasoning 10-30% keeps easy code tasks, hurts hard ones ([arXiv 2511.05874](https://arxiv.org/pdf/2511.05874)); small models degenerate into unproductive exploration ([SWE-Protégé, 2602.22124](https://arxiv.org/pdf/2602.22124)) | Thinking caps closed (r13, r111: thinking spreads to more replies). Logit bias is not a submission field. **presence / frequency penalty are untested** (see 4) |
| B | Context lost at the edit (compaction) | real-fix lines visible at the first edit: solved 76% vs failed 47% (352 runs) | implicit compression hurts SWE agents ([2605.11051](https://arxiv.org/pdf/2605.11051)) | compaction is the scorer's; pinning via system prompt works only through stages |
| C | Right lines, wrong logic | 49% of failed edits on the real-fix lines | Coherence Collapse ([2603.24631](https://www.alphaxiv.org/abs/2603.24631)) | history at the edit: not adopted (sb6 0/8); test check net zero (testcheck) |
| D | Second stage starved | sb3-sb5, sb8: explorer ~400 s, hand-over 3/8 | - | closed (8-minute cap) |
| E | One-call stage does not stop | sb7: 2/8 stopped | stage length must come from structure (memory, r60) | r114 tests a stop line in the tool output (soft advice: 22% base rate, so expect a partial effect at best) |
| F | Garbled tool arguments | alphabetical argument order + vLLM quote bug (11-09, 11-12) | [vLLM #39070](https://github.com/vllm-project/vllm/pull/39070) | plain-text examples fixed most |

Gemma 4 community reports (loops, malformed calls, missing reasoning after the first tool call on 31B) mostly blame
chat templates, parsers and quantization, and Google shipped a quiet fix for tool calling
([the-decoder](https://the-decoder.com/gemma-4-gets-a-stealth-update-that-fixes-tool-calling-bugs-and-truncated-responses-under-the-same-name/),
[HF #119](https://huggingface.co/google/gemma-4-31B-it/discussions/119)). Those are the scorer's, not ours to set.
Nothing public on this competition's leading approaches was found (search 11-18).

## 4. Levers still open (each with its basis and risk)

1. **presence_penalty / frequency_penalty (new, never tried).** Allowed by the scorer (adk_submission limits: no field
   list) and forwarded by ADK to vLLM as `presence_penalty` / `frequency_penalty` (google/adk/models/lite_llm.py).
   They penalise tokens already generated in the same reply, so 'Wait' x11 gets pushed down (the NoWait mechanism,
   softened). **Risk:** the same penalty hits code identifiers the reply already used in its thinking, so edit text
   could drift (wrong names, garbled old_string). No study of penalties on reasoning length found. Test: a small arm
   (presence 0.3-0.5) with bars on reply length, long-reply share, and failed / garbled edits.
2. **Make needed steps blocks, not advice.** Only harness mechanisms can block: the call budget ("Tool call budget
   exhausted" -> submit is followed) and missing tools per stage. Everything else is advice.
3. **Put the step where the model already acts (format adoption).** Steps that ride on what the model does anyway
   (heredoc 72%) are adopted; standalone steps are not. sb6 tried this for history inside the edit sequence and failed
   (0/8): riding on a habit is necessary, not sufficient, when the model sees no need for the step.
4. **User-role channel.** User text was the most obeyed (83%) in the replay. Mid-run, ADK delivers a finished stage's
   reply to the next stage as 'For context: [agent] said' user text; that is the only user-role channel open to a
   submission, and it exists only at stage boundaries.

## 5. What this means for the next agents

- Stop proposing prompt steps the model must remember. A behaviour change needs structure, a block, or a habit the
  model already has.
- The biggest single cost left is item A (long hand-tracing replies). Thinking caps backfired; sampling penalties are
  the one untried knob that acts on it, with a real risk to code fidelity that a small trial can measure.
- r114 (sb7s) is the last test of soft tool-output advice for stopping a stage; its base rate says expect a partial
  effect at best.
