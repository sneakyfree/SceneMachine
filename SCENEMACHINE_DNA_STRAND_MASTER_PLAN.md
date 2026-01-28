# SCENEMACHINE DNA STRAND MASTER PLAN
## A+ Blueprint: Screenplay-to-Movie Generation Platform
### Version 1.0 | January 2026

---

# PREAMBLE

> **SceneMachine** is the "Adobe Premiere of generative video" — transforming written screenplays into fully rendered AI-generated movies through an agentic, explainable, and future-proof platform.

**Document Purpose**: This is the complete DNA strand for building SceneMachine to an A+ standard. It synthesizes industry research, competitor analysis, and a buildable master plan designed to make incumbent tools feel **comparatively primitive**.

---

# TABLE OF CONTENTS

- **PART A**: Industry Deep Dive
- **PART B**: Competitor Landscape
- **PART C**: The Upgrade - Agentic Architecture
- **PART D**: DNA Strand Master Plan

---

# PART A — INDUSTRY DEEP DIVE

## A.1 Market Overview

| Metric | Value | Confidence | Source |
|--------|-------|------------|--------|
| AI Video Generation Market (2024) | $534M - $3.86B | High | Grand View Research, Business Research Co. |
| Projected CAGR (2024-2033) | 19.5% - 32.2% | High | Multiple industry reports |
| Generative AI in Movies Market (2024) | ~$481M | High | Dimension Market Research |
| AI-Generated Movie Script Market (2024) | $432M | Medium | Growth Market Reports |
| Text-to-Video Market (2024) | $310M | Medium | Business Research Co. |

### Key Market Drivers

1. **Democratization of Production** - AI enables indie creators to produce content previously requiring $100K+ budgets [High Confidence]
2. **Content Demand Explosion** - Streaming platforms, social media, and marketing require exponentially more video content [High Confidence]
3. **Cost/Time Compression** - AI reduces production timelines from weeks to hours [High Confidence]
4. **Accessibility** - Non-technical users can now create professional-quality video [High Confidence]

---

## A.2 How the Industry Actually Works

### End-to-End Workflow (Traditional Film Production)

```
Script → Pre-Production → Principal Photography → Post-Production → Distribution
  │           │                   │                      │
  │           │                   │                      └── Color, VFX, Sound, Edit
  │           │                   └── 10-100+ days shooting
  │           └── Casting, Location, Storyboard, Breakdown (weeks-months)
  └── Screenplay writing (months)
```

### AI-Accelerated Workflow (Current State)

```
Script → AI Breakdown → AI Storyboard → AI Video Gen → AI Lip-Sync → Assembly
  │           │              │               │              │            │
  │           │              │               │              │            └── Manual editing still required
  │           │              │               │              └── Quality varies widely
  │           │              │               └── 30 sec - 3 min per 5-second clip
  │           │              └── Character consistency is hard
  │           └── Filmustage, Studiovity (partial automation)
  └── Final Draft, Fountain, Celtx
```

### Real Constraints [High Confidence]

| Constraint | Reality |
|------------|---------|
| **Character Consistency** | No tool maintains perfect character likeness across 50+ shots |
| **Screenplay Parsing** | AI struggles with non-standard formatting; Fountain/FDX parsing is inconsistent |
| **Lip-Sync Quality** | Current tools (Wav2Lip) produce "plastic" faces; LatentSync is better but computationally heavy |
| **Scene Coherence** | Video models break physics, produce artifacts, inconsistent lighting |
| **Audio-Video Sync** | Most tools require post-sync; native sync is rare (Sora exception) |
| **Cost at Scale** | A 10-minute short film = 120+ shots = $500-2000+ in API costs |
| **Rendering Time** | A 10-minute film = 8-24+ hours of rendering on consumer hardware |

---

## A.3 Buyer vs. User Reality

| Role | Buyer? | User? | Pain Points |
|------|--------|-------|-------------|
| **Indie Filmmaker** | Yes | Yes | Budget constraints, technical complexity, time |
| **YouTube Creator** | Yes | Yes | Speed to publish, consistency, cost per video |
| **Marketing Agency** | Yes | No | Client revisions, brand consistency, turnaround |
| **Production Studio** | Yes | No | Integration with existing tools, quality control, audit trails |
| **VFX Artist** | No | Yes | Iteration speed, precision control, compositing |
| **Screenwriter** | No | Partial | Visualization of script, pitch materials |

