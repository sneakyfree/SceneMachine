# Inventory — Defect Catalog

_Started 2026-05-21 21:30 PDT by Dr. D Opus 4.7. Living document. Stage 1 stress-test agents append findings here._

## Severity definitions

- **P0** — crash, data loss, security, blocks core flow
- **P1** — broken feature, persistent silent-fail, ≥10× perf degradation, no workaround
- **P2** — degraded UX, recoverable failure, has workaround
- **P3** — polish, copy, edge case, nice-to-have

## P0 — open

| # | site | description | source | fix branch / PR |
|---:|---|---|---|---|
| P0-1 | `production_pipeline.py:489` `_check_blockers` | Returns `[]` on exception; caller treats as authoritative blocker list; corrupted engine silently proceeds | silent-fail audit | (pending) |
| P0-2 | `api/routes/lipsync.py` namespace `lipSync.*` vs renderer `lipsync.*` | 4 IPC handlers registered with camelCase, renderer calls lowercase; **entire lipsync UI dead** | IPC inventory | (pending — task #28) |
| ~~P0-3~~ | `files.downloadFile` IPC | Renderer calls; no handler exists; **export downloads broken** | IPC inventory | **closed**: handler added at `handlers.py` (path-traversal protected, data-dir sandboxed, name-collision safe). Loop iter 2 / PR follow-up. |
| P0-4 | `generation.listJobs` IPC | Renderer calls; only `generation.getPendingJobs` registered; **generation page job-list broken** | IPC inventory | (pending) |
| P0-5 | `screenplays.autoFix` + `.autoFixAll` IPC | Renderer calls; no handlers; **screenplay auto-fix dead** | IPC inventory | (pending) |
| ~~P0-6~~ | `sharing.deleteComment` IPC | Renderer calls; only `sharing.resolveComment` exists; **comment delete broken** | IPC inventory | **closed**: handler added, wraps `SharingService.delete_comment` (loop iter 3) |
| P0-7 | `crew.getLogs` IPC | Renderer calls; only `crew.getActionLogs` exists; **crew log view broken** | IPC inventory | (pending) |
| P0-8 | `analytics.setBudget` IPC | Renderer calls; no handler; **budget setting dead** | IPC inventory | (pending) |
| P0-9 | `docker-compose.prod.yml` references `./tools/docker/nginx.conf` + `./tools/docker/ssl/` | Both referenced but not tracked in repo; **production deploy broken** | CI inventory | (pending) |
| P0-10 | Alembic `005_actcore` downgrade | Missing explicit `performer_type_enum.drop()` calls; **`alembic downgrade base` fails on PostgreSQL** | DB inventory | (pending) |

## P0 — closed in flight

| # | site | description | closed by |
|---:|---|---|---|
| ~~P0-A~~ | `production_pipeline._assemble_movie` empty-input → 0-byte stub | Silent assembly fail | **PR #96** (open, awaiting CI) |
| ~~P0-B~~ | `production_pipeline._assemble_movie` both-strategies-failed → 0-byte stub | Silent assembly fail | **PR #96** |
| ~~P0-C~~ | `production_pipeline._assemble_movie` exception-during-assembly → 0-byte stub | Silent assembly fail | **PR #96** |
| ~~P0-D~~ | `ipc/handlers.py` 4× missing `sqlalchemy.select` import | 4 IPC handlers crash on use | **PR #97** (open, awaiting CI) |
| ~~P0-E~~ | `api/routes/generation.py` 2× missing `sqlalchemy.select` import | 2 review endpoints crash on use | **PR #97** |
| ~~P0-F~~ | `api/routes/lipsync.py` `_jobs` undefined in WebSocket endpoint | WebSocket endpoint crashes on connect; rewrote to use LipsyncJob model | **PR #97** |
| ~~P0-G~~ | `parsers/pdf.py:240` `fitz` undefined in `_ocr_page()` | PDF OCR path crashes; added local import | **PR #97** |
| ~~P0-H~~ | CI broken on main (8135 ruff violations, format drift, package-lock drift) | Every PR red on infrastructure failure | **PR #97** |

## P1 — open

| # | site | description | source |
|---:|---|---|---|
| P1-1 | `production_pipeline.py:605` `extract_last_frame()` | Returns None on failure; next shot falls back to T2V silently; caller can't see why I2V routing died | silent-fail audit |
| P1-2 | `services/character_image_generator.py:489` | Returns `success=True` with empty file when PIL import fails; downstream treats as real image | silent-fail audit |
| P1-3 | `generators/replicate.py:521` `_generate_thumbnail()` | Returns None on failure without error detail | silent-fail audit |
| P1-4 | `services/audio.py:210` MockTTSProvider.touch() | Creates empty file, reports success; lip-sync fails on silent audio | silent-fail audit |
| P1-5 | `services/video_quality_reviewer.py:440` Laplacian failure | logger.debug() when 100% of frames fail; returns score 0.5/conf 0.1 (look-acceptable) | silent-fail audit |
| P1-6 | `parsers/pdf.py:249` `_ocr_page()` returns None on OCR fail | Caller can't distinguish attempted-failed from not-attempted | silent-fail audit |
| P1-7 | `run_benchmark.py:351` `scene_id = scene_number` | One shot per scene → I2V routing never fires (V4_continuity null result confirmed 2026-05-21) | V4 run forensics |
| P1-8 | `scripts/v_scorecard.py` auto-recommendation heuristic | Returns "tune face_strength + clip_vision_strength" for V3 (no Animate) and V8 (not a strength experiment) — preset-blind | V8/V3 results |
| P1-9 | `apps/desktop` lipsync-store.ts:214 | TODO: WebSocket connection to `/api/lipsync/ws/{job_id}` not implemented (matched on backend by P0-2/P0-F) | Electron inventory |
| P1-10 | `apps/desktop/src/renderer/pages/timeline.tsx:810` | TODO: "Integrate with actual audio tracks from project" — audio is placeholder | Electron inventory |
| P1-11 | ComfyUI VRAM leak across workflow types (V8 Animate → V3 T2V) | T5 encoder OOMs because Animate weights pinned; mitigated in sequencer (PR #92) but root cause unaddressed at harness level | 2026-05-20 incident |
| P1-12 | No systemd unit for ComfyUI | Reboot kills GPU server; every restart costs 30+ min manual recovery | 2026-05-19 incident |

## P1 — closed in flight

| # | site | closed by |
|---:|---|---|
| ~~P1-A~~ | 6 IPC handlers had legacy/new same-Python-name pairs | **PR #97** noqa F811 |
| ~~P1-B~~ | 13 capability-detect F401 unused-import probes | **PR #97** noqa F401 |
| ~~P1-C~~ | `tests/mock_data_generator.py` `shot.id` inside `Shot(...)` constructor | **PR #97** pre-allocate shot_id |
| ~~P1-D~~ | `llm/enhanced_prompts.py` `field` import shadowed by loop var | **PR #97** rename loop var |

## P2 — open (selected, full list in stress test reports)

| # | site | description |
|---|---|---|
| P2-1 | `services/video_quality_reviewer.py:445` rmtree cleanup swallowed | Cleanup failure swallowed; /tmp fills silently |
| P2-2 | `utils/cache.py:806,829,855` Redis fallback warnings | Operator misses cache degradation |
| P2-3 | `services/production_pipeline.py:226-228` `_parse_screenplay` error truncation | Logger format truncates real error detail |
| P2-4 | `generators/comfyui.py:1658` thumbnail None without logging | Caller sees no indication of failure |
| P2-5 | 374 `E501` line-too-long sites | Soft-handled; bikeshed |
| P2-6 | 125 `B904` raise-without-from | Should be `raise X from err` |
| P2-7 | 005_actcore migration enum drops missing | Down-migration risk |
| P2-8 | Coverage gate mismatch | pyproject says 80%, CI enforces 60%, actual is 4.66% |
| P2-9 | Husky v9 deprecated | Will break in v10 |
| P2-10 | Pre-commit not enforced locally | Only CI runs hooks |
| P2-11 | 142 orphan IPC handlers (59% of 213) | Unintegrated UI / dead code; documents the sprawl |
| P2-12 | Frontend coverage not enforced in CI | Uploaded to codecov but no fail-gate |

## P3 — open (selected)

| # | site | description |
|---|---|---|
| P3-1 | `services/character_image_generator.py:498` `metadata={"mock": True, "empty": True}` | Contradictory flags |
| P3-2 | Settings page 64 KB monolithic | Sprawl risk |
| P3-3 | Marketplace surface: auctions + auction_bids SKELETON | DB-only, zero code; **scope-defer to v2** |
| P3-4 | Hardcoded staging URLs in `deploy.yml` | `https://staging.scenemachine.ai`, `https://app.scenemachine.ai` |
| P3-5 | Tracking ID rotation / Secrets Manager not configured for k8s | Env-only secrets |

## Stage 1 batteries — status

- [x] **Desktop app battery** — completed 2026-05-21 22:00 (agent a8fbea07b5bbdc446). 13 findings appended below.
- [x] **Marketplace surface battery** — completed same agent. 8 findings appended below.
- [ ] IPC schema fuzz — every Dict-accepting handler with malformed input (pending)
- [ ] Pipeline external-out — ComfyUI/Ollama/FFmpeg/HF down scenarios (manually covered: caught 2026-05-19 ComfyUI-down, 2026-05-20 VRAM-leak)
- [ ] DB migration up/down/up cycle (alembic 005 downgrade missing enum drops — P0-10)
- [ ] Audio + lipsync paths (lipsync.* P0-2 already documented)

## Stage 1 desktop battery findings (2026-05-21)

### Form validation gaps
- `apps/desktop/src/renderer/components/booking-modal.tsx:91` | P1 | duration not range-checked before send
- `apps/desktop/src/renderer/components/booking-modal.tsx:96` | P2 | `projectId || undefined` passes null to backend
- `apps/desktop/src/renderer/pages/settings.tsx:152` | P2 | API key input accepts empty strings

### Error boundaries
- `export.tsx`, `scene-planning.tsx`, `actforge.tsx`, `timeline.tsx` | P1 | no `<PageErrorBoundary>` wrappers — pages crash the whole renderer on error

### Long-running ops without abort
- `pages/export.tsx:301` | P1 | `assembly.export` (60–600s) has no Cancel button → user trapped during export
- `pages/scene-planning.tsx:255` | P1 | `scenes.generateBreakdown` lacks loading state + abort

### Empty states
- `pages/timeline.tsx:357` | P2 | bare `.map()` without empty-state guard

### Drag-drop hardening
- `components/screenplay-upload.tsx:504-537` | P2 | extension-only validation, no size or MIME check

### Accessibility
- `components/performer-card.tsx:204-221` | P2 | "Blink (10s)" / "Full Booking" buttons missing aria-label
- `components/lipsync/lipsync-panel.tsx:126-143` | P2 | Info button tooltip has no accessible text

### Settings page sprawl
- `pages/settings.tsx` 1725 lines | P2 | monolithic, needs decomposition into `components/settings/*`

## Stage 1 IPC fuzz + DB migration + audio/lipsync findings (2026-05-23)

### IPC authorization gaps (P0 — security)
- `ipc/handlers.py:232-254` `handle_delete_project` | P0 | deletes any project by id with **NO ownership check** — any renderer can delete another user's project. Fix: `if project.owner_id != current_user_id: raise PermissionError`.
- `ipc/handlers.py:456-474` `handle_delete_screenplay` | P0 | same authz gap.
- `ipc/handlers.py:1213-1240` `handle_delete_shot` | P0 | same authz gap.

### ~~Missing migration for lipsync_jobs~~ (P0) — **CLOSED**
- `packages/core/scenemachine/models/lipsync_job.py` model exists but **no alembic migration creates the table** (001-006 don't include it). Fresh DB → "relation lipsync_jobs does not exist". Fix: write migration 007.
- **Closed** by `packages/core/alembic/versions/007_add_lipsync_jobs.py` — creates table + `lipsync_job_status` enum + 4 indexes (shot_id, video_asset_id, audio_asset_id, status); downgrade is symmetric. Verified upgrade → downgrade → upgrade cycle on temp sqlite db with stubbed shots/assets tables. Loop iter 1, 2026-05-24.

### IPC path traversal (P1)
- `ipc/handlers.py:290-319` `handle_upload_screenplay` opens `Path(file_path)` directly. `file_path="../../etc/passwd"` reads anything. Fix: validate under safe dir; `Path.resolve()` + whitelist.
- `ipc/handlers.py:779-801` `handle_add_character_reference` same vulnerability.

### IPC UUID-parse fragility (P1)
- `ipc/handlers.py:99,201,236,265,...` | P1 | 40+ handlers do bare `UUID(id)` cast → `ValueError` propagates → renderer hangs. Fix: wrap or Pydantic validator.

### IPC pagination unbounded (P2)
- `ipc/handlers.py:59-72,1676,3226,3541,3613` | P2 | `limit` param lacks upper bound. `limit=999999999` → memory exhaustion.

### DB migration 004 missing index drops (P2)
- `004_add_integrity_constraints.py` creates indexes; downgrade misses several (e.g. `ix_project_shares_unique`). down→up→down leaves orphans.

### CASCADE asymmetry in lipsync_jobs (P1)
- `models/lipsync_job.py:58,64,72` | P1 | video/audio_asset_id CASCADE on delete, output_asset_id SET NULL. Inconsistent.

### Audio service fallback gaps (P2)
- `services/audio.py:750-764` | P2 | ElevenLabs failure has no fallback to OpenAI/Mock.
- `services/audio.py:519-524` | P2 | `_get_audio_duration()` fallback uses `size/16000` heuristic — wildly wrong on corrupted files; lipsync timings desync silently.

## Stage 1 pipeline external-out failure modes (2026-05-23)

### ComfyUI workflow output gaps (P0)
- `generators/comfyui.py:1547-1565` | P0 | `outputs` dict can be empty after status checks pass — workflow executed but produced no files. Shot `video_path=None`; assembly raises AssemblyError (per PR #96) but ComfyUI-side root cause unknown.
- `generators/comfyui.py:455-462` | P0 | API succeeds but response.json() lacks `prompt_id` → silent no-op. Fix: validate response shape.
- `generators/comfyui.py:1551-1554` | P0 | Race: two queued jobs with same prompt_id history can overwrite. Add client_id filtering.

### FFmpeg truncated/0-byte outputs (P0)
- `utils/ffmpeg.py:452,538` | P0 | `extract_frame`/`concatenate_videos` returncode=0 but output 0-byte or partial (av1 GOP rounding, or timeout-killed mid-write). Fix: verify `output.stat().st_size > 0` before returning.

### Network without timeouts (P1)
- `add_audio_to_movie.py:113-117,130,164,182` | P1 | `subprocess.run(["ffmpeg/ffprobe", ...])` never sets `timeout=`. Hangs forever if ffmpeg crashes.
- `comfyui.py:398,438,539,614,1654,1704` | P1 | httpx client timeout 10-30s per op, but ComfyUI jobs run hours; timeout fires mid-poll and kills jobs.

### TTS rate-limit + 0-byte mock (P1)
- `add_audio_to_movie.py:78-109` | P1 | gTTS retries no jitter; concurrent compound rate-limit.
- ~~`services/audio.py:212` MockTTSProvider .touch()~~ — **closed in PR #103**.

### Disk-space checks missing (P1)
- `utils/ffmpeg.py:462,551,654` | P1 | No `shutil.disk_usage()` check before writing. ffmpeg silently truncates on ENOSPC.

### HuggingFace push gaps (P1-P2)
- `run_benchmark.py:695-707` | P1 | HF push silently logged as warning on failure (rate-limit / token-expired).
- `run_benchmark.py:698-704` | P2 | No checksum validation post-upload.
- HF push has no timeout; can block indefinitely.

## Stage 1 marketplace battery findings (2026-05-21)

### Booking flow — money path bugs
- `api/routes/bookings.py:310-387` | P1 | `create_blink_booking()` accepts `max_price_usd=None` without validation → negative values silently ignored
- `api/routes/bookings.py:345-449` | P1 | `create_deep_booking()` / `create_epic_booking()` don't validate `requester_user_id` exists → orphan bookings possible
- `api/routes/bookings.py:452` | P1 | **race condition**: concurrent DEEP bookings on same performer both succeed → overselling
- `api/routes/bookings.py:360` | P1 | BLINK booking → MATCHED but `payment_status=PENDING`, **no escrow hold until performer accepts** → performer can deliver without payment guarantee
- `api/routes/bookings.py:754-784` | P1 | `rate_booking()` allows rating before `payment_status=RELEASED`
- `api/routes/bookings.py:743-750` | P1 | `cancel_booking()` only refunds ESCROWED, silently no-op on PENDING/RELEASED

### Performer search integrity
- `pages/actforge.tsx:62-69` | P1 | UI offers `sort_by` filter but backend `find_available_performer()` ignores it → "Sort by Price" returns ACI-sorted results

### Rating multi-rate vulnerability
- `models/performer_rating.py` | P2 | no DB unique constraint on `(performer_id, booking_id)` → race-create dup ratings

## CTO scope-defers (intentionally NOT fixed in this 72h sprint)

- **Auctions / auction_bids feature**: SKELETON, build-out is multi-week. Document and defer to v2.
- **130+ missing public-API annotations**: dedicated typing pass with mypy strict, separate sprint.
- **Replace husky with native git hooks**: low-value, deferred.
- **374 E501 line-too-long sites**: format-only, defer migration.
- **96 UP042 str-enum sites**: needs care for serialization compat, defer.
- **125 B904 raise-from**: bulk script + manual review, defer.
