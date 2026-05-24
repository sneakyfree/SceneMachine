# Autonomous Improvement Loop

_Drafted 2026-05-24 09:35 PDT by Dr. D Opus 4.7. Source-of-truth for /goal-fired autonomous iteration on SceneMachine quality + smoothness._

## What this is

A repeating loop where each turn produces a tangible improvement (a PR, a doc, a test, a fix) without burning the operator's attention. Designed for `/goal` invocation; safe to run for hours.

Pattern: **read state → pick highest-value next move → execute → verify → ship → loop**.

## Paste-able /goal prompts

Pick one based on the desired focus:

### Broad quality loop (recommended)
```
/goal Run the autonomous improvement loop from docs/AUTONOMOUS_IMPROVEMENT_LOOP.md until compute reset. Each iteration: pick the highest-severity open defect from docs/INVENTORY_DEFECTS.md (P0 first, then P1) that doesn't touch in-flight V_N benchmark files; fix it on a branch; open + merge a PR when CI greens; update INVENTORY_DEFECTS.md to mark closed; loop. Pace 1-3 PRs per hour. Ultrathink.
```

### Stage-4 hardening loop
```
/goal Run the Stage 4 hardening loop from docs/AUTONOMOUS_IMPROVEMENT_LOOP.md. Each iteration: tighten one CI gate, write one runbook, or close one architectural-debt item. Don't open more than 6 PRs in flight at once. Ultrathink.
```

### Stage-5 polish loop
```
/goal Run the Stage 5 polish loop from docs/AUTONOMOUS_IMPROVEMENT_LOOP.md. Each iteration: pick one frontend rough edge (error message, empty state, missing aria-label, abort button, sprawl candidate) and fix it. Ultrathink.
```

### Video-quality ladder loop
```
/goal Continue the V_N ladder per docs/V9_PLUS_LADDER.md. After each preset lands, analyze + design the next experiment + launch + wait. Halt if all quality bars met. Ultrathink.
```

## Loop body (executed per iteration)

1. **Read current state** (cheap, < 30s):
   - `git log --oneline -5` on main
   - `gh pr list --state open --search "is:open"`
   - In-flight V_N benchmark? Check `pgrep -f run_benchmark.py` and `tail -3` of its log
   - `docs/INVENTORY_DEFECTS.md` top of P0 / P1 lists
   - `tail` MEMORY.md to see if context has shifted

2. **Pick next move** with this priority:
   - **HALT criteria first** — if any of these hit, surface and stop the loop:
     - 3 consecutive iterations made no progress
     - The next defect requires the operator's authorization (security, deploy, prod-data)
     - In-flight V_N is at risk (process died, GPU contention)
   - Otherwise pick from:
     1. P0 defect with concrete fix (auth bug, missing migration, broken endpoint)
     2. P0 with design needed → surface for operator + skip to next item
     3. P1 silent-fail or broken feature
     4. Stage 4 hardening (systemd, runbook, coverage)
     5. Stage 5 polish (error boundary, abort button, accessibility)

3. **Safety gates** (read these before touching code):
   - **Don't touch** `scripts/run_benchmark.py` while a V_N benchmark is running with that file loaded — Python keeps the in-memory copy, but a crash would re-read disk and re-routing logic might shift mid-run.
   - **Don't touch** `packages/core/scenemachine/services/production_pipeline.py` heavily while V_N runs — same reason. Small surgical fixes are OK if they don't change `_assemble_movie` or `_generate_videos` semantics.
   - **Don't restart ComfyUI** while a V_N benchmark is running.
   - **Don't force-push to main** ever.
   - **Don't merge** to main without CI passing (or admin override with clear justification).

4. **Execute on a branch**:
   - Name: `fix/<short-slug>` for bug fixes, `feat/<slug>` for features, `docs/<slug>` for doc-only, `chore/<slug>` for deps/lint
   - Single-concern commits with descriptive messages (see CONTRIBUTING.md style — the multi-paragraph "why" body is the project convention)
   - Add a regression test if the fix is non-trivial
   - `pytest packages/core/tests/services packages/core/tests/ipc --no-cov -q` should be green on changed code

5. **Open + merge PR**:
   - `gh pr create --title "<concise title>" --body "<context + test plan>"`
   - Wait for required CI: python-lint, python-test, frontend-lint, frontend-test, build-backend, docker-build (per inventory)
   - `gh pr merge <N> --squash` when MERGEABLE + status UNSTABLE-or-better
   - If MERGE conflict on rebase: resolve by reading both sides, take the post-#97-format version, re-apply the branch's content

6. **Update tracking**:
   - Mark the defect closed in `docs/INVENTORY_DEFECTS.md` (move from "open" to "closed in flight", reference PR #)
   - Update task list (`TaskUpdate` for affected stage)
   - Save to memory if the fix taught us something durable (per memory rules in CLAUDE.md system)

7. **Loop**:
   - If HALT criteria hit, write a summary to `~/scenemachine_movies/MORNING_REPORT_<date>.md`
   - Otherwise → step 1

## Cadence

- **Healthy**: 1-3 PRs per hour (excluding CI wait time which can be parallel)
- **Burnout signal**: < 1 PR per hour for 2 hours straight → review priority queue; maybe a HALT-worthy blocker
- **Burst**: rebase + merge cascade (like the 2026-05-21 cleanup) can hit 6+ PRs in an hour

## What this loop will NOT do without explicit permission

- Modify CI workflow files (requires `workflow` OAuth scope)
- Delete production data
- Change Stripe / billing logic in services/billing_service.py
- Touch auth tokens or `~/.claude/projects/-home-user1-gpu/memory/reference_credential_lockbox.md`
- Deploy to staging or production
- Force-push, force-delete branches with unmerged work
- Open PRs that bundle multiple unrelated changes (single-concern rule)
- Engage `gh pr merge --admin` without surfacing first

## Where to look when the loop wakes back up

- **Plan**: `STRESS_TEST_PLAN.md` (root)
- **Defects**: `docs/INVENTORY_DEFECTS.md`
- **Inventory**: `docs/INVENTORY_SURFACES.md`
- **V_N design**: `docs/V9_PLUS_LADDER.md`
- **State**: `~/.claude/projects/-home-user1-gpu/memory/project_goal_72h_state.md`
- **Recent runs**: `~/scenemachine_movies/benchmarks/V*/morning_analysis/scorecard_*.md`
- **Recent reports**: `~/scenemachine_movies/MORNING_REPORT_*.md`

## Halt conditions (write to morning report + stop)

- All P0/P1 closed AND coverage > 70% AND V_N hits all quality bars → success
- Operator pushes a `/goal clear` or new `/goal` with different focus
- 3 consecutive no-progress iterations
- A safety-gate violation almost happened (don't second-time it)
- Compute budget signal (operator says "stop", or scheduled reset like 13:00 PDT 2026-05-24)

## Iteration log (auto-appended)

This section is appended to as iterations complete. Most-recent first.

| # | started | PR | title | closed defect |
|---:|---|---:|---|---|
| 1 | 2026-05-24 09:35 PDT | (in flight) | alembic 007 for `lipsync_jobs` | "Missing migration for lipsync_jobs (P0)" |
