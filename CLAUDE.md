# Project: Kaggle "Gemma 4 Developer Agent" competition entry

Goal: build an autonomous SWE agent on `gemma-4-31b-it-qat-w4a16-ct` (Google ADK Agent Config: YAML + prompts +
skills + optional LoRA) for https://www.kaggle.com/competitions/gemma-4-developer-agent, plus a paper-track writeup.

**Read `docs/PLAN.md` first** — its "START HERE" section has current status, all decisions, and the next agenda.
Everything below it is verified research (rules, harness internals, forum findings, papers).

## Working with this user
- Beginner to agents/ADK: explain step by step, plain language, one concept at a time.
- Back claims with sources (web search, the harness source, the data) and label anything unverified.
- In planning discussions, keep talking until the user says to build.

## Layout
- `data/` (gitignored): tasks.jsonl, HARNESS_README.md (official harness guide), sample_submission/, docker/, sandbox/.
- `research/raw/` (gitignored): official pages, paper-track pages, forum threads, public notebooks,
  harness source (`harness_src/`: swegemma 0.2.7, adk-submission 0.2.11, adk-eval-core 0.1.0).
- `scripts/kaggle_api.py`: Kaggle API helper (token in ~/.kaggle/access_token).
- Competition data must never be committed or published.
