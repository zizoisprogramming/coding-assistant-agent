# Gemma 4 Developer Agent — Competition Plan (living doc)

## >>> START HERE (session handoff, written 2026-09-26) <<<
**Where we are:** research + design discussion done (all findings below). Nothing built yet. User is a beginner
to agents/ADK; wants learn-by-building, step-by-step explanations, research-backed answers (see memory), and
decides personally when planning ends.

**Decisions so far:** single self-planning executor first (rung 1), then add verifier → planner → replanner one at
a time, measuring each (ablation ladder = paper core). Testing tiers: Mac + Ollama `gemma4:12b` (num_ctx 32768,
saved as `gemma4-12b-32k`) → Kaggle L4×4 notebook with real 31B W4A16 → 1 LB submission/day. Hosted APIs dropped.
No Claude/GPT distillation; Qwen3.6-27B (Apache 2.0) is the teacher candidate once LoRA works.

**Tomorrow's agenda (agreed):**
1. Walk through `data/sample_submission/` line by line (agent.yaml, prompts/system.md, configs/sampling.yaml,
   eval_config.yaml, sub_agents/code_analyzer.yaml) — explain how YAML becomes a running agent.
2. User runs host notebook `ryanholbrook/getting-started-gemma-4-developer-agent` on Kaggle (L4 GPU, Run All) —
   watch the agent loop on 2 tasks + measure quota burn (15 min).
3. Write our rung-1 `submission/agent.yaml` + `prompts/system.md` together (see "NEXT" section).

**Files saved for the new session (copied from session scratchpad on 2026-09-26):**
- `data/` (gitignored): tasks.jsonl, HARNESS_README.md, sample_submission/, docker/, sandbox/.
- `research/raw/` (gitignored): pages/ (official comp pages), paper/ (paper-track pages), forum/ (threads.txt),
  kernels/ (public notebook sources), harness_src/ (swegemma 0.2.7, adk-submission 0.2.11, adk-eval-core 0.1.0),
  all_files.json (dataset file list), wheelhouse_files.txt.
- `scripts/kaggle_api.py`: tiny Kaggle API helper (reads token from ~/.kaggle/access_token).
- `docs/PLAN.md`: copy of this plan. `CLAUDE.md`: short project brief pointing to docs/PLAN.md.
- Not copied (re-downloadable): snapshots (21.5 GB), graphs/embeddings.

**User to-dos status (2026-09-26):** joined BOTH tracks (verified via API: userHasEntered=true); chose to keep the
current Kaggle token (user decision); `ollama pull gemma4:12b` in progress → then set num_ctx 32768 and
`/save gemma4-12b-32k`.

## Context
Kaggle "Google – The Gemma 4 Developer Agent Competition" (Google DeepMind, Featured, $65k) + optional
Paper Track ($35k). Goal: turn `gemma-4-31b-it-qat-w4a16-ct` into an autonomous SWE agent that fixes Python
bug-fix / feature-request tasks offline. Repo `coding-assistant-agent` is empty (README only) — greenfield.
Working mode: learn + build, $0 compute (Kaggle only), both tracks.

## NEXT: Build P0 + Rung 1 (single self-planning executor) — decided 2026-09-26
Goal: an end-to-end loop (pack → local smoke test → Kaggle 31B dev eval → first LB submission) with the
simplest agent, so every later idea (verifier, planner, skills) is measured against a real baseline.

### Step A — Repo setup (P0)
- `.gitignore`: `data/`, `research/raw/`, `results/`, `*.tgz`, `*.zip`, `.venv/` (competition data must not be
  redistributed).
- Copy scratchpad material into the repo before the session ends: `data/` (tasks.jsonl, sample_submission,
  HARNESS_README.md, docker/, sandbox/), `research/raw/` (pages/, paper/, forum/, kernels/, harness src/).
- `pyproject.toml` via `uv` (Python 3.13 to match sandbox); install from the wheelhouse dataset: swegemma 0.2.7,
  adk-submission 0.2.11, adk-eval-core 0.1.0, google-adk 1.36.1 (+ their deps) — skip the Linux-only vLLM.
- `scripts/fetch_data.py`: Kaggle API (token file) → download a dev subset of snapshots + graphs/embeddings;
  fix 0-byte graph/embedding files by hard-linking to the readable copy per commit (forum 742911).
- Docker sandbox: `colima start`, build `swebench-sandbox:latest` from `data/docker/Dockerfile.public`.

### Step B — Rung 1 submission (`submission/`)
- `agent.yaml`: one LlmAgent `executor`, model `gemma-4-31b-it-qat-w4a16-ct`, tools: run_command, read_file,
  edit_file, write_file, get_status, submit_patch. Graph tools OFF for the baseline (async-blind, symbol-only
  queries) — added later as an ablation.
