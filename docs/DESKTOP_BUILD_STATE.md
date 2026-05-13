# Desktop App (apps/desktop) — Build State as of 2026-05-13

## Summary

The Wan 2.2 / LTX-2 ComfyUI provider backend integration (PR #30) is
**complete and validated** with 14 passing unit tests. The Python
backend (`packages/core`) imports clean and registers all 6 providers.

However, the desktop app's **renderer (Electron + React + Vite)** is
in a partial / WIP state, inherited from commit `c851ca9`
("feat: integrate SceneMachine UI updates and desktop renderer
changes", Feb 16 2026 by Kit OC1). It does **not** currently build.
This document captures what's broken so the work can be properly
scoped and scheduled — it is **not** something to fix in a hurry.

## Concrete build-blocking issues

### 1. Missing exports in `lib/utils.ts` (FIXED)
- `formatDate` — imported by `home.tsx` but not exported. Fixed in
  commit `090b117` by adding `formatDate(input)` to utils.

### 2. Missing exports in `lib/time-estimates.ts` (NOT FIXED)
`components/queue-manager.tsx` imports four functions that don't exist:
- `estimateQueueTime(pending, running, provider, concurrency)`
- `formatCompletionTime(estimate, mode)`
- `formatQueuePosition(position, mode)`
- `formatElapsedTime(startedAt, mode)`

Note: queue-manager.tsx also calls `formatTimeEstimate(estimate, mode)`
with two arguments, but the existing export only accepts one. So the
signatures here are out-of-sync, not just the function presence.

### 3. TypeScript errors in `stores/shot-store.ts` (NOT FIXED)
13 errors found by `tsc --noEmit`:
- Lines 317, 319, 352, 353, 355, 389, 390, 392: `Type 'undefined'
  cannot be used as an index type` — `shot.sceneId` is typed as
  potentially undefined but used as a dict key.
- Lines 346, 365, 383, 402: `Property 'success' does not exist on type
  '{ id: string; state: string; approved: boolean; }'` — the
  `api.approveGeneratedShot(shotId)` / `api.rejectGeneratedShot(shotId)`
  return types don't have a `success` field, but the calling code
  destructures `result.success`.
- Line 440: `Property 'progress' does not exist on type 'GenerationJob'`
  — the GenerationJob type is missing a `progress` field that the
  watcher expects.

These are API-contract mismatches between the renderer's type
definitions and what the actual store code assumes. Fixing requires
deciding whether to:
  - extend the API response types to include `success`, or
  - remove the `.success` checks (assume API throws on failure), or
  - rewrite the store to match the current types

This is a design decision, not a mechanical fix.

### 4. Likely more (audit incomplete)

Vite's build halts at the first missing-export error, so the iteration
to confirm "all" build issues requires fixing each one and re-running.
The above are only what's been surfaced so far. Beyond those, there
may be additional missing imports / type errors that only appear after
the build progresses past the first hurdle.

## Why this matters

- **The PR #30 integration is unaffected.** It modifies only Python
  code in `packages/core/scenemachine/generators/comfyui.py`. The
  Python backend boots clean, registers providers, and is ready to
  receive IPC calls.

- **Launching the Electron desktop UI live** (the original goal of
  task #15 in the integration plan) is blocked until the desktop
  build state is fixed.

- This is **inherited tech debt**, not something the integration
  introduced. The commit log shows Kit OC1's Feb 16 "AntiGravity
  session push" added a large batch of UI code (components/, pages/,
  stores/) that was clearly mid-development.

## Recommended next steps

1. **Triage:** open a GitHub issue capturing this build state, link
   to this doc. (Done — see issue link in `git log` for this commit.)

2. **Decide whether to fix in one focused pass:** this is probably
   one developer-week of work. Roughly:
   - 0.5 day — add missing functions to `time-estimates.ts` with
     proper signatures matching queue-manager.tsx
   - 1 day — resolve all the renderer's missing exports by running
     vite build iteratively; track remaining issues
   - 1–2 days — fix `shot-store.ts` API-contract issues (requires
     decisions about API shape)
   - 1 day — playwright e2e test pass after build is green
   - 0.5 day — final lint + typecheck cleanup

3. **In the meantime,** the Wan 2.2 pipeline is fully usable via the
   command-line tools at `/opt/ai/scripts/`:
   - `scene_to_prompts.py` (validated)
   - `make_scene_v2.py` (validated)
   - `make_movie_v2.py` (validated; produced sample_movie.mp4)
   The SceneMachine desktop UI is the UX-quality layer on top of
   these capabilities, not a prerequisite for using them.

## Authoritative source for current state

Run `git log -1 --oneline` then check this doc's last-update date.

— Opus 4.7 (CTO seat), 2026-05-13