---

## A.4 Top 10 Pain Points

| # | Pain Point | Severity | Evidence |
|---|------------|----------|----------|
| 1 | **Character Inconsistency** | Critical | Users report characters "morphing" between shots; no tool solves this reliably |
| 2 | **Physics Violations** | High | Floating objects, impossible movements, "uncanny valley" humans |
| 3 | **Credit System Exploitation** | High | Runway/Pika credits consumed on failed generations; no refunds |
| 4 | **Lip-Sync Mismatch** | High | Audio drifts from lips; multilingual support weak |
| 5 | **Workflow Fragmentation** | High | Script breakdown → storyboard → video → lip-sync → edit = 5+ different tools |
| 6 | **No Audit Trail** | Medium | Can't reproduce past generations; no version control |
| 7 | **Prompt Engineering Required** | Medium | Novices struggle to get usable output; experts needed |
| 8 | **Long Render Times** | Medium | 2-5 min per 5-sec clip makes iteration painful |
| 9 | **No Explanation of Failures** | Medium | When generation fails, no "why" or "how to fix" |
| 10 | **Copyright Concerns** | Medium | Training data provenance unclear; legal risk |

---

## A.5 Top 10 "Evidence-Heavy" Moments Where Novices Fail

| # | Moment | Why Novices Fail |
|---|--------|------------------|
| 1 | **Screenplay Import** | Format variations (.fountain vs .fdx vs .pdf) cause parsing errors |
| 2 | **Character Setup** | Reference images must be specific; generic prompts = inconsistent characters |
| 3 | **Shot Breakdown** | Novices skip this step; AI can't infer camera angles from prose |
| 4 | **Negative Prompting** | Not knowing to exclude artifacts, blur, distortion |
| 5 | **Voice Selection** | TTS voice profiles ("neutral" vs "expressive") dramatically affect emotion |
| 6 | **Lip-Sync Timing** | Audio must be trimmed precisely; silence padding breaks sync |
| 7 | **Scene Transitions** | Cutting between clips without transitions = jarring amateur result |
| 8 | **Aspect Ratio** | Mixing 16:9 and 9:16 clips breaks assembly |
| 9 | **Audio Normalization** | Dialogue at different volumes across scenes |
| 10 | **Export Settings** | Codec, bitrate, container format mismatches |

---

## A.6 Data Sources & Integration Reality

| Data Source | Automation Level | Notes |
|-------------|------------------|-------|
| **Screenplay Files** | High | .fountain, .fdx, .pdf parseable; edge cases exist |
| **Character Reference Images** | Manual | User must provide or generate |
| **Voice Cloning** | Medium | 10-30 sec audio sample needed |
| **Stock Audio/Music** | Manual | Must license separately |
| **Video Generation APIs** | High | Replicate, Fal, RunPod, ComfyUI APIs available |
| **Lip-Sync Models** | High | LatentSync, Wav2Lip, SadTalker all local |
| **LLM for Parsing** | High | Llama, Claude, GPT-4o all work |

---

## A.7 Compliance & Risk Zones

| Area | Risk Level | Consideration |
|------|------------|---------------|
| **Deepfake Regulations** | High | Many jurisdictions require consent for likeness use |
| **Copyright** | High | AI training data provenance; generated content ownership |
| **Content Moderation** | Medium | Platform must block harmful content generation |
| **Data Privacy** | Medium | User scripts, character images are sensitive |
| **Export Controls** | Low | Some AI models have geographic restrictions |

---

## A.8 Industry Direction (Next 24 Months)

| Trend | Probability | Impact |
|-------|-------------|--------|
| **Native Audio-Video Generation** | High | Sora already does this; others will follow |
| **Multi-Minute Coherent Video** | High | Current 5-10 sec limit will expand to 60+ sec |
| **Character Consistency Solutions** | High | IP-Adapter, face embeddings becoming standard |
| **Real-Time Generation** | Medium | Inference optimization + hardware advances |
| **Agentic Orchestration** | Medium | Multi-model pipelines with autonomous coordination |
| **Enterprise Compliance Tools** | Medium | Audit trails, watermarking, consent management |
| **Open-Source Model Parity** | Medium | CogVideoX, Mochi, Wan challenging closed models |

