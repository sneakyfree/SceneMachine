# SceneMachine Stress Test + Quality Elevation Plan

_Owner: Grant Whitmer. Lead executor: Dr. D (Opus 4.7, 1M context). Drafted 2026-05-21 20:50 PDT, target completion TBD per Grant._

> **Goal**: turn SceneMachine from a trouble-ridden 1/5 "video slop" platform into an industry-shaking one where every tab, link, and feature works flawlessly and the video quality dazzles. Two interleaved tracks: **(A) surface-area stress test + fix loop** and **(B) video quality elevation V9+**. Both grind until the bars are met.

---

## 0. Quality bars — when is "done" done?

The loop exits when ALL of these hold. Each is independently verifiable; no soft criteria.

### A. Platform stress bars

| bar | target | how measured |
|---|---|---|
| Zero P0 defects | 0 | manual classification; P0 = crashes, data loss, security |
| Zero P1 defects | 0 | P1 = broken core flow (parse → generate → assemble → export) |
| P2 defect count | ≤ 5 documented | P2 = degraded UX, recoverable failure |
| Backend test pass rate | 100% | `pytest packages/core/tests` |
| Backend test coverage | ≥ 70% | `pytest --cov`, fail if below |
| Renderer test pass rate | 100% | `vitest run` in `apps/desktop` |
| E2E test pass rate | 100% | `playwright test` in `apps/desktop` |
| IPC contract test pass rate | 100% | all handlers covered by `test_post_audit_ipc_contracts.py` family |
| Cold app boot to ready | < 3s | electron timing + a Playwright assert |
| Drag-drop screenplay → first shot routed | < 30s | E2E flow |
| `pre-commit run --all-files` | green | clean tree pre-merge |
| Lint+format (ruff + eslint + prettier) | 0 errors | green |
| Open feat-PR count (excl. dependabot) | 0 | merge or close all 11 yesterday-session PRs |
| Open security-relevant dependabot PRs | 0 | resolve all 14 dependabot PRs |
| Silent-fail audit | 0 sites | grep+test sweep for write-empty-stub patterns beyond PR #96 |
| Production docker-compose builds + runs | green | `docker-compose -f docker-compose.prod.yml build && up` smoke |
| Alembic migrations: up → down → up | green | clean reset of dev DB |

### B. Video quality bars (on RADAR_LOVE_2 + IMPOSSIBLE_FULL)

| metric | V0 (slop) | target | notes |
|---|---:|---:|---|
| ref_sim_best_mean (identity floor) | 0.5332 | ≥ 0.70 | currently V5 hits 0.80 with full Animate |
| inter_shot_diversity (lower=better) | 0.6191 | ≤ 0.60 | V8 hit 0.60 already |
| worst-cluster rigidity | n/a | < 0.85 | identity tight without total collapse |
| Per-character self-sim min | 0.564 | ≥ 0.70 | currently V5 ellie hits 0.865 |
| Grant's watch-it grade | 1/5 | ≥ 4/5 | Grant's grade after watching the with-audio mp4 |
| Distinct character clusters at n≥3 | 5 (V0) | ≥ 5 | scene coverage stays broad |
| Assembly success rate | inconsistent | 100% | PR #96 closes silent-fail; no 0-byte stubs |
| Pipeline assembly wallclock | ≤ baseline | within 1.2× of V0 | quality doesn't tank speed |
| No-silent-fallback audit | unknown | 0 sites | beyond PR #96; covers all pipeline stages |

**Industry-shaking proof point**: side-by-side comparison against one public reference (e.g., a Sora demo or Wan 2.2 official sample) where Grant rates SceneMachine output as "competitive or better."

---

## 1. Inventory (Stage 0)

Before any test/fix, build a complete map. Outputs:
- `docs/INVENTORY_SURFACES.md` — every surface that exists
- `docs/INVENTORY_DEFECTS.md` — every known broken thing
- `docs/INVENTORY_DEFERRED.md` — anything intentionally out of scope

### 1.1 Desktop app (Electron)

Parallel agent task. For each, capture (a) what it does, (b) what state it depends on, (c) what would break it, (d) does it have a test, (e) does it have user-facing copy that needs polish.

- [ ] Every page route under `apps/desktop/src/renderer/pages/`
- [ ] Every tab/section per page
- [ ] Every button/link/menu item
- [ ] Every drag-drop target
- [ ] Every form field + validation rule
- [ ] Every modal / dialog / confirmation
- [ ] Every toast / notification / error surface
- [ ] Every loading state + spinner + progress bar
- [ ] Every empty state ("no projects yet", "no shots generated", etc)
- [ ] Every keyboard shortcut
- [ ] Every settings panel + value
- [ ] Window: minimize, maximize, close, multi-monitor
- [ ] App lifecycle: cold boot, warm restart, crash recovery
- [ ] Auto-update flow (electron-builder configured)

