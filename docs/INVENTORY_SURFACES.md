# Inventory — Surfaces

_Compiled 2026-05-21 ~21:00 PDT by Dr. D Opus 4.7 from 5 parallel Explore agents. Live snapshot for the STRESS_TEST_PLAN.md §1 Stage 0._

## Top-line numbers

| Surface | Count | Notes |
|---|---:|---|
| Electron pages | 15 | home, project (overview), character-lab, scene-planning, generation, timeline, export, analytics, settings, archive, help, admin, actforge, explainability, dna-strand-demo |
| Zustand stores | 21 | project, settings, toast, screenplay, character, scene, shot, generation, assembly, audio, sharing, experience, copilot, actforge, gpu-exchange, auth, asset, timeline, crew, lipsync, collaboration |
| React hooks | 6 | use-auto-save, use-keyboard-shortcuts, use-offline-cache, use-online-status, use-operation-progress, use-undo-redo |
| Top-level components | 62 | + 20 subdirectories with ~61 more (timeline/, generation/, characters/, etc.) |
| IPC handlers (backend) | 213 | distribution: 48 workflows, 28 gen/asm, 22 settings/audio, 42 advanced, 41 infra, 32 media |
| IPC channels called by renderer | 71 unique (87 sites) | **142 handlers orphaned** (59% never called) |
| Backend service modules | 43 | services/ dir |
| Backend generators | 7 | comfyui, replicate, fal, runpod, mock, actcore (legacy), registry |
| Backend utils | 4 | circuit_breaker, cache, ffmpeg, logging |
| Workflows | 5 | base, generation, screenplay, export, agentic_crew |
| Agents | 6 | parser, generator, character, assembler, export, reviewer (orchestrator unwired) |
| Parsers | 3 | fountain, fdx, pdf |
| SQLAlchemy models / DB tables | 24 (22 main + 2 timeline) | core, marketplace (performers/bookings ALIVE, auctions SKELETON), collaboration |
| Alembic migrations | 6 | chain intact: 001 → 002 → 003 → 004 → 005 (actcore) → 006 |
| Renderer unit tests | 43 | components 16, stores 12, hooks 1, pages 6, hardening 3, complete-workflow 5 |
| Renderer E2E tests | ~210 across 11 files | app, project-workflow, character-workflow, scene-planning, generation, timeline-export, complete-workflow, supporting-pages, etc |
| CI workflows | 3 | ci.yml (8 jobs, 5 required), deploy.yml (5), security.yml (7, continue-on-error) |
| Docker compose envs | 3 | dev, staging, prod (with monitoring profile) |
| K8s manifests | base + overlays staging/production + monitoring |  |

## Routes (Electron pages)

- `/` → `home.tsx` — Project list, creation, search, deletion
- `/project/:projectId` → `project.tsx` — Project dashboard
- `/project/:projectId/characters` → `character-lab.tsx` — Character mgmt + variations + ref uploads
- `/project/:projectId/scenes` → `scene-planning.tsx` — Scene list + breakdown
- `/project/:projectId/generate` → `generation.tsx` — Shot gen queue + cost
- `/project/:projectId/timeline` → `timeline.tsx` — Timeline editor (54 KB file — large)
- `/project/:projectId/export` → `export.tsx` — Assembly + export
- `/analytics` → `analytics.tsx` — Dashboard
- `/settings` → `settings.tsx` — Prefs, API keys (64 KB — sprawl risk)
- `/archive` → `archive.tsx` — Project archival
- `/help` → `help.tsx` — Docs
- `/admin` → `admin.tsx` — Circuit breakers, worker status
- `/actforge` + `/project/:id/actforge` → `actforge.tsx` — Performer discovery
- `/(project/:id/)explainability` → `explainability.tsx` — AI decision traces
- `/dna-strand-demo` → `dna-strand-demo.tsx` — Demo visualization

## IPC surface — high-risk fuzz candidates