---

# PART B — COMPETITOR LANDSCAPE

## B.1 Competitor Matrix

### Tier 1: Direct Competitors (AI Video Generation)

| Competitor | Core DNA | Strengths | Weaknesses | Why They Fail | Moats |
|------------|----------|-----------|------------|---------------|-------|
| **Runway ML** | Professional video editing with AI | Intuitive UI, Motion Brush, Director Mode, character consistency | Expensive credits, wasted on failed generations, physics issues | Credit model prioritizes revenue over user success | Brand recognition, enterprise integrations |
| **Pika Labs** | Fast, stylized video clips | Speed (30-90 sec), creative effects, generous free tier | Short clips (3-10 sec), stylized not realistic, character consistency | Optimized for social media, not filmmaking | Community, accessibility |
| **OpenAI Sora** | Cinematic realism | Photorealism, physics accuracy, native audio-video | Limited access, long generation times, high cost, causality issues | Built as AI research demo, not production tool | OpenAI brand, ChatGPT integration |
| **Kling AI** | Budget-friendly realistic video | Affordable, good motion dynamics, lip-sync | Slow processing, inconsistent results, login issues | Chinese market focus, less polished UX | Price point |
| **Luma Dream Machine** | Cinematic motion from images | Natural motion, character consistency, intuitive UI | Short clips, prompt-dependent, physics failures | Image-to-video focus, not end-to-end pipeline | Ease of use |

### Tier 2: Adjacent Competitors (Avatar/Presenter Video)

| Competitor | Core DNA | Strengths | Weaknesses | Why They Fail | Moats |
|------------|----------|-----------|------------|---------------|-------|
| **Synthesia** | Enterprise avatar video | 140+ avatars, 120+ languages, SCORM, enterprise security | Not for creative filmmaking, talking head only | Optimized for training/marketing, not storytelling | Enterprise contracts |
| **HeyGen** | Realistic avatar cloning | 175+ languages, 4K, natural lip-sync, voice cloning | Presenter-focused, no scene generation | No cinematic capability | Localization strength |

### Tier 3: Adjacent Competitors (Pre-Production)

| Competitor | Core DNA | Strengths | Weaknesses | Why They Fail | Moats |
|------------|----------|-----------|------------|---------------|-------|
| **Katalist** | AI storyboard from scripts | Script parsing, character consistency, multiple art styles | Storyboards only, no video generation | Stops at visualization phase | Script import |
| **Filmustage** | Automated script breakdown | Element tagging, scheduling exports | No video generation, no storyboarding | Pre-production only | Industry exports (FDX, Movie Magic) |
| **LTX Studio** | End-to-end AI video creation | Integrated pipeline, character consistency | New, limited track record | Platform quality uncertain | Ambition |

### Tier 4: Self-Hosted/Open-Source

| Competitor | Core DNA | Strengths | Weaknesses | Why They Fail | Moats |
|------------|----------|-----------|------------|---------------|-------|
| **ComfyUI + Wan/Mochi** | Open-source video generation | Free, customizable, local processing | Requires technical expertise, no unified UI | Nodes-based = steep learning curve | Open-source community |
| **Automatic1111 + Extensions** | Open-source image/video | Massive ecosystem, free | Complexity, maintenance burden | Not designed for video workflows | Plugin ecosystem |

---

## B.2 Common User Complaints (Themes)

| Theme | Frequency | Platforms Affected |
|-------|-----------|-------------------|
| **Wasted credits on bad output** | Very High | Runway, Pika |
| **Character morphing between shots** | Very High | All |
| **Physics violations** | High | All |
| **Slow generation** | High | Kling, Sora |
| **No explanation when generation fails** | High | All |
| **Complex or fragmented workflow** | High | ComfyUI, multi-tool pipelines |
| **Expensive at scale** | High | Runway, Sora |
| **Customer service unresponsive** | Medium | Runway, Pika |
| **Lip-sync mismatch** | Medium | All |
| **No audit trail/version control** | Medium | All |

---

## B.3 Competitive Opportunity Matrix

### Weaknesses We Can Turn Into GOAT Superpowers