### 1.2 IPC layer

- [ ] Catalog every handler in `packages/core/scenemachine/ipc/handlers.py` (7082 lines — full enumeration via grep `def handle_`)
- [ ] Catalog every IPC channel name + payload shape
- [ ] Map every renderer-side `electron.ipcRenderer.invoke('X', …)` call to a handler
- [ ] Find orphaned IPC: handlers without callers, callers without handlers (the "ghost-IPC" bug class PR #48/#49 fixed instances of)

### 1.3 Backend services + generators

- [ ] `packages/core/scenemachine/services/*.py` — every service
- [ ] `packages/core/scenemachine/generators/*.py` — comfyui, actcore, registry, stack_router
- [ ] `packages/core/scenemachine/utils/*.py` — ffmpeg, cache, circuit_breaker, etc
- [ ] `packages/core/scenemachine/workflows/*.py`
- [ ] `packages/core/scenemachine/agents/*.py`
- [ ] `packages/core/scenemachine/parsers/*.py`

### 1.4 Database

- [ ] All 22 tables enumerated (already partial)
- [ ] Alembic migrations: chain integrity (PR `fix/alembic-broken-migration-chain` hints at past trouble)
- [ ] Foreign-key constraints + cascade behavior
- [ ] What lives in `performers`/`auctions`/`bookings`/`performer_ratings`? Is the marketplace surface alive or skeleton?

### 1.5 External integrations

- [ ] ComfyUI: server lifecycle (PR #92 patched VRAM leak; root fix?), all 6 video providers in the registry
- [ ] Ollama: Qwen 72B (for V3 prompts), other models loaded
- [ ] FFmpeg: every ffmpeg call site (`packages/core/scenemachine/utils/ffmpeg.py` is 307 lines)
- [ ] HuggingFace: push paths, repo IDs, token usage
- [ ] gTTS / chatterbox TTS (PR #73)
- [ ] InsightFace (PR #60), CLIP-ViT-H

### 1.6 CI + tooling

- [ ] GitHub Actions workflows in `.github/workflows/`
- [ ] Pre-commit hooks (`.pre-commit-config.yaml`)
- [ ] Husky hooks
- [ ] Pyproject + package.json scripts

### 1.7 Deployment

- [ ] `docker-compose.yml` (dev), `.staging.yml`, `.prod.yml`
- [ ] `k8s/` manifests
- [ ] `monitoring/` (prometheus? grafana?)

### 1.8 Open work

- [ ] All 11 yesterday-session feat-PRs (#65–#73, #92, #95) — read, classify, plan disposition
- [ ] PR #96 (no-silent-fail harness fix — mine, awaiting review/merge)
- [ ] 14 dependabot PRs (#74–#91)
- [ ] Branches without PRs (any?)

**Stage 0 estimated work**: 2-4h with multi-agent parallelization (one Explore agent per surface category).

---

## 2. Surface-area stress test (Stage 1)

For each surface from Stage 0, define a stress battery. Each battery has: (a) preconditions, (b) inputs, (c) expected outcome, (d) failure mode classification.

### 2.1 Desktop app battery

- **Fuzz drag-drop**: 50 file types (txt, pdf, fountain, fdx, binary, 0-byte, 100GB sparse, symlink loop, file in unreadable dir)
- **Large screenplays**: 1-scene, 47-scene (RADAR_LOVE_2 baseline), 106-scene (IMPOSSIBLE_FULL), 500-scene synthetic
- **Concurrent ops**: 2 generations running, 2 users (multi-window), generate while preview rendering
- **Network failure**: backend down, network partition mid-generation
- **Long-running**: 8h overnight runs (V3, V5 already tested overnight); confirm progress UI doesn't bleed memory
- **State persistence**: kill app mid-pipeline, restart, verify resume from snapshot (PR #50 wired this)
- **Settings round-trip**: change every setting, restart app, verify persisted
- **Keyboard nav**: tab through every interactive element, no traps
- **Screen reader**: VoiceOver smoke test on the main flow

### 2.2 IPC battery

- **Schema fuzz**: every handler called with: valid input, missing required field, wrong type, extra fields, null, undefined, huge string, deeply nested object, circular ref, SQL injection strings
- **Concurrency**: 10 parallel invocations of the same handler with different params; verify no race
- **Slow handlers**: 30s+ handler with renderer timeout = 5s; verify graceful timeout
- **Renderer crash**: crash mid-handler; verify backend doesn't leak resources

### 2.3 Pipeline battery

- **Empty input**: 0 scenes
- **Single shot**: 1 scene, 1 shot (validates the single-shot copy path in `_assemble_movie`)
- **Full corpus**: RADAR_LOVE_2 (47) + IMPOSSIBLE_FULL (106) on every preset V0–V8 + V4_continuity (fixed)
- **External-out**: ComfyUI down (caught 2026-05-19), Ollama down, FFmpeg missing, HF unreachable
- **Mid-run kill**: SIGTERM at every stage boundary, verify clean state + resumable
- **OOM injection**: pre-allocate VRAM to leave < 2 GiB free, verify graceful failure (caught 2026-05-20)
- **Disk full**: tmpfs limit, verify error message
- **Concurrent runs**: 2 benchmarks at once (likely refused but should fail clean)
- **Quality gate edge cases**: shot with zero motion, shot with all-black frames, shot with mismatched aspect ratio

### 2.4 DB battery

- **Migrations**: fresh DB up to head, head down to base, base up to head, verify checksum match
- **Constraint violations**: delete a project with shots; orphan a shot; cycle in `previous_version_id`
- **Concurrent writes**: 10 parallel scene-creates, verify no dup `scene_number`
- **Large rows**: 1MB `raw_content`, 10MB `generation_metadata` JSON
- **SQLite lock**: long-running read + write; WAL mode check

### 2.5 Audio + lipsync battery

- **Audio mix**: every screenplay's narration mux (PR #73 path)
- **TTS failure**: gTTS rate-limited, chatterbox crash
- **Mismatch**: 47-shot video vs 30-scene narration vs 50-scene narration

### 2.6 Marketplace surface (if alive)

- `performers`, `auctions`, `auction_bids`, `bookings`, `performer_ratings` tables suggest a feature surface
- Need Stage 0 to determine: is this implemented or skeleton?

**Stage 1 estimated work**: 8-16h with parallelization (one agent per battery category). Output: `docs/STRESS_TEST_REPORT.md` with defect catalog.

---

## 3. Defect triage + fix sprint (Stage 2)

After Stage 1, every defect gets:
- Severity (P0/P1/P2/P3)
- Reproduction steps
- Owner (agent + branch name)
- Estimated effort
- Regression test plan

**Severity definitions:**
- **P0**: crash, data loss, security vuln, blocking core flow
- **P1**: broken feature, persistent silent-fail, ≥10× degraded perf, no workaround
- **P2**: degraded UX, recoverable failure, has workaround
- **P3**: polish, copy, edge case, nice-to-have

**Loop:**
1. Sort defect list by (severity desc, effort asc)
2. Take top item
3. Create branch `fix/<short-slug>`
4. Reproduce locally (or via agent)
5. Write failing test FIRST
6. Implement fix
7. Verify test passes + other tests still pass
8. Open PR
9. Auto-merge if green + CI passes + meets `auto_merge_policy` (see §6)
10. Else: notify Grant for review
11. Loop

**Stop condition**: P0 + P1 count = 0; P2 count ≤ 5 documented.

---

## 4. Video quality elevation V9+ (Stage 3, parallel)

Track B runs alongside A. Per [[project-scenemachine-v8-result]] and [[project-scenemachine-v3-null-result]], the missing mechanism is **identity carry-over across T2V shots**. The corpus harness limitation (1 shot per scene, found 2026-05-21) means V4_continuity as-launched doesn't even exercise the I2V mechanism — must be fixed before any V9 design.

### 4.1 Prerequisite: fix the harness corpus decomposition

- **Issue**: `scripts/run_benchmark.py:351` gives every shot a unique `scene_id` = `scene_number`, so I2V routing's per-scene grouping never has > 1 shot per group
- **Fix candidates** (decide before V4 redesign):
  - (a) Single-chain mode: for presets that test continuity, set `scene_id="_chain"` so all 47 shots form one I2V chain
  - (b) Multi-shot scene decomposition: split each scene into N shots based on duration (real screenplay shot breakdown)
  - (c) Hybrid: keep 1-shot-per-scene as default; let preset opt into chain mode
- **Recommended**: (a) for the V4 re-run (cheapest, tests the hypothesis cleanly), then (b) as a Stage 2 fix for realistic shot breakdown

### 4.2 V9+ experiment ladder

Each experiment defined with: hypothesis, mechanism, preset config, expected outcome, time budget, kill criterion.

- **V4_continuity (fixed)**: single I2V chain on RADAR_LOVE_2. Tests "does I2V's image-conditioning preserve character identity across T2V-style chains?" — Time: ~5h. Kill if first 10 shots show clear drift.
- **V9_lora**: per-character LoRA trained from each `character_refs/*.png`. Injected into T2V text-encoder when shot mentions that character. Tests "does a learned weight preserve identity without Animate?" — Time: ~3.5h training + 5h inference. Kill if LoRA loss doesn't converge.
- **V10_embed_inject**: extract Animate's CLIP-vision embedding for each character on first appearance, cache, inject into subsequent T2V text-encode for that character. Tests "is the embedding all we need to carry identity?" — Time: ~5h. Higher infra cost (StackRouter changes).
- **V11_animate_plus_diversity**: V5 base (full Animate) + active scene diversification (prompt jitter, seed variation per shot). Tests "can we keep V5's identity AND get diversity?" — Time: ~5h.
- **V12_hybrid_v8_v4**: V8's first-appearance-only Animate + V4's I2V continuity for intra-character shots. Tests "anchor with Animate, propagate with I2V?" — Time: ~5h.

Each gets a scorecard run via `wait_and_analyze.sh`. Each result feeds into the quality bar tracker.

### 4.3 Quality-bar gate

After each V9+ experiment, check whether **all** §0.B bars are met. If yes → call quality bar achieved → move to Stage 5 polish. If no → continue ladder OR pivot based on the gap (e.g., if diversity is fine but identity still below floor, double down on identity mechanisms).

### 4.4 Grant-in-the-loop checkpoints

Grant grades each watchable artifact 1/5. The grade is decisive — metrics can lie, eyes can't. Checkpoints:
- After V4_continuity (fixed) lands: Grant watches + grades
- After V11 or V12 (whichever first hits all metric bars): Grant watches + grades
- Industry-shaking proof: build a comparison strip vs public Sora/Wan demo; Grant grades

---

## 5. Hardening + regression locks (Stage 4)

Done in parallel with Stage 2; locks the wins.

### 5.1 Architectural debt

- **Merge the 11 yesterday-session PRs** to main (each gets a clean rebase + review)
- **Eliminate runtime `git checkout`** in `post_v8_sequencer.sh` — get all scripts on main
- **Add ComfyUI systemd unit** (or systemd-user) so reboot doesn't kill the GPU server
- **Silent-fail sweep**: grep every site that writes a "stub" file, asserts existence, or returns success on partial output. Extend PR #96's pattern. Target: 0 silent-fail sites.
- **Branching policy**: every fix on a `fix/*` branch, every experiment on `run/*`, no direct commits to main

### 5.2 Test coverage push

- **Coverage target**: 70% (current is ~5% based on the run we saw)
- Focus order: pipeline > generators > services > workflows > utils
- Every defect fix from Stage 2 ships with a regression test
- Add hardening tests covering the failure modes from Stage 1 batteries (so future regressions get caught in CI not prod)

### 5.3 CI gates

- pre-merge: `pytest` clean, `vitest` clean, `playwright` clean, `pre-commit` clean
- pre-merge: coverage ≥ 70%
- weekly: full battery against IMPOSSIBLE_FULL (the heavy corpus)
- nightly: smoke test against RADAR_LOVE_2

### 5.4 Runbooks

- `docs/RUNBOOK_BENCHMARK.md`: how to run V0–V12 from scratch
- `docs/RUNBOOK_COMFYUI.md`: start, restart, troubleshoot the GPU server
- `docs/RUNBOOK_INCIDENT.md`: what to do when the pipeline silent-fails (now ~0 if §5.1 sweep is real)
- `docs/RUNBOOK_DEPLOY.md`: staging + prod deploy

---

## 6. Polish + dazzle (Stage 5)

Last 10% takes 50% of the polish budget.

- **Error messages**: every user-facing error rewritten to (a) say what went wrong, (b) say what to try
- **Loading states**: every async op has a visual indicator
- **Empty states**: every "no data" surface looks intentional, not broken
- **Accessibility**: keyboard nav, focus rings, ARIA labels, color contrast
- **Performance**: app boot < 2s, first-shot < 1 min on fast preset
- **Onboarding**: first-run experience — pick a screenplay, see a result in < 5 min
- **Demo mode**: a curated 1-screenplay demo that always works (locked outputs, fast)

---

## 7. The /goal execution loop

When Grant fires `/goal`, I re-enter the plan. Each loop iteration:

```
1. Read this file (STRESS_TEST_PLAN.md) to refresh
2. Read state:
   - git log (recent commits)
   - gh pr list (open PRs + statuses)
   - tasks active (TaskList)
   - Monitor events (any failures since last loop?)
3. Identify next action:
   - If Stage 0 incomplete: continue inventory
   - Else if Stage 1 batteries unrun: run next battery
   - Else if defects in queue: take top defect
   - Else if V9+ experiment slot open: launch next
   - Else if Stage 4/5 incomplete: progress hardening or polish
4. Execute (delegate to subagents for parallel work where applicable)
5. Update state (PR opened, defect closed, memory updated)
6. Loop
```

### Auto-merge policy (Grant authorizes)

Default: every PR requires Grant approval. **Exceptions** Grant may pre-authorize:
- Pure regression-test additions (no behavior change)
- Dependabot PRs that ship green + don't touch runtime
- Typo fixes in docs/comments
- Test-only PRs from Stage 2 that ride a defect Grant already greenlit

If Grant doesn't authorize: I open the PR + ping in chat + wait.

### Stop conditions (when /goal exits)

- All §0 quality bars met (success — the legendary state)
- Hard blocker requires Grant decision (e.g., V9 hypothesis fork, marketplace surface scope)
- 3 consecutive iterations make no progress (escape hatch — surface why)

---

## 8. Risk register

| risk | severity | mitigation |
|---|---|---|
| GPU time budget overrun | high | every V9+ experiment has a kill criterion (§4.2); RADAR_LOVE_2 (47 shots) before IMPOSSIBLE_FULL (106) |
| Merging fragmented branches breaks main | high | green CI gate on every merge; one PR at a time |
| Silent-fail discoveries cascade | medium | grep audit (§5.1) before fix sprint; each fix adds a regression test |
| ComfyUI VRAM/state weirdness | medium | systemd unit (§5.1); restart-between-runs in sequencer (PR #92, already shipped) |
| Marketplace surface is huge skeleton | medium | Stage 0 determines; if huge skeleton, scope-defer to a v2 |
| Industry-shaking bar is subjective | medium | metrics + Grant's eye both required (§4.4) |
| Test infra has its own bugs | low | pyproject 80% coverage gate currently fails (saw "Total coverage: 4.66%" earlier); raise gradually |
| Plan changes mid-execution | low | this file is the source of truth; updates are PRs to it |

---

## 9. Open questions for Grant (BLOCKING before /goal fires)

These change the shape of the plan. Need explicit answers.

1. **Auto-merge authority**: which categories of PRs (§7) am I authorized to merge without explicit per-PR approval?
2. **Industry-shaking quality bar**: is metric-based (§0.B) enough, or do you want a specific public-reference comparison (e.g., "must hold up against Wan 2.2 official sample of similar genre")?
3. **Time horizon**: days, weeks, months? Affects parallelism + risk tolerance.
4. **GPU budget**: is overnight runs every night for V9+ acceptable? Any blackout windows?
5. **Marketplace surface scope**: if `performers`/`auctions`/`bookings`/`performer_ratings` is a substantial unbuilt feature, scope-defer or in-scope?
6. **What about V4 currently burning GPU on a confirmed-null?** Kill now (recommended), let finish for control data (5h waste), or kill and replace with V4_continuity fixed-harness re-run tonight?
7. **Multi-agent parallelism**: can I spawn 3-5 subagents in parallel for inventory/stress tests, or one at a time?
8. **Branch cleanup**: am I authorized to delete merged feat branches and stale dependabot branches?
9. **Grant's grading availability**: how do you want to be pinged when an experiment lands a watchable artifact? Chat message? File written to `~/scenemachine_movies/READY_TO_WATCH/`?
10. **Failure escalation**: when 3 consecutive loop iterations make no progress (§7 stop condition), what do you want? Pause + ask, or just stop?

---

## 10. Deliverables checklist

When this plan is fully executed:

- [ ] All §0 bars green
- [ ] All P0/P1 defects closed
- [ ] All 11 yesterday-PRs merged or closed
- [ ] At least one V9+ experiment lands all quality bars
- [ ] Comparison strip vs public reference exists + Grant grades ≥ 4/5
- [ ] `docs/RUNBOOK_*` complete
- [ ] CI gates active + green for ≥ 7 days
- [ ] Demo mode works (§6)
- [ ] STRESS_TEST_REPORT.md final version archived

When all green: SceneMachine is no longer trouble-ridden 1/5 slop. It's the legendary platform.

---

_End of plan v1.0. Updates land as PRs to this file. Next action after Grant answers §9: kill V4 (if confirmed), execute Stage 0 inventory._
