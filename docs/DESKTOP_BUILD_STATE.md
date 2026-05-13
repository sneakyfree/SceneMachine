# Desktop App (apps/desktop) — Build State

**Status as of 2026-05-13 (post-PR #32): BUILD GREEN.**

The Wan 2.2 / LTX-2 ComfyUI provider backend integration (PR #30) is
complete and validated with 14 passing unit tests. The Python backend
(`packages/core`) imports clean and registers all 6 providers.

The desktop renderer also now builds AND serves successfully (PR #32):

```
$ npm run build:renderer    # 1830 modules, ✓ built in 2.71s
$ npm run build:main        # Electron main + preload, no errors
$ npx vite preview --port 5191
  curl http://127.0.0.1:5191/ → <title>SceneMachine</title>
  curl /assets/index-*.js   → HTTP 200, 922 kB bundle served
```

**Remaining work — typecheck-only errors (do NOT block build/run):**
There are 326 real type errors (TS2339, TS2538, TS2353, etc.) plus 202
unused-import warnings (TS6133) reported by `tsc --noEmit`. None of
these block `vite build` or the Electron `dev` cycle — they're tech
debt that the renderer will tolerate at runtime. Fixing them properly
requires API-contract decisions and is sized in `docs/UPGRADE_ROADMAP.md`.

This document captures the historical state for reference.

## Build-blocking issues (all resolved)

### 1. Missing exports in `lib/utils.ts` ✅ FIXED (commit `090b117`)
- `formatDate` — added to utils.

### 2. Missing exports in `lib/time-estimates.ts` ✅ FIXED (PR #32)
- `estimateQueueTime`, `formatCompletionTime`, `formatQueuePosition`,
  `formatElapsedTime` — implemented with experience-mode-aware copy.
- `formatTimeEstimate` — signature widened to accept optional mode.

### 3. Missing exports in `lib/accessibility.ts` ✅ FIXED (PR #32)
- `SkipLink` interface, `useSkipLinks`, `useFocusTrap`,
  `usePrefersReducedMotion`, `ariaDialog` — added React hooks that
  reuse the existing `createFocusTrap` mechanics.

### 4. Missing exports in `lib/offline-cache.ts` ✅ FIXED (PR #32)
- `offlineCache` (OfflineCacheService singleton), `CachedProject`,
  `CachedVideo`, `SyncQueueItem` — added an in-memory + localStorage
  shim. IndexedDB-backed implementation is in the roadmap.

### 5. Missing export in `api/client.ts` ✅ FIXED (PR #32)
- `BookingRequest` interface — added with fields matching
  `booking-modal.tsx`'s call site.

## Non-blocking issues (type-only; main has 326 of these)

### TypeScript errors in `stores/shot-store.ts` (NOT FIXED — not build-blocking)
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