| Competitor Weakness | SceneMachine Superpower |
|---------------------|------------------------|
| Character inconsistency | **Character Laboratory** - Lock character appearance with face embeddings + IP-Adapter before generation |
| Wasted credits on failed generations | **Preview Before Commit** - Low-res preview + confidence score before full generation |
| Fragmented workflow | **End-to-End Pipeline** - Script → Movie in one platform |
| No explanation of failures | **Multi-View Explainability** - Why it failed + what to fix |
| No audit trail | **Immutable Snapshots** - Every generation versioned, reproducible |
| Prompt engineering required | **TurboTax-Style Intake** - Guided wizard, contradiction detection |
| Physics violations | **Agentic Quality Gate** - AI reviews output, flags issues before human sees |

### Strengths We Must Match or Surpass

| Competitor Strength | SceneMachine Approach |
|--------------------|----------------------|
| Runway's professional UI | Modern glassmorphism PWA with premium UX |
| Pika's speed | Local GPU + cloud burst hybrid |
| Sora's realism | Best-available model routing (Mochi, Wan 2.1, CogVideoX) |
| Synthesia's enterprise features | Audit trails, RBAC, export compliance |
| Katalist's script parsing | LLM-powered parsing with validation UI |

### Feature Wedge (Drives Adoption Fastest)

> **"Screenplay → Movie in One Click"**
> 
> No other platform offers: upload .fountain → AI breakdown → AI storyboard → AI video → AI lip-sync → rendered movie — without leaving the platform.

### Moat Extension (Makes Churn Hard)

> **Character Library + Project History**
> 
> Once users define characters and generate scenes, their investment in the platform compounds. Project history, character embeddings, and voice profiles become sticky assets.

---

# PART C — THE UPGRADE: Agentic + From the Future

## C.1 Design Philosophy

SceneMachine will feel like:

- **Evidence-first + explainable** - Every decision has a rationale the user can inspect
- **Agentic, but safely bounded** - AI makes decisions within guardrails, human approves high-stakes actions
- **Built to get smarter** - Model-agnostic, continuous improvement hooks, evaluation harnesses

---

## C.2 TurboTax-Style Intake DNA

### Screenplay Import Wizard

```yaml
Intake Flow:
  Step 1: Upload File
    - Accepts: .fountain, .fdx, .pdf, .txt
    - Validation: Format detection, encoding check
    - Fallback: "We couldn't parse this automatically. Would you like to paste the text directly?"

  Step 2: Parsing Preview
    - Shows: Extracted title, characters, scene count
    - User confirms or corrects

  Step 3: Character Setup
    - For each character: Name, Description, Voice Profile
    - Optional: Upload reference image OR generate with AI
    - Contradiction Detection: "SARAH is described as 'tall blonde' in Scene 1 but 'short brunette' in Scene 5"

  Step 4: Scene Breakdown
    - AI generates shot list for each scene
    - User can edit: shot description, camera angle, character refs
    - "I'm not sure" path: Flags ambiguous descriptions for human review

  Step 5: Generation Settings
    - Quality: Draft (fast, low-res) / Standard / Premium
    - Compute: Local GPU / Cloud / Auto
    - Cost Estimate: "$X for X shots at X quality"

  Step 6: Confirm & Queue
    - Shows: Total shots, estimated time, estimated cost
    - User approves or adjusts
```

---

## C.3 Blockers / Unlockers Engine

### Prioritized Fix List

```
CRITICAL (Block generation):
  ├── Character "DETECTIVE MORSE" has no reference image
  │   └── Fix: Upload image OR generate with AI (Quick Win, 2 min)
  └── Scene 7 references non-existent character "VICTIM"
      └── Fix: Add character OR remove from scene (Quick Win, 1 min)

HIGH (Quality risk):
  ├── 3 shots have low confidence (<0.6) prompts
  │   └── Fix: Review and refine prompts (30 min)
  └── Voice profile for "SARAH" not selected
      └── Fix: Choose from library OR clone custom voice (5 min)

MEDIUM (Polish needed):
  └── Transition style not specified between scenes
      └── Fix: Set global transition OR per-scene (Quick Win, 2 min)
```

---

## C.4 Multi-View Explainability

### 4-Layer Explanation System