- `prompts/system.md` sections: (1) situation — autonomous, nobody answers, every turn needs a tool call until
  submit; (2) self-plan — first turn writes TASK SPEC (exact names verbatim, expected/actual, done-when) + 3–6 step
  plan to `/tmp/plan.md` via run_command, re-read it after a failed check; (3) localize — git log/grep/-S/show,
  `git grep -n … | head`; (4) reproduce in `/tmp/repro.py` before editing, note pre-existing failing tests;
  (5) small `edit_file` edits, never tests/config/pytest.ini/conftest.py; (6) re-run repro + nearest tests;
  (7) pre-submit check `git status --short` + `git diff --stat` (no scratch files, non-empty); (8) submit, then one
  short text reply. Plus: safe/forbidden git list, output hygiene (`| head -40`, read_file ≤80 lines), no `rg`/
  `tree`/pip, budget via free `get_status`.
- `configs/sampling.yaml`: temperature 0.2, top_p 0.95, max_output_tokens 8192, `include_thoughts: false`
  (thinking off first; thinking_budget isn't forwarded — thinking-on is a later ablation).
- `eval_config.yaml`: max_time_minutes 5.0, timeout_seconds 240, max_tool_calls 45, max_turns 90
  (~120 tasks × (5 min + setup) must stay < 12 h).

### Step C — Tooling (`scripts/`)
- `pack.py`: zip `submission/` with agent.yaml at root; validate with swegemma `ALLOWED_SUBMISSION_EXTENSIONS`,
  `MAX_SUBMISSION_SIZE_BYTES`, `validate_single_declared_model`, and `compile_submission()` (reuse the host
  notebook's packaging cell logic).
- `eval_local.sh`: `swegemma eval --sandbox docker --task-ids … --submission-dir submission` with a models-yaml
  mapping the competition alias → local Ollama (`gemma-4-12b-it-qat-q4_0` GGUF, num_ctx 32768).
- `analyze.py`: read `summary.json`, `task_results.jsonl`, `traces/` → resolve rate, time/tool-calls per task,
  failure buckets (no patch, context overflow, timeout, wrong fix, tool errors, test-file edits).
- `kaggle/eval_31b.ipynb`: adapted from `ryanholbrook/getting-started-gemma-4-developer-agent` (wheelhouse install,
  VllmServer TP=4, Evaluator with subprocess sandbox) running our `submission/` on the dev subset.
- `experiments/<date>_<name>/`: config snapshot + summary + notes.md (paper log from day 1).

### Step D — Dev subset & baseline
- ~20 tasks across fastapi/rich/requests, mixed sizes incl. title-only ones; keep only tasks whose gold patch
  passes locally (gold-patch positive control; see notebook `busyaprime/119-of-129-sound-…`).
- Run rung 1 on Kaggle 31B → baseline resolve rate + failure buckets → first LB submission.

### Verification
- `scripts/pack.py` passes all validators and `compile_submission()` returns the agent tree.
- Local: 2–3 tasks on Mac (12B via Ollama, Docker sandbox) produce patches, traces and logs without harness errors.
- Kaggle: 20-task 31B run completes with a resolve rate; first LB submission scores (not error).
- First measurement to take: L4×4 quota burn rate (15-min test).

### User actions
- Rotate the Kaggle API token; join the paper track.

Sources pulled 2026-09-26 via Kaggle API (token in ~/.kaggle/access_token): competition pages (Overview,
Evaluation, Rules, Data, Model/Budget/Harness Rules, Timeline, Prizes), paper track pages, leaderboard CSV,
forum threads, public notebooks (incl. host's Getting Started), dataset file list, HARNESS_README.md,
tasks.jsonl, sample_submission. Local copies: scratchpad `data/`, `pages/`, `paper/`, `forum/`, `kernels/`.

## Competition facts (VERIFIED unless marked)
### Timeline & limits
- Main: final submission **Dec 2, 2026** 23:59 UTC; entry + team merge deadline Nov 25. Team size ≤5.
- **1 submission per day** (a failed run still burns the slot). Pick **2 final submissions**.
- Paper: **Nov 12, 2026**. Joined (verified 2026-09-26).
- Winners must open-source (OSI license, Apache 2.0) the solution + training code, reproducible write-up.
- **Competition data must not be redistributed** → keep `data/` out of any public git repo.
- External data/models allowed if public and free/cheap ("reasonably accessible to all").
  Distillation from proprietary LLMs (Claude/GPT) → **host answer pending** (forum 742807). Open-weight
  teacher models are the safer route. Also mind provider ToS.

### Scoring
- Per task PASS/FAIL (SWE-Bench-style). Score = fraction resolved. Kaggle truncates to 2 decimals.
- Hidden test set ≈120 tasks, split ~50/50 public/private LB. **Public LB = exactly 58 tasks** (forum
  743506 deduction) → **1 task ≈ 0.017**; LB is noisy — a 1-task change is noise.
- **Hidden test set is from PRIVATE repositories** (Data page). Public 129 tasks (fastapi 67, rich 48,
  requests 13, httpx 1) are only a dev set → optimise for generalisation, not these 4 repos.
- Test tasks were filtered so "a larger frontier model can pass the case or get within a single test".
- Verification: fresh container, apply patch (4 fallback strategies), reset any test/config files the agent
  touched, apply hidden test_patch, pytest target tests. Resolved iff exit 0, >0 passed, 0 fail/err, not skipped.
  Unsubmitted working-tree diffs are still extracted and scored.

### Runtime budget
- **12 h total** for all tasks (includes sandbox setup, excludes validation). Tasks run **sequentially**.
  Exceeding 12 h currently **errors the whole submission** (host plans to score unfinished as 0).
  → ~6 min/task average. Always set `max_time_minutes` as a failsafe.
- Scorer reads only 4 `eval_config.yaml` fields: timeout_seconds, max_tool_calls, max_time_minutes,
  max_turns. Default = no limit. `timeout_seconds` also bounds the Phase-2 pytest run → keep ≥180–300.
- Hardware: 4×L4 (96 GB), vLLM 0.19.1 (patched), TP=4, max_model_len **32,768**, gemma4 tool/reasoning parser.

### Leaderboard now (348 teams, 613 submissions)
- Top = **0.13** (8/58). Distribution: 0.13×4, 0.12×25, 0.10×30, 0.08×42, 0.06×54, 0.05×46 … 0.00×119.
- Best public notebook (romanrozen, coder + read-only code_analyzer, LOCATION/ROOT CAUSE/FIX PLAN format,
  temp 0.2) = 0.12; a direct fork scored 0.08 (noise!) and took 14.5 h wall clock.
- Many recent runs fail platform-side ("requested more CPU/GPU/TPU than available") — host is fixing.

### Submission format (ADK Agent Config, declarative YAML only)
- `submission.zip` with `agent.yaml` at root; optional eval_config.yaml, configs/, prompts/, sub_agents/,
  adapters/<name>/{adapter_config.json, adapter_model.safetensors}, skills/<name>/{SKILL.md, scripts/, resources/}.
- ≤3 GiB unpacked. Extensions allowed: .yaml .yml .md .txt .py(skill scripts) .json .safetensors.
- Agent classes: LlmAgent, SequentialAgent, ParallelAgent, LoopAgent; `agent_tool` for sub-agents
  (context isolation); `{problem_description}` available in instructions; one base model for all agents.
- Sampling: `include_thoughts: false` ⇒ thinking fully OFF; `thinking_budget` is NOT forwarded to vLLM
  (forum 743365), so with thinking on only `max_output_tokens` bounds reasoning. `thinking_level` should be omitted.
- Context compaction configured (threshold 14,336 tokens; interval 5 in README vs 15 in host notebook) —
  whether it actually fires is questioned (forum 743456). Design as if it doesn't: keep outputs small.

### Tools (9) + gotchas
run_command, submit_patch (free), get_status (free), read_file (≤150 lines/10k chars), edit_file (3-tier fuzzy
match), write_file, get_code_neighbors, search_similar_code (takes a SYMBOL name, not natural language),
get_code_subgraph; plus skill helpers run_skill_script / load_skill_resource.
- Output cap 5,000 chars (first 5k). Command timeout 300 s. Sandbox offline, 4 GB RAM, 2 vCPU.
- **`rg` and `tree` are not installed** → use `git grep -n`.
- Scratch files in /workspace get into the patch → use /tmp. Don't touch pytest.ini / conftest.py.
- Pinned vLLM parser may pass int/bool tool args as strings (happyc0der) → e.g. read_file line ranges fail.
- **No GitHub/network access** (verified): Docker network_mode none; sandbox image = python:3.13-slim + git,
  patch, protobuf-compiler, pigz, pytest (+pytest-timeout), typer, build backends. No `gh`, `rg`, `tree`, `curl` use.
  Snapshot has no git remote. → `gh issue view`, `pip install`, web lookups all impossible.
- **Full LOCAL git history up to base_commit IS available** (verified on requests_7505: 6,475 commits back to
  "first commit", `git blame`/`git log`/`git show` work, branches main + export_ref). Example: issue says
  "successor to #7502" and HEAD is exactly "Fix `_encode_files` detection … (#7502)" → `git show HEAD` reveals the
  pattern to replicate. → Scaffold lever: teach `git log --oneline -15`, `git log -S'<symbol>'`, `git log --grep`,
  `git show <sha> --stat`, `git blame -L` for localisation/spec recovery (esp. title-only tasks).
- **Git safety** (verified: container_setup.py:581 tags baseline `_swegemma_baseline`; patch = `git diff --binary
  _swegemma_baseline` of the final working tree, execution.py:84 / agent_runner.py:767). Git is just bash via
  run_command → rules can't be enforced, only prompted + verifier-checked.
  - Encourage (read-only, bounded output): git log --oneline -n/--grep/-S, git show --stat / -- file, git blame -L,
    git grep -n | head, git diff --stat, git status --short.
  - Forbid: git checkout -- / restore / reset --hard (lose edits), git stash (empty patch if not popped / timeout),
    git clean -fd (deletes new files), checkout other commits/branches (huge wrong diff), touching the
    _swegemma_baseline tag, rebase/merge/cherry-pick. git commit is harmless (diff is vs tag) but pointless.
  - Baseline failing tests: record BEFORE editing, never via stash. Verifier runs git status/diff --stat pre-submit.
- **Graphs/embeddings contain NO async functions** (0/305) → graph tools blind to async code (fastapi!).
  Half of graph/embedding files are 0-byte in download + Kaggle mount (hard-link issue).

### LoRA status
- Only LoRA adapters accepted (no full fine-tunes). PEFT safetensors, rank ≤128, ≤8 adapters, per-agent.
- **Currently broken**: patched vLLM 0.19.1 loads adapters but resets their weights to zero (forum 743508);
  PyPI vLLM refuses LoRA for Gemma4. Official sample (with adapters) also FAILED. Watch for host fix.
  → LoRA is not usable today; prompt/scaffold is the only working lever right now.

### Harness packages
- Kaggle dataset `metric/gemma-4-developer-agent-wheelhouse`: swegemma 0.2.7, adk-submission 0.2.11,
  adk-eval-core 0.1.0, google-adk 1.36.1, vllm 0.19.1 (patched, x86 Linux), transformers 5.13.1, flashinfer.
- Host notebook `ryanholbrook/getting-started-gemma-4-developer-agent` runs the real 31B model + Evaluator
  on a **Kaggle L4 notebook** (subprocess sandbox; no Docker on Kaggle). → We CAN run real-model local evals
  on Kaggle for free (quota for L4×4 = UNVERIFIED; check account; queues reported).
- Public wheels miss some test deps (typing-inspection, inline-snapshot, dirty-equals, pytest-httpbin) →
  some gold patches fail locally. Need a "gold-patch positive control" run to know which dev tasks are valid.

### Verified from harness SOURCE (swegemma 0.2.7 / adk-submission 0.2.11 / adk-eval-core 0.1.0)
Unpacked in scratchpad `src/` — read the code when README and forum disagree.
- **"Custom tools" = skills.** YAML tool names only resolve against the closed ToolRegistry (the 9 tools) +
  `agent_tool`. The only way to ship our own code is `skills/<name>/` (SKILL.md + scripts/ + resources/),
  exposed via ADK SkillToolset (`run_skill_script`, `load_skill_resource`). Scripts run as `python3` inside
  the task sandbox (same FS as run_command, /workspace cwd), timeout = timeout_seconds, debit the time budget.
  Temp script files are git-excluded and deleted → no patch pollution. (Forum 743573 asks the same; no answer yet.)
  → Big lever: e.g. a repo-map / async-aware symbol search / test-finder script written in Python.
- **Callbacks**: CallbackRegistry exists but swegemma registers none → no callbacks usable.
- **No MCP** (verified): ADK supports MCP via `McpToolset`/`to_mcp_server` but only in Python agent code; the
  competition compiler is YAML-only, `tools:` = `list[str | AgentToolEntry]` resolved against the closed registry,
  and "mcp" appears nowhere in swegemma/adk-submission/adk-eval-core. Mapping: harness = tool server, ADK agent built
  from agent.yaml = client, skills = our only custom tools. Our Python lives in skill scripts (CLI, compact output)
  and local tooling (pack, eval runner, analyzer, trajectory builder, LoRA training, Kaggle notebook).
- Task prompt (`build_agent_prompt`): repo + problem statement, budget lines, env rules, instructions 0–5
  (incl. "final action must be a text-only response"), graph-tools blurb only if graph+embedding files >100 B,
  plus `find . -maxdepth 3 | head -150` workspace tree. Our system prompt sits on top of this.
- Tool signatures use typed params (`start_line: int | None`) — consistent with the string-vs-int parser issue.

- **No human in the loop** (verified agent_runner.py L677–739): one initial task message, then only 3 canned
  nudges ("Please continue… or call submit_patch", token-limit variants). Counter resets on any tool call;
  3 consecutive text-only turns → task ends and the working tree is graded as-is. Questions get the canned nudge.
  → Scaffold rule: never ask, resolve ambiguity from issue wording / code conventions / tests, every turn must
  contain a tool call until submit_patch, then one short text reply to end.

### Models available for local work (Kaggle Models, google/gemma-4)
- Competition: `other/gemma-4-31b-it-qat-w4a16-ct` v2 (23.3 GB). Same family: **`gemma-4-12b-it-qat-w4a16-ct`**
  (10.3 GB) — a proxy with the same quantisation/format for cheaper Kaggle runs.
- GGUF: `gemma-4-12b-it-qat-q4_0-gguf` (7.2 GB — fits Mac M5 16 GB via llama.cpp), 31B gguf 18.9 GB (too big).
- Unquantized QAT checkpoints `gemma-4-31b-it-qat-q4_0-unquantized` (62.6 GB bf16) — the likely base for LoRA
  training (adapter must target `google/gemma-4-31b-it-qat-w4a16-ct` modules; verify when LoRA is fixed).
- All Apache 2.0.

### Forum status notes (2026-09-26)
- Host says the resource-error failures are fixed and affected submissions will be **re-run Monday** (743683).
- Other LB posts: bare-bones configs score 0.08; thinking off + coder/analyzer = 0.10; top 0.13.

### Paper track
- Kaggle Writeup ≤3,000 words (title, abstract, intro, methods/experiments, related work); optional public
  notebook / arXiv PDF. Judged 0–5 on Novelty, Quality (generalisation), Relevance, Verifiability, Clarity.
- Suggested topics: PEFT/RL for SWE agents, code-graph generation/embeddings, new tasks/benchmarks, graph reasoning.
- Paper angle candidates from what we've found: async-blind graphs → repaired graph + effect on localisation;
  context-budget management under 32k; cheap scaffolds for small local models.

## Our compute (user's Kaggle quota, 2026-09-26)
- GPU 30 h/week, TPU 20 h/week, "AI Models" $10/day & $100/month, LB submissions don't use quota.
- UNVERIFIED: whether L4×4 burns quota at 1× or 4× wall-clock → test: run host notebook 15 min, check quota.
  If 1×: ~10 real-31B dev evals/week (20 tasks ≈ 2 h + 10–20 min vLLM startup). If 4×: ~2–3/week, lean on
  Mac proxy (small Gemma 4 via MLX/llama.cpp) for plumbing.
- AI Models credit = hosted models via `kaggle-benchmarks` in notebooks (model list UNVERIFIED). Uses: failure
  triage / LLM-judge of trajectories (safe); teacher for SFT trajectories only if distillation ruling allows.
- TPU: only relevant for LoRA training (JAX/Keras) once adapters work in scoring.

## Local dev setup (Mac M5, 16 GB unified, macOS 27)
- Installed: Ollama (/usr/local/bin/ollama), Docker via Colima (not running → `colima start`). No llama.cpp/LM Studio.
- Model: Kaggle `gemma-4-12b-it-qat-q4_0-gguf` (7.2 GB, same QAT lineage) loaded into Ollama via Modelfile;
  fallback `ollama pull gemma4:12b` (Q4_K_M, 7.6 GB, tags: tools, thinking). Set num_ctx 32768 (default 4k!).
- Memory estimate: ~7.5 GB weights + ~3–6 GB KV at 32k (40/48 layers sliding-window 1,024) ≈ 11–13 GB —
  close to macOS default GPU wired limit (iogpu.wired_limit_mb=0 → default). Measure; raise limit or cut ctx if needed.
- Harness: `swegemma eval --sandbox docker` locally; route `gemma-4-31b-it-qat-w4a16-ct` alias → Ollama's
  OpenAI endpoint via `--models-yaml` (harness uses LiteLLM `openai/<model>` + api_base).
- Use for: plumbing, compile checks, workflow/prompt smoke tests, skill-script development.
  NOT for: score prediction (12B ≪ 31B) or tool-parser quirks (Ollama ≠ vLLM gemma4 parser). Speed unmeasured.
- UNVERIFIED: Ollama Gemma 4 tool-call reliability over long sessions; swegemma install on macOS without vLLM.
- **31B does NOT run usefully on the Mac** (checked 2026-09-26): Ollama gemma4:31b Q4_K_M 20 GB, official QAT
  Q4_0 GGUF 18.85 GB (Unsloth: needs ~18 GB RAM), Unsloth Q4_K_M 18.25 GB (recommends 32 GB). 2-bit quants
  (~9–10 GB) fit but quality collapses and ≠ scorer's W4A16 → not a valid baseline; overflow → swap, unusable.
  → Real 31B baseline = Kaggle L4×4 notebook (same model file + vLLM 0.19.1 as scorer); LB = daily confirmation;
  Mac = 12B for plumbing only. T4×2/llama.cpp (~12 tok/s) not worth it.
- **Local proxy candidates (researched 2026-09-26):**
  - gpt-oss-20b (Apache 2.0, MoE 20.9B/3.6B active, MXFP4 ≈12.8–13 GB, 128k ctx): SWE-bench Verified 53.3%
    (medium) / 60.4% (high) per OpenAI model card — numerically closest to Gemma 31B's 53.9% (Vals). BUT different
    harnesses → numbers not directly comparable; fit on 16 GB with 32k ctx is tight (may need iogpu limit raise) — UNVERIFIED.
  - Gemma 4 12B QAT (7.2 GB): same family/chat template/tool-call format/quirks as the competition model; weaker.
    Vals has no 12B page; third-party numbers inconsistent (unreliable).
  - Ruled out: Devstral 24B (46.8% Verified, ~14 GB → no room for 32k ctx), Gemma 4 26B-A4B (≈18 GB at 4-bit;
    one source 17.4% Verified), Qwen3.6-27B/35B-A3B (too big for 16 GB).
  → DECISION: Gemma 4 12B stays the primary local proxy (behavioural fidelity > benchmark match: prompts and
    tool-format quirks are family-specific). gpt-oss-20b optional second opinion: a prompt change that helps both is
    more likely to transfer. Real numbers only from 31B on Kaggle.
- **Hosted Gemma 4 31B (researched 2026-09-26):**
  - Vertex AI MaaS: Gemma 4 not listed as of Apr 2026 (only Gemma 3) — skip.
  - **Gemini API / AI Studio serves `gemma-4-31b-it`** (official Gemma docs; tool calling supported, 256K ctx).
    Pricing page: **free tier "Free of charge"; paid tier "Not available"; free-tier content used to improve products.**
    Rate limits per project, only visible in AI Studio console (UNVERIFIED numbers). Harness retries 429s (ModelRetryPlugin).
  - Hook-up: swegemma models-yaml → LiteLLM `gemini/gemma-4-31b-it` + GEMINI_API_KEY, local Docker sandbox on Mac.
  - Fidelity gaps vs scorer: likely bf16 not W4A16 (UNVERIFIED); Google's server parses tool calls (not vLLM gemma4
    parser → string/int quirks won't show); **no 32k wall** (256K) → context-overflow failures hidden unless we enforce
    a 32k cap ourselves; thinking config mapping may differ.
  - Data caution: sending task text/code to a free API that trains on it; rules forbid giving Competition Data to
    non-participants. Public tasks are public GitHub PRs and Google is the sponsor → low risk, but keep usage to dev
    tasks and don't paste anything private.
  - Other paid hosts: OpenRouter ($0.08/$0.30 per M tokens; also a `:free` variant), Together ($0.20/$0.50) — fallback.
  → DECISION (user, 2026-09-26): **drop the hosted API entirely** — the 256K window hides context-overflow
    failures, plus parser/precision/data-use gaps. (Possible workaround — count runs >32k tokens as failures from trace
    token usage — noted but not pursued.)
  → Testing tiers: Mac + Gemma 4 12B (offline plumbing, format fidelity) → Kaggle L4×4 31B W4A16 (numbers we
    trust) → LB (daily confirmation).

## Levers (ROI order, given LoRA is broken today)
1. Scaffold + prompt: localize → reproduce (in /tmp) → minimal edit → targeted test → submit. Short outputs.
2. Budget config: thinking on/off tradeoff vs the 12 h cap; failsafe per-task limits.
3. Sub-agents/skills for context isolation (analyzer AgentTool), skills with helper scripts (e.g. repo map,
   async-aware search) — skill scripts can run Python inside the sandbox.
4. LoRA SFT once the host fixes adapter loading (trajectories from public tasks / open datasets).
5. RL — likely out of reach at $0.

## Phases (draft)
- P0 Setup: join paper track; repo scaffold (+ .gitignore data/); download data to repo `data/`;
  install wheelhouse locally for compile/validate checks (Linux-only vLLM isn't needed on Mac).
- P1 Eval loop on Kaggle L4 notebook: run subset of dev tasks with our submission dir; gold-patch control.
- P2 Scaffold iteration with 1 LB submission/day, one hypothesis each, logged in experiments/.
- P3 LoRA if fixed. P4 Paper by Nov 12, final picks by Dec 2.

## Why Gemma scores 54% elsewhere but ≤13% here (researched 2026-09-26)
- Vals AI 53.92% SWE-bench Verified = **mini-swe-agent** (bash-only, no tool-calling API, stateless
  subprocess per command, fully linear history, ~100-line agent), **150-step cap**, provider default config with
  max output tokens maxed, 500 human-validated tasks. Precision/context not stated — almost certainly bf16 via an
  API with the full 256k context (UNVERIFIED).
- Our room: 32k context, W4A16, ~6 min & sequential budget, 9 JSON tools via vLLM gemma4 parser, private repos,
  tasks filtered by frontier-model solvability.
- **Key paper: "An Empirical Study of Harness Design for Coding Agents" (arXiv 2609.20804):**
  - Context management is the dominant factor: managed vs unmanaged = **+35.7 pts at 32k** (2.7 pts at 128k);
    unmanaged runs overflow in **78.7%** of cases at tight budgets. Best: staged "rule-based elision before
    LLM summarisation".
  - Planning helps weaker models (+11.6 pts for a 30B; runs collapsed from 40→5 turns without it).
  - Weaker models lose ~15 pts bash-only (66% of runs die after failed tool calls); strong models do fine bash-only.
  - Definitions (paper): M1 elision = replace stale tool-output bodies with short stubs; M2 recall = store them
    externally, fetchable via `recall_event`; M3 summarisation = fold oldest middle events into a running summary.
    Preamble + recent window kept verbatim; soft threshold B1 → elide middle, hard threshold B2 → summarise. T4 = all three.
  - Planning (paper §3.2/§7.2, Fig. 15/17): a todo list kept via an `update_plan` tool; first action on any
    3+-step task; exactly one item in_progress; stored OUTSIDE the history and re-injected fresh before every model
    call ("Current plan …: {PLAN}") instead of appending copies. Effect: Nemotron-3 30B +11.6 pts SWE-Bench (higher
    cost); 128B/550B models: ~30% cheaper, −0.4/−2.0 pts. Gemma 31B-W4 at 32k ≈ the "weaker model" side → likely helps.
  - Our version (no update_plan tool, no callbacks): SequentialAgent [planner (read-only, output_key=plan) → coder
    whose instruction contains {plan}]. ADK renders instruction state templates on each model request, so the plan is
    re-supplied every turn and survives compaction (expected ADK behaviour — VERIFY locally). Progress tracking:
    optional tiny /tmp/plan.md checklist via run_command. Planner can double as the localizer (files, lines, repro idea).
  - Prompt/issue reformatting (researched 2026-09-26): benchmark papers (SWE-Bench Pro, ProMax) rewrite issues
    OFFLINE with human/gold knowledge — not evidence for inference-time rewriting; no solid paper found showing a
    rewrite module alone lifts resolve rate. Public-task data: 34/129 statements <150 chars (often just a PR title,
    e.g. "✨ Add support for Server Sent Events"), 25 contain PR/checklist templates, 9 HTML-comment templates,
    18 code blocks, 1 traceback; median 418 chars, max 10k.
    → DECISION: no separate rewriter. Fold into the planner as a "TASK SPEC" section: expected vs actual behaviour,
    identifiers/messages/values quoted VERBATIM, acceptance criteria, ambiguities + chosen interpretation, boilerplate
    ignored. For title-only tasks the planner must recover the spec from the repo (docs/, docs_src/, changelog,
    similar existing features, related tests) — rewriting can't add information that isn't there.
    Raw issue always stays in the harness's first message, so a rewrite adds tokens rather than replacing them.
  - We likely CANNOT elide history (declarative YAML, no callbacks registered — inference, untested). ADK events
    compaction ≈ M3. Emulate elision by design: AgentTool sub-agents (their reads never enter root context),
    compact skill-script outputs, strict output-size rules in the prompt.
  → For us (mid-size model, 32k window): context management + explicit plan + robust structured tools =
    top priorities. Ties directly to the ADK compaction question (does it fire?) and to AgentTool isolation.

## Self-correction (researched 2026-09-26) — likely under-explored lever
- Competition status: 2 EDA notebooks list "reviewer sub-agent (inspect git diff vs issue before submit)" as an
  untried idea; the 0.10 notebook has a read-only `code_verifier` sub-agent variant in an ablation (results not
  shown). No public use of SequentialAgent/LoopAgent generate→review→revise.
- Literature: SWE-Review (arXiv 2607.06065) generate-review-revise loop beats single-shot review in decision
  accuracy and resolve rate; ExecCritic (2609.09133) generated test patches +4.2 pts on SWE-bench Verified;
  Adversarial Review (2608.18167) reviewer–critic loop; "Confident and Wrong" (2603.25764) silent semantic failures.
- Three levels possible in our harness:
  1. In-loop: reproduce → edit → re-run → read failure → fix (prompt-driven; cheapest).
  2. Reviewer AgentTool: read-only sub-agent checks `git diff` vs issue (names/signatures, scratch files, test edits,
     partial fix) and returns a verdict + fix list before submit_patch.
  3. Workflow: SequentialAgent [coder → reviewer(output_key=review) → fixer uses {review}]. LoopAgent can't exit
     early: `exit_loop` is not in the closed ToolRegistry → only `max_iterations` (keep 1–2).
- Risks/UNVERIFIED: harness breaks the loop as soon as a turn ends with patch_submitted → only the LAST agent should
  hold submit_patch (unsubmitted diffs are auto-extracted anyway); how harness handles workflow-agent roots needs a
  local test; review costs time inside the ~6 min/task budget.
- **Chosen design (user idea, refined): coder + verifier AgentTool, bounded loop.**
  - Coder owns edits + submit_patch; calls `verifier` (agent_tool, skip_summarization) after each fix attempt.
  - Verifier = evidence-based, not opinion: runs the /tmp repro script + the closest existing tests + a
    diff audit (names/signatures vs issue, no test/config edits, no scratch files in /workspace, fix complete),
    returns `VERDICT: PASS|FAIL` + for FAIL the exact command, trimmed error (≤20 lines) and the one thing to fix.
    Tools: run_command, read_file (no edit/write/submit). Must write only to /tmp (prompt rule; not enforceable).
  - Loop = coder decides (AgentTool can be called repeatedly) — cap at 2–3 verifier calls; stop early on PASS,
    when the same complaint repeats, or when budget_warning appears / get_status shows <25% left.
  - Never revert a plausible fix because of a vague complaint; a FAIL must quote real command output.
  - Baseline noise: coder records failing tests BEFORE editing so verifier can ignore pre-existing failures.
- Verified from source: verifier's run_command/read_file calls hit the SAME per-task budget (budget_gated uses the
  shared task context) → max_tool_calls must include verifier usage. The agent_tool call itself is not a swegemma
  tool, so it likely isn't counted (inference). `problem_description` is in session state; whether the AgentTool
  child sees it via `{problem_description}` in its instruction is UNVERIFIED → test locally; fallback: coder passes
  issue essentials in the request.
- Also relevant: notebook `busyaprime/119-of-129-sound-the-gemma-4-grader-rebuilt` (gold-patch validity of dev tasks).

## Agent communication topology (researched 2026-09-26)
- Evidence: "Towards a Science of Scaling Agent Systems" (Google, arXiv 2512.08296; 260 configs): sequential
  reasoning tasks degrade 39–70% under all multi-agent variants; tool-heavy tasks pay a coordination "tax";
  coordination has diminishing/negative returns once single-agent baseline > ~45% (we are ~13% → below, so
  targeted help can pay); independent agents amplify errors 17.2×, centralized 4.4× (orchestrator = validation
  bottleneck). MAST (arXiv 2503.13657): 14 failure modes, a major class is inter-agent misalignment (information lost
  or misread at hand-offs). Another survey: MAS slightly degrade SWE-bench Verified (−2 to −15%) at high baselines.
- Implication: coding is sequential + tool-heavy → keep ONE agent that owns the working context and all edits
  (hub); specialists are call-and-return helpers with short structured I/O; specialists never talk to each other.
- ADK mechanics (verified in compiler): `agent_tool` = call-and-return (parent keeps control, gets child's final
  text); `SequentialAgent` = fixed pipeline; `sub_agents` transfer hands control away (avoid — harness loop/final-
  response handling makes it risky, UNVERIFIED). Shared state via `output_key` → `{key}` in instructions.
- Recommended topology ("hub-and-spoke with a fixed opening"):
  SequentialAgent[ planner (read-only, output_key=plan: TASK SPEC + PLAN) → executor/hub (instruction has {plan}) ]
  executor calls: verifier (agent_tool, 2–3× max) and optionally replanner (agent_tool, same planner prompt, only when
  stuck, given what was learned). No planner↔verifier channel; all traffic goes through the executor.
  DECISION (user asked for recommendation): target = hub + fixed opening, built as an ablation ladder, each rung
  measured on the same dev subset (also the paper's core experiment):
    1) single agent + strong prompt (git history, safe git, bounded output, never ask) → baseline + failure taxonomy
    2) + verifier agent_tool (max 2–3 calls)
    3) + planner up front (Sequential, {plan} re-injected every turn)
    4) + replanner agent_tool only when stuck
  Keep a rung only if it pays for its time on our tasks.
  Rejected: planner-as-orchestrator commanding an executor sub-agent (executor would restart context each call, the
  orchestrator only sees summaries of edits → hand-off loss, more hops, more time).