**Schema fuzz (dict-accepting handlers):**
- `projects.create/update` — settings: Dict[str, Any] — HIGH
- `settings.update` / `settings.import` — Dict[str, Any] bulk — HIGH
- `timeline.save` — clipData Dict — HIGH
- `textOverlays.create/update` — overlayData + styling — HIGH
- `copilot.*` (9) — context Dict[str, str] — MEDIUM
- `overlays.save`, `colorGrade.save` — MEDIUM

**UUID-parsing fragility:**
- 40+ handlers do bare `UUID(id)` without try/except → crash on malformed input

**Long-running (UI timeout risk if no progress streaming):**
- `screenplays.parse` 5-30s
- `scenes.generateBreakdown` 10-60s
- `moviePlan.generate` 30-120s
- `audio.generateSpeech` 5-30s × N scenes
- `lipSync.analyzeAudio` 10-60s
- `assembly.assembleMovie` 30-300s
- `assembly.export` 60-600s — **CRITICAL hang risk**
- `pipeline.run` 5-30 min — **will timeout in renderer**
- `copilot.analyze/chat` 5-30s

## Backend pipeline call chain (stress focus)

```
ProductionPipeline.run()
  → parsers (FountainParser / FDXParser / PDFParser)
  → ShotListGenerator.generate()
  → BlockersEngine.analyze_project()
  → CharacterService.generate_character_prompt()
  → stack_router.route_shot()
  → generators (ComfyUI / Replicate / FAL / RunPod)     [heavy]
  → VideoQualityReviewer.review_video()                  [bottleneck]
  → TTSProvider (ElevenLabs / OpenAI / Mock)
  → LipSyncProvider                                       [optional]
  → AssemblyService.export() via FFmpeg                  [I/O heavy]
  → SnapshotService.create_snapshot()                    [audit]
```

## Marketplace surface verdict

| table | DB | service | IPC | UI | tests | verdict |
|---|---|---|---|---|---|---|
| performers | ✓ | ✓ aci.py | ✓ performers.* | ✓ actforge.tsx + PerformerCard | ✓ | **ALIVE** |
| performance_takes | ✓ | partial | ✗ | ✗ | ✓ seeds | **WIRED** |
| bookings | ✓ | ✓ billing | ✓ bookings.* | ✓ BookingModal | ✓ | **ALIVE** |
| auctions | ✓ | ✗ | ✗ | ✗ | ✓ | **SKELETON** — scope-defer |
| auction_bids | ✓ | ✗ | ✗ | ✗ | ✗ | **SKELETON** — scope-defer |
| performer_ratings | ✓ | ✓ aci | ✓ ratings.* | partial | ✓ | **WIRED** |

**Decision (CTO call)**: auctions + auction_bids are SKELETON — scope-defer to a future "Marketplace v2" milestone. Don't fix in this 72h sprint. Document the deferral.

## CI workflows (current state)

**ci.yml** — 8 jobs, **5 required for merge**: python-lint, python-test, frontend-lint, frontend-test, ci-success. Currently **ALL RED** on every open PR (ruff + mypy violations on pre-existing code).

**deploy.yml** — staging + production. Production deploy referenced `./tools/docker/nginx.conf` and `./tools/docker/ssl/` which **are not in the repo** — production deploy is broken until those land.

**security.yml** — 7 jobs, `continue-on-error: true` so they don't block. Good for our case.

## Architectural debt summary

1. **CI gates fail on main** (ruff, mypy strict, coverage 4.66% vs 80% gate) → blocks every merge
2. **lipSync vs lipsync case collision** → entire lipsync UI dead
3. **14 IPC caller-without-handler mismatches** → broken features
4. **142 orphan IPC handlers** (59%) → either dead code or unintegrated UI
5. **6 untracked scripts** in `/scripts` (yesterday's session) — should be part of the relevant PRs
6. **nginx.conf + SSL not tracked** → prod deploy broken
7. **Husky deprecated**, pre-commit not enforced locally
8. **005_actcore migration**: downgrade missing enum drops → CI test `alembic up/down/up` would fail
9. **2 hardening test gaps**: lipsync WebSocket not implemented, timeline audio tracks placeholder

See `INVENTORY_DEFECTS.md` for the actionable defect list (populated by Stage 1).