| Layer | Audience | Content |
|-------|----------|---------|
| **Client View** | End user, non-technical | Plain language summary, visual preview, estimated delivery |
| **Operator View** | Content creator, filmmaker | Shot-by-shot breakdown, generation settings, cost/time tracking |
| **Technical View** | Developer, VFX artist | Model parameters, inference logs, error traces |
| **Audit View** | Compliance, legal | Immutable snapshots, version history, consent records |

---

## C.5 Agentic Crew Design (Bounded Autonomy)

### Crew Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          SCENEMACHINE CREW                                  │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      ORCHESTRATOR (Director Agent)                   │   │
│  │  • Routes tasks to specialist agents                                 │   │
│  │  • Maintains project state                                           │   │
│  │  • Enforces guardrails                                               │   │
│  │  • Escalates to human for approval gates                             │   │
│  └───────────────────────────┬─────────────────────────────────────────┘   │
│                              │                                              │
│      ┌───────────────────────┼───────────────────────────────────────┐     │
│      │                       │                                        │     │
│  ┌───┴────────┐  ┌──────────┴──────────┐  ┌────────────────────────┴──┐   │
│  │   PARSER   │  │     CHARACTER       │  │      GENERATOR            │   │
│  │   Agent    │  │      Agent          │  │        Agent              │   │
│  │            │  │                     │  │                           │   │
│  │ • Script   │  │ • Reference gen     │  │ • Video generation        │   │
│  │   parsing  │  │ • Face embedding    │  │ • TTS audio               │   │
│  │ • Shot list│  │ • Voice cloning     │  │ • Lip-sync                │   │
│  │ • Prompts  │  │ • Consistency check │  │ • Quality gate            │   │
│  └────────────┘  └─────────────────────┘  └───────────────────────────┘   │
│                                                                             │
│  ┌────────────────┐  ┌────────────────────┐  ┌──────────────────────┐      │
│  │   ASSEMBLER    │  │      REVIEWER      │  │       EXPORT         │      │
│  │     Agent      │  │       Agent        │  │        Agent         │      │
│  │                │  │                    │  │                      │      │
│  │ • Clip concat  │  │ • Quality scoring  │  │ • Format conversion  │      │
│  │ • Transitions  │  │ • Physics check    │  │ • Compression        │      │
│  │ • Audio mix    │  │ • Artifact detect  │  │ • Watermarking       │      │
│  │ • Normalization│  │ • Human escalation │  │ • Distribution       │      │
│  └────────────────┘  └────────────────────┘  └──────────────────────┘      │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

### Agent Boundaries

| Agent | Can Do Autonomously | Requires Human Approval |
|-------|---------------------|------------------------|
| Parser | Parse scripts, generate prompts, detect contradictions | Resolve ambiguous character descriptions |
| Character | Generate reference images, extract embeddings | Use likeness of real people |
| Generator | Queue generations, retry on failure, route to cloud | Spend >$10, generate sensitive content |
| Assembler | Concatenate, apply transitions, normalize audio | Final export |
| Reviewer | Flag quality issues, suggest fixes | Mark "approved for delivery" |
| Export | Compress, watermark, prepare distribution | Publish to external platform |

---

# PART D — DNA STRAND MASTER PLAN

## D.1 End-State Vision

> **The 30-Second Pitch**: Upload a screenplay. Click generate. Watch your movie render. Download a professional-quality film with consistent characters, synchronized dialogue, and cinematic polish — all without leaving SceneMachine.

### Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Script-to-First-Frame | <60 seconds | Automated benchmark |
| Character Consistency | >90% similarity | CLIP embedding distance |
| Lip-Sync Accuracy | <80ms drift | Audio-visual sync |
| Full Pipeline Success | >95% | Scripts completing without intervention |
| User Satisfaction | >4.5/5 | Post-generation survey |
| Cost Efficiency | <$0.10/sec final video | Cost tracking |

---

## D.2 Scope Envelope

### In Scope

- Screenplay import (.fountain, .fdx, .pdf, .txt)
- AI-powered script breakdown and shot list generation
- Character Laboratory with face embedding consistency
- Multi-provider video generation (local + cloud)
- TTS dialogue with voice profiles and emotion
- Lip-sync for dialogue shots
- Automated assembly with transitions and audio mixing
- Multi-view explainability dashboard
- Audit-grade reproducibility and version control
- PWA frontend with premium UX