## Teacher models for distillation (researched 2026-09-26)
Reference point: Gemma 4 31B IT (bf16) ≈ 53.9% SWE-bench Verified (Vals AI) — vs LB top 13%. Gap = harder
private repos/frontier-filtered tasks, 4-bit, 32k context, weak scaffolds → large scaffold headroom.
- **Primary teacher: Qwen3.6-27B** (HF model card): dense 27B, **Apache 2.0**, SWE-bench Verified 77.2%,
  Pro 53.5%, tool calling (vLLM `--tool-call-parser qwen3_coder`), needs vLLM ≥0.19.0 (competition wheelhouse has
  0.19.1). bf16 ≈54 GB → fits Kaggle 4×L4 (96 GB, TP=4) at 32k ctx → **teacher runs on our free quota.**
- Alt: **Qwen3.6-35B-A3B** (MoE 35B/3B active, Apache 2.0, 73.4% Verified) — much faster per token.
  Qwen3-Coder-Next (80B-A3B, 70.6%, Apache 2.0).
- Too big for free hardware (API only): DeepSeek V4-Flash (284B/13B, MIT, ~79%), V4-Pro (MIT, ~80.6%),
  GLM-5.2 (MIT), Kimi K2.5/K3 (Modified MIT). DeepSeek's API terms explicitly allow distillation — but costs money.
