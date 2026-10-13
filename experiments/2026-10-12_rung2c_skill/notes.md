# Rung-2c (2026-10-12): safe-edit skill (checked SEARCH/REPLACE editor)

Why: rung-2b r4_budget had the right rich_3470 fix but the edit duplicated a line (invalid Python) at call 25/28,
with no calls left to notice. A tool-level check (event-triggered) instead of a prompt rule.
Skill (skills_src/safe-edit, written by us): run_skill_script(safe-edit, scripts/install.py) once copies
safe_edit.py to the task's /tmp (tempfile.gettempdir(): TMPDIR = per-sandbox tmp in the subprocess sandbox, /tmp in
Docker); edits are run_command heredocs `python3 /tmp/safe_edit.py FILE << 'EDIT'` with SEARCH/REPLACE blocks.
All-or-nothing; refuses: SEARCH not found (shows closest numbered lines), SEARCH ambiguous, invalid Python after
the edit (shows error + numbered lines), test/test-config files. Tested locally incl. the exact 3470 duplicate.
Harness facts: skill scripts run via AdkSandboxCodeExecutor in the task's own ManagedSandbox (safe with
concurrency), cwd = a temp dir (not /workspace); edit text is passed through run_command, not tool args (avoids
the gemma4 tool-parser array hang, forum 745138). edit_file stays declared (insurance), prompt points to the editor.
Prompt change (+32 words): step 0 install; step 4 uses the editor (replaces the edit_file + Python fallback text);
example and tool lines updated.

| Arm | = |
|---|---|
| r4_budget | reference |
| r4b_skill | r4_budget + skill |
| r4b_think_t02 | rung-2b best (thinking 4096, T 0.2) |
| r4b_think_t02_skill | r4b_think_t02 + skill |
Measure: score, NOT_APPLIED events and whether the next block fixed it, edit_file vs editor use, the extra call.

## Results (2026-10-13): the skill was not used — no test of the skill
| Arm | r1 | r2 |
|---|---|---|
| r4_budget | 2/4 | 1/4 |
| r4b_skill | 1/4 | 1/4 |
| r4b_think_t02 | 1/4 | 2/4 (rich_3470 solved) |
| r4b_think_t02_skill | 2/4 (15589 solved) | 1/4 |
- Only 1 of 16 skill-arm tasks ran the install ("Ah, I forgot to run the install script for safe-edit", call 15,
  rich_3882) and used the editor once. All others used edit_file. "Step 0: first call = install" is another
  self-monitoring rule and was ignored, like earlier step-order rules.
- Cumulative (4 tasks, 2a–2c): r4_budget 10/24, r4b_think_t02 7/16. Batch-to-batch swings of ±1 task per arm.
- Harness (swegemma 0.2.11): ToolErrorPlugin returns undeclared-tool calls to the model as an error (no crash);
  build_agent_prompt never mentions edit_file/write_file. → Next: remove edit_file/write_file so the editor is
  the only editing path; a missing /tmp/safe_edit.py ("No such file") is an event that points to the install.