### Explicit Non-Goals (v1.0)

- Real-time video streaming
- Collaborative multi-user editing
- Mobile native apps (PWA only)
- Integration with external NLEs (Premiere, DaVinci)
- Music composition or scoring
- 3D asset generation
- VR/AR output
- Live streaming

---

## D.3 Phased Rollout Plan

### Phase 0: Foundation (Week 1-2)

| Task | Description | Acceptance Test |
|------|-------------|-----------------|
| 0.1 | Create monorepo structure | `npm run dev` starts frontend |
| 0.2 | Setup FastAPI backend | `/health` returns 200 |
| 0.3 | PostgreSQL + SQLAlchemy 2.0 async | Migrations run successfully |
| 0.4 | Redis + Celery | Background task executes |
| 0.5 | Core database models | All models migrate without error |
| 0.6 | Authentication (JWT) | Login/logout works |
| 0.7 | Basic API structure | CRUD for projects works |

---

### Phase 1: Screenplay Parser (Week 3-4)

| Task | Description | Acceptance Test |
|------|-------------|-----------------|
| 1.1 | PDF text extraction | Extract text from sample screenplay PDF |
| 1.2 | Fountain parser | Parse sample Fountain file correctly |
| 1.3 | FDX parser | Parse Final Draft file correctly |
| 1.4 | LLM prompt engineering | Generate valid shot list from script |
| 1.5 | Contradiction detection | Detect conflicting character descriptions |
| 1.6 | Validation UI | User can fix parsing errors |

---

### Phase 2: Character Laboratory (Week 5-6)

| Task | Description | Acceptance Test |
|------|-------------|-----------------|
| 2.1 | Character definition UI | Create character with description |
| 2.2 | Reference image upload | Upload and display reference |
| 2.3 | AI reference generation | Generate character portrait from text |
| 2.4 | Face embedding extraction | Extract InsightFace embedding |
| 2.5 | Voice profile selection | Select from Kokoro voices |
| 2.6 | Voice cloning | Clone voice from 10-30 sec sample |
| 2.7 | Character consistency check | Flag characters that look too similar |

---

### Phase 3: Generation Engine (Week 7-10)

| Task | Description | Acceptance Test |
|------|-------------|-----------------|
| 3.1 | Video generation service | Generate 5-sec clip |
| 3.2 | Wan 2.1 local integration | Run on RTX 5090 |
| 3.3 | Cloud provider integration | Run on Lambda Labs |
| 3.4 | IP-Adapter face injection | Character consistency maintained |
| 3.5 | TTS audio generation | Generate dialogue audio |
| 3.6 | Lip-sync service | Lips match dialogue |
| 3.7 | Quality gate | Flag physics violations |
| 3.8 | Retry and fallback logic | Auto-retry with modified prompt |
| 3.9 | Cost tracking | Accurate cost per shot |

---

### Phase 4: Assembly & Export (Week 11-12)

| Task | Description | Acceptance Test |
|------|-------------|-----------------|
| 4.1 | FFmpeg wrapper | Combine clips |
| 4.2 | Transition engine | Apply fade/dissolve |
| 4.3 | Audio mixing | Combine dialogue + ambient |
| 4.4 | Audio normalization | Consistent levels |
| 4.5 | Final render | Export MP4/MOV |
| 4.6 | Thumbnail generation | Extract frame |
| 4.7 | Export presets | YouTube preset works |

---

### Phase 5: Explainability Dashboard (Week 13-14)

| Task | Description | Acceptance Test |
|------|-------------|-----------------|
| 5.1 | Client view dashboard | Non-technical user understands |
| 5.2 | Operator view | Creator can troubleshoot |
| 5.3 | Technical view | Developer can debug |
| 5.4 | Audit view | Compliance officer can audit |
| 5.5 | Snapshot system | Snapshots are reproducible |
| 5.6 | Delta reports | Changes are visible |

---

### Phase 6: Agentic Crew (Week 15-16)