- Avoid: Llama 4 (custom community license strings), all closed APIs (Claude, GPT, Gemini-proprietary ToS).
- Caveats: (1) teacher must act in OUR room (same tools/prompt/limits), then transcripts are re-rendered into
  Gemma's chat/tool-call format; (2) teacher skill gap → filter to verified passes, prefer shorter/simpler
  trajectories the student can imitate; (3) competition ruling on distillation still pending — open-weight
  Apache/MIT teachers are the route the rules' "publicly available, free" clause clearly covers.
- Kaggle "AI Models" credit: model list only visible via `list(kbench.llms.keys())` in a notebook — check.

## Still unverified / waiting on hosts
1. L4×4 quota burn rate (1× vs 4×) — measure.
2. Distillation from proprietary LLMs allowed? (742807) — host "conferring" since Sep 24, still no ruling
   (checked 2026-09-26). Independently: Anthropic terms prohibit "using Outputs as training targets for models" /
   training competing models (support.claude.com article 12326764); OpenAI similar. Winner obligations
   (open-source, reproducible) also clash. → DECISION: no Claude/GPT-generated training data. Claude is used
   only to build the system (prompts, skills, eval tooling, failure analysis).
   Training-data plan instead: (a) rejection sampling / self-distillation from Gemma 31B in our own room
   (keep only harness-verified passes); (b) open-weight teachers with training-permissive licenses;
   (c) extra runnable task sets (e.g. SWE-Gym 2,438 tasks) — check licenses + effort to port into swegemma.
3. LoRA adapter-wipe fix in scoring vLLM (743508) + whether sample adapters then work.
4. Whether events compaction actually fires (743456); int/bool tool-arg parsing on the scorer.
5. Whether scoring env has the empty graph/embedding files problem and missing test wheels.
6. Hidden-test repos are private — nothing known about their size/style beyond "similar pipeline".
7. Which hosted models the Kaggle "AI Models" credit exposes.

## Housekeeping
- Scratchpad (`/private/tmp/claude-501/.../scratchpad/`) is session-scoped: in P0 copy `data/`, `pages/`,
  `paper/`, `forum/`, `kernels/`, `src/` into the repo under `data/` or `research/` — gitignored where it
  contains competition data (no redistribution).
- Rotate the Kaggle API token that was pasted in chat.

## Verification
- `make pack` → zip validated with swegemma's ALLOWED_SUBMISSION_EXTENSIONS / MAX_SUBMISSION_SIZE_BYTES and
  compile_submission(). Kaggle-notebook eval on dev subset → resolution rate; LB submission for calibration.
