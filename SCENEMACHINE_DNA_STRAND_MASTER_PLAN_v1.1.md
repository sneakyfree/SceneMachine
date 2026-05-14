# SCENEMACHINE DNA STRAND MASTER PLAN — v1.1
## A+ Blueprint: Screenplay-to-Movie Generation Platform
### Version 1.1 · 2026-05-14 · Accepts platform pivots discovered by the 2026-05-14 DNA-strand audit

---

## CHANGELOG (v1.0 → v1.1)

v1.0 was the January 2026 blueprint authored before the codebase existed. v1.1 captures the platform reality the team has shipped to and explicitly resolves the six open binary decisions surfaced by the 2026-05-14 DNA-strand gap analysis.

| # | v1.0 baseline | v1.1 reality | Status |
|---|---|---|---|
| **0.2** | FastAPI HTTP backend | IPC socket (FastAPI app exists but is unused at runtime in the Electron app) | **Accepted** |
| **0.3** | PostgreSQL + SQLAlchemy 2.0 async | SQLite + SQLAlchemy 2.0 async (Postgres supported via env var; not used in dev or single-user prod) | **Accepted** |
| **0.4** | Redis + Celery task queue | asyncio poll loop (`services/queue_worker.py`); Redis is optional cache only | **Accepted** |
| **0.6** | JWT authentication required | **Single-user desktop v1; auth scaffolding to be deleted in R-0**. Multi-user is a v3 question. | **Resolved** |
| **3.2** | Wan 2.1 local | Wan 2.2 family (T2V FP8 + I2V FP8 + Animate BF16) — proven at 153-shot scale 2026-05-14 | **Accepted** |
| **3.3** | Lambda Labs cloud | RunPod + Replicate (Lambda Labs never built; dropped); Fal marked experimental | **Resolved — drop Lambda** |
| **3.5** | Kokoro TTS | ElevenLabs + OpenAI TTS shipped; Kokoro deferred to R-2 as offline-only option | **Resolved — defer Kokoro** |
| **3.6** | Wav2Lip / SadTalker / LatentSync lipsync | LatentSync + Rhubarb only; Wav2Lip & SadTalker enum values to be deleted in R-2 (renderer-touching refactor) | **Resolved — drop Wav2Lip/SadTalker** |
| **6.*** | Agentic Crew integrated into pipeline | **Currently bypassed; ADOPT in R-3 by refactoring production_pipeline.py to delegate phase-by-phase to agents.** Differentiator-class feature. | **Resolved — adopt later** |
| **7.10** | PWA (Next.js + service worker) | Electron desktop app (PWA service worker file still present but unused) | **Accepted — Electron is correct for local-GPU workflow** |

