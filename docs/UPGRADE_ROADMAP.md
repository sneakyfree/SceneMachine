# Deferred Dependency Upgrade Roadmap

**Authored 2026-05-13 alongside `feat/wire-local-wan22-stack` (PR #30).**

## Policy

This document records the *deliberate deferrals* of major dependency upgrades
made during the Wan 2.2 / SceneMachine integration. The choice in every case
was the same: **do the integration on a known-good toolchain, then upgrade
each major dependency as its own focused effort with proper regression
testing.** Doing them all at once would have made root-causing any breakage
impossible.

This is a marathon, not a sprint. Future-proofing means *upgrading
deliberately* — not bundling 13 major versions into one merge.

## Already done

Merged during the `feat/wire-local-wan22-stack` cleanup pass (2026-05-13):

| # | Upgrade | Risk | Why merged |
|---|---|---|---|
| #1  | `docker/build-push-action` 5 → 6 | low | GitHub Action only |
| #7  | `concurrently` 8 → 9 | low | dev tool; Node ≥ 16 requirement satisfied |
| #28 | `@testing-library/react` 14 → 16 | low | test lib; still supports React 18 |
| #29 | `jsdom` 24 → 29 | low | test DOM; Node ≥ 20 requirement satisfied |

Deferred and dismissed with `@dependabot ignore this major version` (will
not be auto-recreated). To revive any of these, comment `@dependabot
unignore @<dep>` on the closed PR.

Closed but **not** ignored because the OAuth token couldn't merge workflow
files — to redo, retry with a token that has `workflow` scope, OR merge via
the GitHub web UI:
- #2 `actions/download-artifact` 4 → 7
- #3 `azure/setup-kubectl` 3 → 4
- #4 `actions/setup-node` 4 → 6
- #5 `softprops/action-gh-release` 1 → 2

These can wait until CI workflows are restored in the repo.

## Deferred (with rationale + sequencing)

Order is by recommended sequencing. **Do not** try to combine adjacent
items unless explicitly noted.

### Round 1 — Backend (no UI risk, can be done independently)

#### A1. Python 3.11 → 3.13 (not 3.14)
- **Original PR**: #6
- **Priority**: P2 (Python 3.11 has security support through 2027)
- **Effort estimate**: 2–4 hours
- **Risk**: low–moderate
- **Notes**: Dependabot's PR went to 3.14, which only released in October 2025
  and may not have wheels for every dep yet. **Target 3.13 instead** — same
  performance wins, broader ecosystem support. Re-run `pytest` against the
  new image; backend has no GUI surface so failures are bounded.
- **Files**: `tools/docker/Dockerfile`, `packages/core/pyproject.toml`
  (`requires-python`).

### Round 2 — Test tooling (verify before depending on these)

#### B1. `@vitest/coverage-v8` 1 → 4
- **Original PR**: #26
- **Coupled with**: `vitest` (currently 1.2, needs to go to 3+)
- **Priority**: P3 (only impacts test reports)
- **Effort estimate**: 1–2 days
- **Risk**: moderate — vitest 2 and 3 each had test-runner API changes
- **Sequence**: bump `vitest` and `@vitest/coverage-v8` in lock-step.
  Coverage-v8 4.x requires vitest ≥ 3.0.

### Round 3 — Linting (cosmetic, do whenever)

#### C1. `eslint` 8 → 9 (skip 10 for now)
- **Original PR**: #25
- **Priority**: P3
- **Effort estimate**: 3–5 hours
- **Risk**: moderate — eslint 9 mandates flat config (`eslint.config.js`).
  The repo currently uses `.eslintrc.*` style. The migration is mechanical
  but every `eslint-config-*` and `eslint-plugin-*` dep needs a check for
  flat-config compatibility.
- **Sequence**: do `eslint` 8 → 9 first as its own PR. Hold 10 until at
  least one minor release of 10.x is available.

#### C2. `@typescript-eslint/eslint-plugin` 6 → 8
- **Original PR**: #11
- **Coupled with**: `@typescript-eslint/parser` (in the build-tools group)
- **Priority**: P3
- **Effort estimate**: 2–4 hours
- **Risk**: moderate — must be done in the same PR as `eslint` 9 because
  the rule schemas changed.

### Round 4 — Small, high-value runtime libs

#### D1. `uuid` 9 → 13 *and* `@types/uuid` 9 → 11
- **Original PRs**: #20 + #17 (must be merged together)
- **Priority**: P3
- **Effort estimate**: 4–8 hours
- **Risk**: moderate — `uuid` 10 changed module export shape from CommonJS
  to ESM-only. Any `require('uuid')` calls break; `import { v4 } from 'uuid'`
  works. Need to audit all import sites in `apps/desktop/src/`.

#### D2. `zustand` 4 → 5
- **Original PR**: #13
- **Priority**: P3
- **Effort estimate**: 1–2 days
- **Risk**: moderate–high — `zustand` 5 removed the default-export `create`
  pattern and made stores stricter about middleware ordering. Every
  `create((set, get) => …)` callsite needs review.

#### D3. `framer-motion` 10 → 12
- **Original PR**: #27
- **Priority**: P3
- **Effort estimate**: 4–8 hours
- **Risk**: moderate — version 11 was just a rename pass; version 12 added
  the `motion/react` import pathway. The old `framer-motion` import still
  works, so this can be done lazily.

### Round 5 — Frontend framework (the big one)

#### E1. React 18 → 19 *and* `@types/react-dom` 18 → 19
- **Original PRs**: #12 + #24 (the *react-ecosystem* group)
- **Priority**: P1 — but only when we're ready to commit a focused week
- **Effort estimate**: 1–2 weeks of dedicated engineering
- **Risk**: HIGH
- **Breaking changes to audit per component**:
  - `ReactDOM.render` / `hydrate` are removed → use `createRoot` / `hydrateRoot`
  - Legacy context API is removed
  - String refs are removed
  - `defaultProps` on function components is removed
  - `useFormState` renamed to `useActionState`
  - Suspense behavior changed for sibling-effects
- **Coupled with**: react-router-dom version bump (within the same
  ecosystem group) — must verify route component patterns still work
- **Sequence**: schedule this as its own week-long sprint with the desktop
  app's Playwright e2e suite running every commit. Do **after** the build
  toolchain upgrade in Round 6 — vite 6/7 has better React 19 support.

### Round 6 — Build toolchain (the other big one)

#### F1. The `build-tools` group (PR #23) — one item at a time

This Dependabot PR bundled seven bumps:

| Dep | From | To proposed | Recommended target |
|---|---|---|---|
| `vite` | 5.0 | 8.0 | Do **5 → 6 → 7** in two PRs; hold 8 until next stable point release |
| `@vitejs/plugin-react` | 4.x | 6.x | Bump in lock-step with each `vite` step |
| `vitest` | 1.x | 4.x | Do **1 → 2 → 3** in three PRs; couple with #B1 above |
| `typescript` | 5.3 | 6.0 | Bump to latest 5.x first; defer 6.0 |
| `vite-plugin-pwa` | 0.20 | 1.2 | After vite is on a known-good version |
| `electron` | 28 | 41 | **DEDICATED MULTI-WEEK EFFORT** — see below |
| `electron-builder` | 24 | 26 | Couple with electron upgrade |

- **Priority**: P1 for the partial step (vite 5→6, vitest 1→2, ts to
  latest 5.x). P0 for electron if security vulnerabilities are reported.
- **Effort estimate**: vite/vitest pair → 1 week. **Electron upgrade
  (28→41) → 2–4 weeks** — that's 13 major versions, with main-process
  / renderer-process API changes, context-isolation defaults flips, and
  IPC behavior shifts.
- **Risk**: HIGH for the electron piece, moderate for the rest.

### Recommended order of attack

```
Round 1 (Python 3.13)              ← safe, do anytime
   │
Round 2 (vitest/coverage)          ← unblocks better test signal
   │
Round 3 (eslint flat config)       ← unblocks Round 4/5 lint catches
   │
Round 4 (uuid, zustand, framer)    ← small wins, do one at a time
   │
Round 6a (vite 5→6, ts to 5.x)     ← prepare build for React 19
   │
Round 5 (React 19)                 ← biggest UI risk; pin a week
   │
Round 6b (electron 28→41)          ← dedicated multi-week effort
```

## Re-enabling Dependabot for an upgrade you want to do

When you're ready to schedule one of the deferred upgrades:

```bash
# Find the closed PR number from this doc (e.g. uuid was #20)
gh pr comment 20 --body "@dependabot unignore @uuid major version"
# Dependabot will open a fresh PR within a day.
```

## Why not just merge everything now

The user's guiding principle for SceneMachine, recorded for posterity:

> Marathon not sprint. Quality and a solid foundation over launch speed.
> Future-proof the platform so it can evolve over time.

A 14-major-version-bump PR is the opposite of that.

— Opus 4.7 (CTO seat), 2026-05-13