| Task | Description | Acceptance Test |
|------|-------------|-----------------|
| 6.1 | Orchestrator agent | End-to-end works |
| 6.2 | Parser agent | Auto-parses |
| 6.3 | Character agent | Auto-generates references |
| 6.4 | Generator agent | Auto-queues |
| 6.5 | Assembler agent | Auto-assembles |
| 6.6 | Reviewer agent | Flags issues |
| 6.7 | Human approval gates | High-stakes require approval |
| 6.8 | Action logging | Every action logged |

---

### Phase 7: PWA Frontend (Week 17-20)

| Task | Description | Acceptance Test |
|------|-------------|-----------------|
| 7.1 | Design system | Components render correctly |
| 7.2 | Screenplay import wizard | Upload and validate screenplay |
| 7.3 | Character Laboratory UI | Create and edit characters |
| 7.4 | Shot breakdown editor | View and edit shots |
| 7.5 | Generation queue | Monitor generation progress |
| 7.6 | Assembly preview | Preview assembled movie |
| 7.7 | Export UI | Download final movie |
| 7.8 | Explainability dashboard | View all 4 layers |
| 7.9 | Settings and preferences | User can configure |
| 7.10 | Responsive/PWA | Works on tablet, offline capable |

---

### Phase 8: Polish & Testing (Week 21-24)

| Task | Description | Acceptance Test |
|------|-------------|-----------------|
| 8.1 | E2E test suite | All critical paths covered |
| 8.2 | Load testing | Handles 10 concurrent users |
| 8.3 | Security audit | No critical vulnerabilities |
| 8.4 | Performance optimization | Generation queue <2 min overhead |
| 8.5 | Documentation | User guide complete |
| 8.6 | Deployment scripts | Docker Compose deploys |
| 8.7 | Monitoring and alerting | Errors trigger alerts |
| 8.8 | Beta user testing | 5+ testers complete full workflow |

---

## D.4 Technology Stack Summary

### Backend

| Component | Technology |
|-----------|-----------|
| Runtime | Python 3.11+ |
| Web Framework | FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 16 |
| Task Queue | Celery + Redis |
| Validation | Pydantic v2 |

### Frontend

| Component | Technology |
|-----------|-----------|
| Framework | Next.js 14 / React 18 |
| State | Zustand + React Query |
| Styling | Tailwind CSS + Framer Motion |
| PWA | next-pwa |

### AI/ML

| Task | Model |
|------|-------|
| Video Generation | Wan 2.1 (local/cloud) |
| TTS | Kokoro 82M |
| Lip-Sync | LatentSync |
| LLM | Llama 3.3 70B (Q4) |
| Face Embedding | InsightFace ArcFace |
| Character Reference | Flux Schnell |

---

## D.5 Hard Guardrails (Always Enforced)

1. **No hallucination** - Agents cannot invent dialogue, character traits, or plot points not in the screenplay
2. **No invented pricing** - Cost estimates use actual API pricing, never estimates
3. **Source-label everything** - Every data point has provenance
4. **Uncertainty triggers REFER** - Confidence <0.6 escalates to human
5. **Explicit non-goals** - Features marked out-of-scope are rejected
6. **Immutable audit trail** - Logs cannot be deleted or modified
7. **Consent for likeness** - Real person likeness requires explicit user confirmation

---

## D.6 KPIs by Phase

| Phase | KPI | Target |
|-------|-----|--------|
| Phase 1 | Parse success rate | >90% |
| Phase 2 | Character embedding variance | <0.3 |
| Phase 3 | Generation success rate | >85% |
| Phase 4 | Assembly success rate | >95% |
| Phase 5 | User understands explanation | >80% survey |
| Phase 6 | Autonomous completion rate | >75% |
| Phase 7 | Task completion rate | >90% |
| Phase 8 | Beta user satisfaction | >4.5/5 |

---

## D.7 Verification Plan

### Automated Tests

```bash
# Backend tests
cd packages/core && pytest

# Frontend tests
cd apps/desktop && npm run test

# E2E tests
npm run test:e2e
```

### Manual Verification

1. **Screenplay Import Test**: Upload .fountain → verify parsed scenes match expected
2. **Character Consistency Test**: Generate 3 shots with same character → visually consistent
3. **Full Pipeline Test**: Upload 5-scene screenplay → final movie plays correctly

---

**END OF DOCUMENT**

*This DNA Strand Master Plan is a living document. Update after each phase completion.*