**Scope creep accepted** (13 features added to v1.1, scheduled R-6/R-7): ActForge, BookingModal, Archive, Sharing/Comments, Watermark picker, Text overlays, Music & SFX libraries, Color grading, Template selector, GPU Exchange, Movie Plan viewer, Help page, Story Mode Wizard (replaces Phase 7.2's screenplay-import wizard).

**Scope creep deleted** (7 features removed in R-0): DNA Strand Demo page, Admin page, Steven AI Assistant (rebuilt grounded in R-7), per-take performer ratings (rebuilt with ActForge in R-7), standalone Approval Queue (absorbed into Agentic Crew UI in R-3), 4 orphan auth components, IPAdapterControls fetch-to-nowhere (fixed to IPC in PR #51).

---

## PREAMBLE

> **SceneMachine** is the "Adobe Premiere of generative video" — but for grandma. She drag-drops a screenplay before bed, walks away, wakes up to a movie. No login screens. No technical settings to twiddle. No cliffs of complexity. The grandma test is the lodestar — every feature must serve her drag-drop-to-movie journey or it's premature.

The platform's foundation is **proven** as of 2026-05-14: 153 video shots generated across two real screenplays (47-scene RADAR LOVE 2 + 106-scene IMPOSSIBLE_FULL) in 5h 53min of unattended pipeline runtime, with zero drift and zero OOMs at a steady 2:20 per shot wallclock. The bedrock holds. The job from here is to pour each higher pyramid layer carefully — no styrofoam between marble.

---

## END-STATE VISION (unchanged from v1.0)

> **The 30-Second Pitch**: Upload a screenplay. Click generate. Watch your movie render. Download a professional-quality film with consistent characters, synchronized dialogue, and cinematic polish — all without leaving SceneMachine.

### Success Metrics (refined for v1)

| Metric | v1 Target | Measurement |
|---|---|---|
| Grandma-test pass rate | 20/20 reference screenplays | Drag-drop reference screenplay → unattended → watchable mp4 |
| Script-to-First-Frame | < 90 seconds (cold) | Cold-load + first shot completion |
| Character Consistency | > 85% similarity (Wan 2.2 Animate baseline) | InsightFace embedding distance across same-character shots |
| Lip-Sync Accuracy | < 80ms drift | LatentSync default config |
| Full Pipeline Success | > 95% | Reference screenplays completing without intervention |
| User Satisfaction | > 4.5/5 | Post-generation survey (R-5 beta program) |
| Cost Efficiency (local) | < $0.05/sec final video (electricity only) | Cost tracking + power meter |
| Cost Efficiency (cloud) | < $0.25/sec final video | RunPod/Replicate billed per shot |

---

## V1 ROADMAP (8 phases, foundation-first)

Each phase is a structural block in the pyramid. No phase begins until the one below it passes its R-X acceptance test.

| Phase | Name | Duration | Acceptance test (definition of "poured") |
|---|---|---|---|
| **R-0** | **Subtract & lock decisions** | 2 weeks (currently ~60% done) | Codebase ~3000 LoC smaller; 6 binary decisions captured in v1.1; tonight's 9 PRs landed in main |
| **R-1** | **Bulletproof grandma journey** | 4 weeks | 20/20 reference screenplays produce watchable mp4 unattended; zero crashes; zero silent failures |
| **R-2** | **Honest quality** | 4 weeks | Quality scores are real (no hardcoded 0.85s); snapshots auto-captured at every stage; contradiction detection live; voice cloning UX complete |
| **R-3** | **Agentic + Explainable** | 6 weeks | production_pipeline.py delegates phase-by-phase to specialist agents; every decision logged with confidence; approval gates fire at < 0.6 confidence; AgentActivityFeed shows live decisions |
| **R-4** | **UX 9+/10** | 4 weeks | Lighthouse Performance ≥90 on every page; skeleton loaders everywhere; first-paint < 200ms; keyboard nav complete; undo on every non-destructive action |
| **R-5** | **Production scale** | 4 weeks | 10 concurrent users; nightly canary; Sentry alerts wired; 5 beta testers complete full screenplay → movie unaided |
| **R-6** | **Differentiation** | 4 weeks | Sharing/comments, color grading, music+SFX library, text overlays, templates, watermarks, story-mode wizard live |
| **R-7** | **Premium tier** | 4+ weeks | ActForge marketplace, Movie Plan viewer, Steven AI Assistant rebuilt with project-grounding |

**~24 weeks to v1** (through R-5) · **~32 weeks to v1 + premium** (through R-7).

---

## D.1 End-State Vision (preserved from v1.0)

[Identical to v1.0 — pitch, success metrics, market position. The vision is unchanged; only the implementation deviations are renegotiated above.]

## D.2 Scope Envelope (revised for v1.1)

### In Scope (v1.1 baseline)

**Foundation features (v1.0 retained):**
- Screenplay import (.fountain, .fdx, .pdf, .txt)
- AI-powered shot breakdown
- Character Laboratory with face-embedding consistency
- Local (Wan 2.2) + Cloud (RunPod, Replicate) video generation
- TTS dialogue (ElevenLabs, OpenAI)
- Lip-sync (LatentSync, Rhubarb)
- FFmpeg assembly with transitions and audio mixing
- Multi-view explainability dashboard
- Audit-grade snapshot history
- Electron desktop frontend

**Added in v1.1 (accepted from scope creep):**
- ActForge talent marketplace (R-7)
- BookingModal tiered bookings (R-7)
- Archive — `.smr` project zip-share-restore (R-6)
- Sharing & comments simplified for single-user — share = exportable bundle (R-6)
- Watermark picker with custom images (R-6)
- Text overlays — lower thirds, titles, captions (R-6)
- Music & SFX library (R-6)
- Color grading with LUT support (R-6)
- Template selector — pre-built project starters (R-6)
- GPU Exchange — multi-provider cost comparison (R-2 — extension of plan 3.3)
- Movie Plan viewer — AI-generated treatment from logline (R-7)
- Help page (R-1 — required for grandma)
- Story Mode Wizard — "I have an idea" guided flow (R-1 — replaces v1.0's Phase 7.2 wizard)

### Explicit Non-Goals (v1.0 + v1.1)

- Real-time video streaming
- Collaborative multi-user editing (deferred to v3)
- Mobile native apps (Electron desktop only)
- Integration with external NLEs (Premiere, DaVinci)
- Music composition or scoring
- 3D asset generation
- VR/AR output
- Live streaming

### Explicit DELETED scope (was in v1.0 or scope creep)

- JWT authentication / Login flow (single-user desktop)
- Admin user dashboard (single-user desktop)
- DNA Strand Demo page (was a marketing meta-page)
- Steven AI Assistant first version (to be rebuilt grounded in R-7)
- Wav2Lip lip-sync provider (no implementation existed)
- SadTalker lip-sync provider (no implementation existed)
- Lambda Labs cloud provider (no implementation existed)
- PWA service worker (Electron does not benefit)
- Kokoro TTS (deferred to R-2 conditional on offline-tier demand)

---

## D.3 Phased Rollout (full atomic tables in `RIBOSOME_PLAN_2026-05-14.md`)

The original v1.0 had 8 Phase tables (Phase 0 through Phase 8) covering ~70 atomic features. v1.1 reorganizes them under R-0 through R-7 with the audit-driven gap analysis baked in. See `RIBOSOME_PLAN_2026-05-14.md` in the repo for the full ~85 codon atomic plan with acceptance tests per codon.

R-0 codon status as of v1.1 publication:

- ✅ **Merge tonight's foundation PRs** (#44, #45, #46, #47 — overnight discovery + fix)
- ✅ **Reconcile worst ghost-IPC** (#48 pipeline aliases, #49 blockers, #50 snapshots, #51 IPAdapter, #52 regression tests)
- ✅ **Master Plan v1.1** (this document)
- ⏳ **Subtraction Sprint** (delete ~3000 LoC of dead/styrofoam code; next session)
- ⏳ **Mount-or-delete orphan components** (DialoguePanel, VoiceSelector, FaceSimilarityPanel, AgentActivityFeed, ApprovalQueue; next session)
- ⏳ **R-0 acceptance test** (fresh-laptop grandma-test on 20 reference screenplays)

---

## D.4 Technology Stack (v1.1 reality)

### Backend

| Component | v1.0 | v1.1 |
|---|---|---|
| Runtime | Python 3.11+ | Python 3.12+ |
| Web framework | FastAPI | FastAPI (exists, unused by Electron app) + IPC socket (production path) |
| ORM | SQLAlchemy 2.0 async | SQLAlchemy 2.0 async |
| Database | PostgreSQL 16 | SQLite (dev/single-user) + PostgreSQL supported via DATABASE_URL |
| Task queue | Celery + Redis | asyncio poll loop (services/queue_worker.py) |
| Validation | Pydantic v2 | Pydantic v2 |

### Frontend

| Component | v1.0 | v1.1 |
|---|---|---|
| Shell | Next.js 14 PWA | **Electron** desktop app (cross-platform) |
| UI framework | React 18 | React 18 |
| State | Zustand + React Query | TanStack Query v5 (formerly React Query) |
| Styling | Tailwind + Framer Motion | Tailwind + Framer Motion |
| IPC | n/a (was HTTP) | electron-ipc-socket via `window.electronAPI.backendRequest` |

### AI/ML (v1.1)

| Task | Model |
|---|---|
| Video Generation (local) | Wan 2.2 14B FP8 (T2V + I2V + Animate-BF16 with Lightx2v 4-step LoRA) |
| Video Generation (cloud) | RunPod, Replicate |
| TTS | ElevenLabs, OpenAI |
| Lip-Sync | LatentSync (default), Rhubarb (legacy) |
| LLM (shot breakdown) | Local Qwen 2.5 72B Q6_K via Ollama, fallback to OpenAI/Anthropic |
| Face Embedding | InsightFace `buffalo_l` (ArcFace) |
| Character Reference | Flux Schnell |

---

## D.5 Hard Guardrails (preserved from v1.0)

1. **No hallucination** — Agents cannot invent dialogue, character traits, or plot points not in the screenplay.
2. **No invented pricing** — Cost estimates use actual API pricing, never estimates.
3. **Source-label everything** — Every data point has provenance.
4. **No silent fallbacks** — Per the `feedback_no_silent_fallbacks` engineering memory: any fallback path that produces a partial/empty output the caller can't distinguish from real success is a bug, not a defensive nicety. Widen stderr logs; never trim error messages below 4 KB.
5. **The grandma test is the lodestar** — Every codon must serve the drag-drop-screenplay → wake-up-to-movie journey. If it doesn't trace to that, it goes to R-6 or R-7.

---

## D.6 KPIs by Phase

| Phase | Primary KPI | Secondary KPI |
|---|---|---|
| R-0 | LoC deleted / open ghost-IPC count | Test coverage on changed files |
| R-1 | Grandma-test pass rate (20 screenplays) | First-paint < 200ms |
| R-2 | % shots with real quality scores (no hardcoded 0.85) | Snapshot auto-create rate |
| R-3 | % pipeline actions logged with confidence | Approval gates triggered correctly at < 0.6 |
| R-4 | Lighthouse Performance score (≥90 every page) | Keyboard nav completeness |
| R-5 | p95 IPC latency at 10 concurrent users | Beta tester completion rate |
| R-6 | Adoption rate of differentiation features | Time-to-first-use per feature |
| R-7 | Premium tier conversion / first ActForge bookings | Steven grounding accuracy (no hallucinations) |

---

## D.7 Verification Plan

Every codon ships with:
1. **Unit test** for the change itself
2. **Integration test** that exercises the contract end-to-end (no mocks at the integration boundary)
3. **Acceptance test** documented in the codon ticket
4. **Manual smoke** by Grant when the feature touches user-facing flow

R-0 closes when:
- All 9 session-merged PRs are in main (✅)
- v1.1 plan is canonical document in repo (this PR)
- Subtraction Sprint deletes the styrofoam (pending)
- 20-screenplay grandma-test corpus exists (Grant's task)
- Reference R-0 Playwright smoke test passes (pending — depends on corpus)

---

## Signed

Claude Opus 4.7 (1M context) — acting CTO
Authored 2026-05-14T11:45 UTC

Grant Whitmer (sign-off required): _____________________

Once this document is countersigned, every future PR is measured against v1.1, not v1.0. Plan v1.0 becomes archival.
