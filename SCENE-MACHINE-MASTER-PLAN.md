# SCENE MACHINE
## Ultimate Master Development Plan & Architecture Blueprint
### Version 2.0 | December 30, 2025

---

# PREAMBLE: HOW TO USE THIS DOCUMENT

## Purpose
This is the **complete DNA strand** for building **Scene Machine** - a self-hosted, hybrid-cloud platform that transforms written screenplays into fully rendered AI-generated movies. This document is designed to be used in VS Code with AI coding assistants (Claude Code, Cline, etc.) that have **NO prior context** about this project.

## Critical Usage Rules

1. **PHASE-BY-PHASE EXECUTION**: Build ONE phase at a time. Do not skip ahead. Do not combine phases. Complete Phase 0, verify it works, then move to Phase 1, etc.

2. **QUALITY OVER SPEED**: Every component should work correctly before moving forward. Test each piece. Fix bugs immediately. Do not accumulate technical debt.

3. **GAP ANALYSIS**: After completing each phase, use this document to perform a gap analysis:
   - Check off completed tasks
   - Note any deviations from the plan
   - Document any blockers or adjustments needed

4. **CONTEXT REMINDERS**: When starting a new coding session, remind your AI assistant:
   - "This is Scene Machine"
   - "We are currently on Phase [X]"
   - "The goal of this phase is [Y]"
   - "Reference the master plan at [path]"

5. **COMMIT FREQUENTLY**: After each sub-task completion, commit to git with descriptive messages.

---

# TABLE OF CONTENTS

- PART I: VISION & NORTH STAR
- PART II: SYSTEM ARCHITECTURE  
- PART III: TECHNOLOGY STACK SPECIFICATIONS
- PART IV: DETAILED COMPONENT SPECIFICATIONS
- PART V: FRONTEND SPECIFICATIONS
- PART VI: DEVELOPMENT PHASES (GRANULAR)
  - Phase 0: Project Scaffolding
  - Phase 1: Script Parser
  - Phase 2: Audio Generation
  - Phase 3: Video Generation
  - Phase 4: Lip Sync
  - Phase 5: Orchestrator
  - Phase 6: Assembly
  - Phase 7: Frontend
  - Phase 8: Cloud Integration
  - Phase 9: Polish & Testing
- PART VII: GAP ANALYSIS TEMPLATES
- PART VIII: RISK REGISTER
- PART IX: TROUBLESHOOTING GUIDE
- APPENDICES

---

# PART I: VISION & NORTH STAR

## 1.1 The End State Vision

**Product Name:** Scene Machine™
**Domain:** SceneMachine.ai

**What we are building:** A self-hosted, hybrid-cloud platform that transforms written screenplays into fully rendered movies with synchronized dialogue, consistent characters, and professional-quality output—all through a dead-simple interface that a non-technical person could operate.

**The Core Promise:** Upload a script → Click "Generate Movie" → Download a finished film.

**Key Differentiators:**
- **No wrapper APIs**: We own the entire pipeline, not dependent on HeyGen, Runway, or Synthesia
- **Hybrid compute**: Seamless toggle between local GPU (RTX 5090) and cloud bursting (Lambda Labs H100s)
- **Open source stack**: Every model is open, forkable, and under your control
- **Cost efficiency**: Local processing for development/small jobs; cloud only when you need raw power

**Owner:** Grant Whitmer (Independent Product)

## 1.2 Success Metrics

| Metric | Target | How We Measure |
|--------|--------|----------------|
| Script-to-First-Frame | < 60 seconds | Time from upload to first generated frame |
| Character Consistency | > 85% similarity | CLIP embedding distance across scenes |
| Lip Sync Accuracy | < 100ms drift | Audio-visual sync measurement |
| Full Pipeline Success Rate | > 95% | Scripts that complete without manual intervention |
| Local Generation Speed | 2-3 min/scene | 5-second clips on RTX 5090 |
| Cloud Generation Speed | 30-45 sec/scene | 5-second clips on H100 |

---

# PART II: SYSTEM ARCHITECTURE

## 2.1 High-Level Architecture Diagram

```
                                    ┌────────────────────────┐
                                    │   FRONTEND (Nuxt)      │
                                    │   SceneMachine.ai UI   │
                                    │   Progress Dashboard   │
                                    └───────────┬────────────┘
                                                │ REST/WebSocket
                                                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      BACKEND (Python/FastAPI)                            │
├──────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐   ┌──────────────┐   ┌─────────────┐   ┌─────────────┐  │
│  │   INTAKE    │──▶│   PARSER     │──▶│ ORCHESTRATOR│──▶│  ASSEMBLER  │  │
│  │   Module    │   │   Module     │   │   Module    │   │   Module    │  │
│  └─────────────┘   └──────────────┘   └──────────────┘  └─────────────┘  │
│        │                  │                  │                  │        │
│        ▼                  ▼                  ▼                  ▼        │
│  • File upload     • PDF extraction   • Job queue        • Stitch clips │
│  • Validation      • Scene parsing    • Local/Cloud      • Add audio    │
│  • Format detect   • Prompt gen       • Progress track   • Final render │
└──────────────────────────────────────────────────────────────────────────┘
                          ┌─────────────────────┴─────────────────────┐
                          ▼                                           ▼
              ┌───────────────────────┐                 ┌───────────────────────┐
              │     LOCAL COMPUTE     │                 │     CLOUD COMPUTE     │
              │      (Your 5090)      │                 │   (Lambda/RunPod)     │
              ├───────────────────────┤                 ├───────────────────────┤
              │ • Wan 2.1 (Quantized) │                 │ • Mochi 1 (Full)      │
              │ • Kokoro TTS          │                 │ • Wan 2.1 (14B Full)  │
              │ • LatentSync          │                 │                       │
              │ • Llama 3.3 70B (Q4)  │                 │                       │
              └───────────────────────┘                 └───────────────────────┘
```

## 2.2 Pipeline Flow

**Stage 1: INTAKE** → Validate & store uploaded file
**Stage 2: PARSER** → Extract text, identify scenes, generate JSON shot list via LLM
**Stage 3: CHARACTER SETUP** → Generate reference images, extract face embeddings
**Stage 4: GENERATION LOOP** → For each shot: generate video, generate audio if dialogue, lip sync if needed
**Stage 5: ASSEMBLY** → Concatenate clips, mix audio, apply transitions, normalize, render final

## 2.3 Directory Structure

```
/scene-machine/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entry point
│   │   ├── config.py               # Environment configuration
│   │   ├── database.py             # SQLAlchemy setup
│   │   ├── models/                 # Database models
│   │   ├── routers/                # API endpoints
│   │   ├── services/
│   │   │   ├── parser/             # Screenplay parsing
│   │   │   ├── video/              # Video generation
│   │   │   ├── audio/              # TTS audio
│   │   │   ├── lipsync/            # Lip synchronization
│   │   │   ├── assembly/           # Final movie assembly
│   │   │   └── orchestrator/       # Pipeline coordination
│   │   └── workers/
│   │       ├── celery_app.py       # Celery configuration
│   │       ├── tasks/              # Background tasks
│   │       └── cloud/              # Cloud integration
│   └── tests/
├── frontend/
│   ├── pages/
│   ├── components/
│   └── composables/
├── jobs/                           # Runtime job storage (gitignored)
├── models/                         # Cached model weights (gitignored)
├── skypilot/                       # Cloud task configs
├── docker-compose.yml
├── .env.example
├── CLAUDE.md                       # AI assistant context file
└── README.md
```

---

# PART III: TECHNOLOGY STACK

## 3.1 Backend Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Runtime | Python | 3.11+ |
| Web Framework | FastAPI | 0.109+ |
| Task Queue | Celery | 5.3+ |
| Message Broker | Redis | 7.0+ |
| Database | PostgreSQL | 16+ |
| ORM | SQLAlchemy | 2.0+ |

## 3.2 Frontend Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | Nuxt 3 | 3.9+ |
| UI Framework | Vue 3 | 3.4+ |
| Styling | Tailwind CSS | 3.4+ |
| State | Pinia | 2.1+ |

## 3.3 AI/ML Stack

| Task | Model | VRAM Required | Speed |
|------|-------|---------------|-------|
| Script Parsing | Llama 3.3 70B (Q4) | ~40GB | 10-30 sec |
| Video Gen (Local) | Wan 2.1 1.3B | ~16GB | 2-3 min |
| Video Gen (Cloud) | Mochi 1 or Wan 2.1 14B | ~80GB | 30-45 sec |
| TTS Voice | Kokoro 82M | ~2GB | Real-time |
| Lip Sync | LatentSync | ~8GB | 30 sec |
| Character Ref | Flux Schnell | ~16GB | 5 sec |
| Face Embedding | InsightFace (ArcFace) | ~2GB | Instant |

---

# PART VI: DEVELOPMENT PHASES (GRANULAR)

---

## PHASE 0: PROJECT SCAFFOLDING

**Duration:** 1-2 hours
**Goal:** Set up complete project structure before writing any application code

### Task 0.1: Create Project Directory
```bash
mkdir scene-machine && cd scene-machine && git init
```
**Verification:** Directory exists, git initialized

### Task 0.2: Create .gitignore
```bash
cat > .gitignore << 'EOF'
__pycache__/
*.py[cod]
.env
.venv
venv/
node_modules/
.nuxt/
.output/
dist/
jobs/
models/
*.mp4
*.wav
*.log
.DS_Store
EOF
```

### Task 0.3: Create Backend Directory Structure
```bash
mkdir -p backend/app/{models,routers,services/{parser,video,audio,lipsync,assembly,orchestrator},workers/tasks,workers/cloud}
mkdir -p backend/tests backend/alembic/versions
touch backend/app/__init__.py
touch backend/app/models/__init__.py
touch backend/app/routers/__init__.py
touch backend/app/services/__init__.py
touch backend/app/workers/__init__.py
touch backend/tests/__init__.py
```

### Task 0.4: Create pyproject.toml
```toml
[project]
name = "scene-machine"
version = "0.1.0"
description = "Scene Machine - Transform screenplays into AI-generated movies"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "python-multipart>=0.0.6",
    "celery>=5.3.0",
    "redis>=5.0.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.13.0",
    "psycopg2-binary>=2.9.9",
    "pdfplumber>=0.11.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
]

[project.optional-dependencies]
ml = [
    "torch>=2.1.0",
    "transformers>=4.36.0",
    "diffusers>=0.25.0",
    "accelerate>=0.25.0",
    "bitsandbytes>=0.41.0",
    "insightface>=0.7.3",
]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.23.0",
]
```

### Task 0.5: Create .env.example
```bash
cat > .env.example << 'EOF'
DATABASE_URL=postgresql://user:password@localhost:5432/scene_machine
REDIS_URL=redis://localhost:6379/0
JOBS_PATH=/path/to/jobs
MODELS_PATH=/path/to/models
ENABLE_CLOUD=false
MAX_FILE_SIZE_MB=50
API_PORT=8000
EOF
cp .env.example .env
```

### Task 0.6: Create docker-compose.yml
```yaml
version: '3.8'
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: scene_machine
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

### Task 0.7: Create Backend Config Module
```python
# backend/app/config.py
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    database_url: str = "postgresql://user:password@localhost:5432/scene_machine"
    redis_url: str = "redis://localhost:6379/0"
    jobs_path: Path = Path("/tmp/jobs")
    models_path: Path = Path("/tmp/models")
    max_file_size_mb: int = 50
    enable_cloud: bool = False
    api_port: int = 8000
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### Task 0.8: Create FastAPI Main Entry Point
```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Scene Machine API",
    description="Transform screenplays into AI-generated movies",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"name": "Scene Machine", "status": "online"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
```
**Verification:** `uvicorn backend.app.main:app --reload` starts server

### Task 0.9: Create Frontend Structure
```bash
npx nuxi@latest init frontend
cd frontend && npm install
npm install -D @nuxtjs/tailwindcss
```

### Task 0.10: Create CLAUDE.md Context File
```markdown
# CLAUDE.md - AI Assistant Context

## Project: Scene Machine
Transform screenplays into AI-generated movies.
Website: SceneMachine.ai

## Current Phase: Phase 0 (Scaffolding)

## Architecture
- Backend: Python 3.11 / FastAPI / Celery
- Frontend: Nuxt 3 / Vue 3 / Tailwind CSS
- AI: Wan 2.1, Kokoro TTS, LatentSync, Llama 3.3 70B

## Commands
- Start backend: uvicorn backend.app.main:app --reload
- Start frontend: cd frontend && npm run dev
- Start services: docker compose up -d
```

### Task 0.11: Initial Git Commit
```bash
git add .
git commit -m "Phase 0: Scene Machine project scaffolding complete"
```

### Phase 0 Completion Checklist
- [ ] Task 0.1-0.11 all complete
- [ ] `docker compose up -d` starts Postgres and Redis
- [ ] Backend starts without errors
- [ ] Frontend dev server runs
- [ ] Git repository initialized with first commit

**Phase 0 Complete When:** All services start without errors

---

## PHASE 1: SCRIPT PARSER

**Duration:** 1 week
**Goal:** Convert screenplay files into structured JSON shot lists
**Dependencies:** Phase 0 complete

### Task 1.1: Create Database Models
```python
# backend/app/models/job.py
from sqlalchemy import Column, String, Integer, Float, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from backend.app.database import Base

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(String(20), default="uploaded")
    original_filename = Column(String(255), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    scene_count = Column(Integer)
    shot_count = Column(Integer)
    progress_percent = Column(Float, default=0)
    current_step = Column(String(100))
    error_message = Column(Text)
    output_url = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### Task 1.2: Create Database Connection
```python
# backend/app/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.app.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Task 1.3: Create Alembic Migration
```bash
cd backend
alembic init alembic
# Update alembic.ini and env.py
alembic revision --autogenerate -m "Create jobs table"
alembic upgrade head
```

### Task 1.4: Create PDF Parser
```python
# backend/app/services/parser/pdf_parser.py
import pdfplumber

class PDFParser:
    def extract_text(self, pdf_path: str) -> str:
        text_content = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_content.append(text)
        return "\n\n".join(text_content)
    
    def get_page_count(self, pdf_path: str) -> int:
        with pdfplumber.open(pdf_path) as pdf:
            return len(pdf.pages)
```

### Task 1.5: Create LLM Processor
```python
# backend/app/services/parser/llm_processor.py
import json
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

PARSE_PROMPT = """You are a screenplay analysis AI. Convert the following screenplay into a structured JSON shot list.

OUTPUT FORMAT (JSON only):
{
  "title": "TITLE",
  "characters": [{"name": "NAME", "description": "desc", "voice_profile": "profile"}],
  "scenes": [{
    "scene_id": "001",
    "slug": "INT. LOCATION - TIME",
    "shots": [{
      "shot_id": "001-001",
      "visual_prompt": "detailed description for video generation",
      "camera": "wide/medium/close-up",
      "dialogue": null or {"character": "NAME", "text": "text", "emotion": "emotion"},
      "character_refs": []
    }]
  }]
}

SCREENPLAY:
{screenplay_text}

JSON:
"""

class LLMProcessor:
    def __init__(self, model_path: str):
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path, device_map="auto", torch_dtype=torch.float16, load_in_4bit=True
        )
    
    def parse(self, screenplay_text: str) -> dict:
        prompt = PARSE_PROMPT.format(screenplay_text=screenplay_text[:50000])
        inputs = self.tokenizer(prompt, return_tensors="pt").to("cuda")
        outputs = self.model.generate(**inputs, max_new_tokens=16384, temperature=0.1)
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        json_start = response.rfind('{')
        json_end = response.rfind('}') + 1
        return json.loads(response[json_start:json_end])
```

### Task 1.6: Create Upload Router
```python
# backend/app/routers/upload.py
from fastapi import APIRouter, UploadFile, HTTPException, Depends
from sqlalchemy.orm import Session
from pathlib import Path
import uuid
from backend.app.database import get_db
from backend.app.models.job import Job
from backend.app.config import settings

router = APIRouter(prefix="/api/v1", tags=["upload"])
SUPPORTED_FORMATS = {'.pdf', '.fdx', '.fountain', '.txt'}

@router.post("/upload")
async def upload_script(file: UploadFile, db: Session = Depends(get_db)):
    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_FORMATS:
        raise HTTPException(400, f"Unsupported format: {ext}")
    
    content = await file.read()
    if len(content) > settings.max_file_size_mb * 1024 * 1024:
        raise HTTPException(413, "File too large")
    
    job_id = uuid.uuid4()
    job_path = settings.jobs_path / str(job_id)
    job_path.mkdir(parents=True, exist_ok=True)
    
    for subdir in ['input', 'parsed', 'characters', 'clips', 'audio', 'output']:
        (job_path / subdir).mkdir(exist_ok=True)
    
    input_path = job_path / "input" / file.filename
    input_path.write_bytes(content)
    
    job = Job(id=job_id, status="uploaded", original_filename=file.filename, file_size_bytes=len(content))
    db.add(job)
    db.commit()
    
    # Queue parsing task (Task 1.7)
    
    return {"job_id": str(job_id), "status": "queued", "message": f"Script '{file.filename}' uploaded"}
```

### Task 1.7: Create Celery Configuration
```python
# backend/app/workers/celery_app.py
from celery import Celery
from backend.app.config import settings

celery_app = Celery("scene_machine", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(task_serializer='json', result_serializer='json', timezone='UTC')
```

### Phase 1 Completion Checklist
- [ ] Database models created and migrated
- [ ] PDF parser extracts text correctly
- [ ] LLM processor generates valid JSON shot lists
- [ ] Upload endpoint stores files and creates job records
- [ ] Celery task processes uploaded scripts
- [ ] Tests passing

**Phase 1 Complete When:** Upload a PDF → JSON shot list created in /jobs/{id}/parsed/

---

## PHASE 2: AUDIO GENERATION

**Duration:** 3-4 days
**Goal:** Generate dialogue audio from shot list
**Dependencies:** Phase 1 complete

### Key Tasks
1. Install Kokoro TTS model
2. Create TTSService class with voice profiles and emotion modifiers
3. Create Celery task for audio generation
4. Create batch processor for all dialogue shots

### TTSService Structure
```python
# backend/app/services/audio/tts.py
class TTSService:
    VOICE_PROFILES = {
        "male_deep": {"speaker": 0, "pitch": -2},
        "male_normal": {"speaker": 1, "pitch": 0},
        "female_soft": {"speaker": 2, "pitch": 1},
        "female_normal": {"speaker": 3, "pitch": 0},
    }
    
    EMOTION_MODIFIERS = {
        "neutral": {"speed": 1.0, "pitch": 0},
        "angry": {"speed": 1.1, "pitch": 2},
        "sad": {"speed": 0.9, "pitch": -1},
        "excited": {"speed": 1.2, "pitch": 1},
    }
    
    def generate(self, text, output_path, voice_profile, emotion):
        # Generate WAV file using Kokoro
        pass
```

**Phase 2 Complete When:** All dialogue shots have WAV files in /jobs/{id}/audio/

---

## PHASE 3: VIDEO GENERATION

**Duration:** 2 weeks
**Goal:** Generate video clips from shot prompts with character consistency
**Dependencies:** Phase 2 complete

### Key Tasks
1. Install Wan 2.1 model (1.3B for local, 14B for cloud)
2. Install InsightFace for face embeddings
3. Install Flux Schnell for character reference generation
4. Create VideoGenerator class
5. Create FaceEmbedder class
6. Create CharacterReferenceGenerator class
7. Create IP-Adapter integration for consistency
8. Create Celery task for video generation
9. Create batch processor for all shots

### VideoGenerator Structure
```python
# backend/app/services/video/generator.py
class VideoGenerator:
    def generate(self, prompt, output_path, negative_prompt="blurry, low quality",
                 num_frames=120, height=480, width=854, num_inference_steps=50):
        # Load Wan 2.1, generate video, export
        pass
```

### Character Consistency Flow
1. For each character, generate reference portrait with Flux Schnell
2. Extract face embedding with InsightFace ArcFace
3. Save embedding as .npy file
4. For shots containing character, inject embedding via IP-Adapter
5. Generate video with character consistency

**Phase 3 Complete When:** All shots have video files in /jobs/{id}/clips/

---

## PHASE 4: LIP SYNC

**Duration:** 3-4 days
**Goal:** Synchronize mouth movements to dialogue audio
**Dependencies:** Phases 2 and 3 complete

### Key Tasks
1. Install LatentSync model
2. Create LipSyncService class
3. Create Celery task for lip sync
4. Create batch processor for dialogue shots

### LipSyncService Structure
```python
# backend/app/services/lipsync/service.py
class LipSyncService:
    def sync(self, video_path, audio_path, output_path):
        # Load LatentSync, detect faces, sync lips, save output
        pass
```

**Phase 4 Complete When:** All dialogue shots have _synced.mp4 files

---

## PHASE 5: ORCHESTRATOR

**Duration:** 4-5 days
**Goal:** Coordinate the full pipeline from upload to completion
**Dependencies:** Phases 1-4 complete

### Key Tasks
1. Create JobManager for state transitions
2. Create ComputeRouter for local/cloud decisions
3. Create PipelineOrchestrator to run full pipeline
4. Create WebSocket endpoint for progress updates
5. Create Jobs API endpoints

### Job States
```
uploaded -> parsing -> parsed -> character_setup -> generating -> lip_syncing -> assembling -> complete
                 |         |           |              |               |             |
                 v         v           v              v               v             v
               failed    failed     failed         failed          failed        failed
```

### ComputeRouter Logic
```python
def decide(shot_count, user_preference, local_queue_depth):
    if user_preference == "local":
        return ComputeDecision(mode="local", cost=0)
    if user_preference == "cloud":
        return ComputeDecision(mode="cloud", cost=shot_count * 0.15)
    # Auto mode
    if local_queue_depth > 5 or shot_count > 50:
        return ComputeDecision(mode="cloud", cost=shot_count * 0.15)
    return ComputeDecision(mode="local", cost=0)
```

**Phase 5 Complete When:** Full pipeline runs from upload through generation

---

## PHASE 6: ASSEMBLY

**Duration:** 3-4 days
**Goal:** Stitch clips into final movie with transitions and audio
**Dependencies:** Phase 5 complete

### Key Tasks
1. Create FFmpegWrapper for video operations
2. Create VideoStitcher service
3. Create assembly Celery task
4. Create static file serving for outputs

### FFmpeg Operations
```python
class FFmpegWrapper:
    @staticmethod
    def concat_videos(input_files, output_path):
        # ffmpeg -f concat -safe 0 -i concat.txt -c copy output.mp4
        pass
    
    @staticmethod
    def add_audio_track(video_path, audio_path, output_path):
        # ffmpeg -i video -i audio -c:v copy -c:a aac output
        pass
    
    @staticmethod
    def normalize_audio(input_path, output_path, target_lufs=-14.0):
        # ffmpeg -af loudnorm=I=-14:TP=-1.5:LRA=11
        pass
    
    @staticmethod
    def apply_transition(clip1, clip2, output_path, transition="fade", duration=0.5):
        # xfade filter for transitions between scenes
        pass
```

**Phase 6 Complete When:** final_movie.mp4 created and downloadable

---

## PHASE 7: FRONTEND

**Duration:** 1 week
**Goal:** Build the Scene Machine user interface
**Dependencies:** Phase 6 complete (backend fully functional)

### Key Tasks
1. Setup Tailwind CSS in Nuxt
2. Create layout component with Scene Machine branding
3. Create FileUploader component (drag-drop)
4. Create Upload page with settings
5. Create Progress page with real-time updates
6. Create Jobs list page
7. Configure API proxy in Nuxt

### Page Structure
- **/** - Upload page: drag-drop file, select style/quality/compute mode
- **/jobs** - List of all jobs with status
- **/jobs/[id]** - Progress page with real-time updates, previews, download

### UI Components
```vue
<!-- Layout with Scene Machine branding -->
<template>
  <div class="min-h-screen bg-gray-100">
    <nav class="bg-white shadow">
      <div class="max-w-7xl mx-auto px-4 py-4">
        <NuxtLink to="/" class="text-xl font-bold">
          🎬 Scene Machine
        </NuxtLink>
      </div>
    </nav>
    <main class="max-w-7xl mx-auto px-4 py-8">
      <slot />
    </main>
  </div>
</template>
```

**Phase 7 Complete When:** Full user flow works in browser at SceneMachine.ai

---

## PHASE 8: CLOUD INTEGRATION

**Duration:** 3-4 days
**Goal:** Enable cloud GPU processing via SkyPilot
**Dependencies:** Phase 7 complete

### Key Tasks
1. Install SkyPilot with Lambda Labs support
2. Create SkyPilot task YAML configuration
3. Create cloud generation script
4. Create SkyPilotRunner class
5. Update generate_video task to support cloud mode

### SkyPilot Task Config
```yaml
# skypilot/video_gen.yaml
name: scene-machine-video-gen
resources:
  cloud: lambda
  accelerators: H100:1
  disk_size: 200

setup: |
  pip install torch diffusers transformers accelerate
  
run: |
  python /tmp/generate.py --prompt "$PROMPT" --output /tmp/output.mp4

envs:
  PROMPT: "default prompt"
```

**Phase 8 Complete When:** Generation can run on Lambda Labs H100s

---

## PHASE 9: POLISH & TESTING

**Duration:** 1 week
**Goal:** End-to-end testing, bug fixes, and polish

### Key Tasks
1. Write end-to-end test suite
2. Create performance benchmarks
3. Improve error handling and retry logic
4. Add UI polish (loading states, toasts, animations)
5. Write README and documentation
6. Final review and cleanup

### Performance Targets
- Parsing: < 30 seconds for 120-page screenplay
- Video generation (local): < 3 minutes per 5-second clip
- Full pipeline: MVP should complete in under 1 hour for short scripts

**Phase 9 Complete When:** Scene Machine ready for demo/launch

---

# PART VII: GAP ANALYSIS TEMPLATE

```markdown
# Week [N] Gap Analysis - Scene Machine
Date: [DATE]

## Phase Status
| Phase | Target % | Actual % | Gap | Notes |
|-------|----------|----------|-----|-------|
| Phase 0 | 100% | | | |
| Phase 1 | 100% | | | |
| Phase 2 | 100% | | | |
| Phase 3 | 100% | | | |
| Phase 4 | 100% | | | |
| Phase 5 | 100% | | | |
| Phase 6 | 100% | | | |
| Phase 7 | 100% | | | |
| Phase 8 | 100% | | | |
| Phase 9 | 100% | | | |

## Tasks Completed This Week
- [ ] Task X.Y: [Description]

## Blockers
1. [Blocker] - Impact: [High/Med/Low] - Mitigation: [Action]

## Adjustments for Next Week
1. [What will change]
```

---

# PART VIII: RISK REGISTER

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Character inconsistency across scenes | High | High | IP-Adapter + face embeddings; accept 80-85% similarity |
| VRAM overflow | Medium | High | Use quantized models; enable CPU offload |
| Cloud costs exceed budget | Medium | Medium | Implement cost caps; prioritize local |
| Lip sync quality poor | Medium | Medium | Pre-process audio; Wav2Lip fallback |
| Script parsing fails on non-standard formats | Medium | Low | Multiple parsers; manual correction |
| Lambda Labs unavailable | Low | High | RunPod/Vast.ai backup |

---

# PART IX: TROUBLESHOOTING

### "CUDA out of memory"
- Enable model CPU offload: `pipe.enable_model_cpu_offload()`
- Use smaller batch size
- Use more aggressive quantization

### "No face detected"
- Check image has clear face
- Try different InsightFace model
- Lower detection threshold

### "Celery task stuck"
- Check worker: `celery -A backend.app.workers.celery_app inspect active`
- Check Redis: `redis-cli ping`

### "FFmpeg error"
- Verify FFmpeg installed: `ffmpeg -version`
- Check input files valid: `ffprobe input.mp4`

---

# APPENDIX A: MODEL DOWNLOAD COMMANDS

```bash
# Wan 2.1 (local)
huggingface-cli download Wan-AI/Wan2.1-T2V-1.3B

# Llama 3.3 70B
huggingface-cli download meta-llama/Llama-3.3-70B-Instruct

# Flux Schnell
huggingface-cli download black-forest-labs/FLUX.1-schnell

# Kokoro TTS
git clone https://github.com/hexgrad/kokoro

# LatentSync
git clone https://github.com/bytedance/LatentSync

# InsightFace
pip install insightface
python -c "import insightface; insightface.app.FaceAnalysis(name='buffalo_l')"
```

---

# APPENDIX B: ENVIRONMENT VARIABLES

```bash
# .env.example for Scene Machine

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/scene_machine
REDIS_URL=redis://localhost:6379/0

# Paths
JOBS_PATH=/path/to/jobs
MODELS_PATH=/path/to/models

# Cloud
LAMBDA_API_KEY=your_lambda_key
RUNPOD_API_KEY=your_runpod_key

# Features
ENABLE_CLOUD=true
MAX_CONCURRENT_JOBS=3
MAX_FILE_SIZE_MB=50
```

---

# APPENDIX C: API ENDPOINTS

```
Scene Machine API (v1)

POST /api/v1/upload          - Upload screenplay
GET  /api/v1/jobs            - List all jobs
GET  /api/v1/jobs/{id}       - Get job details
DELETE /api/v1/jobs/{id}     - Cancel job
WS   /ws/jobs/{id}/progress  - Real-time progress
GET  /outputs/{id}/{file}    - Download output
GET  /health                 - Health check
```

---

# APPENDIX D: VIBE CODING PROMPTS

Use these when working with AI assistants in VS Code:

**Parser:**
"Create a Python class for Scene Machine that extracts text from a PDF screenplay using pdfplumber, preserving line breaks and identifying uppercase character names."

**TTS:**
"Write a Python class for Scene Machine using Kokoro TTS that converts dialogue text into WAV files with emotion modifiers for pitch and speed."

**Video:**
"Write a Python script for Scene Machine using diffusers to load Wan 2.1 and generate a 5-second video from a text prompt with VRAM optimization for 32GB GPUs."

**Lip Sync:**
"Write a Python script for Scene Machine using LatentSync to synchronize video mouth movements to audio, with error handling for no face detected."

**Orchestrator:**
"Create a Celery task chain for Scene Machine that orchestrates parsing → character setup → video gen → audio gen → lip sync → assembly with WebSocket progress."

**Assembly:**
"Create an FFmpeg wrapper class for Scene Machine with methods for concatenating videos, adding audio, applying transitions, and normalizing loudness."

---

# APPENDIX E: CLAUDE.md TEMPLATE

Create this file in your project root:

```markdown
# CLAUDE.md - Scene Machine AI Assistant Context

## Project: Scene Machine™
Transform screenplays into AI-generated movies.
Website: SceneMachine.ai

## Current Phase: [UPDATE THIS]
Phase X: [Phase Name]

## Active Task: [UPDATE THIS]
Task X.Y: [Task Description]

## Architecture
- Backend: Python 3.11 / FastAPI / Celery
- Frontend: Nuxt 3 / Vue 3 / Tailwind CSS
- Database: PostgreSQL + Redis
- AI: Wan 2.1, Kokoro TTS, LatentSync, Llama 3.3 70B

## Commands
- Start backend: uvicorn backend.app.main:app --reload
- Start frontend: cd frontend && npm run dev
- Start Celery: celery -A backend.app.workers.celery_app worker -l info
- Start services: docker compose up -d
- Run tests: pytest backend/tests/ -v

## Directory Map
- backend/app/services/parser/ - Screenplay parsing
- backend/app/services/video/ - Video generation
- backend/app/services/audio/ - TTS generation
- backend/app/services/lipsync/ - Lip synchronization
- backend/app/services/assembly/ - Final movie assembly
- backend/app/workers/tasks/ - Celery background tasks
- frontend/pages/ - Vue pages
- frontend/components/ - Reusable components

## Quality Standards
1. Test each component before moving to next task
2. Commit after each task completion
3. No technical debt - fix bugs immediately
4. Follow the master plan structure exactly

## Reference
See SCENE-MACHINE-MASTER-PLAN.md for complete specifications.
```

---

# END OF MASTER PLAN

---

**Product:** Scene Machine™
**Domain:** SceneMachine.ai
**Document Version:** 2.0
**Created:** December 30, 2025
**Owner:** Grant Whitmer (Independent Product)

---

## FINAL NOTES FOR VS CODE

1. **Start with Phase 0** - Don't skip scaffolding
2. **One Phase at a Time** - Tell your AI exactly which phase/task you're on
3. **Verify Before Proceeding** - Each task has verification steps
4. **Use CLAUDE.md** - Update it as you progress
5. **Gap Analysis Weekly** - Track progress, identify blockers
6. **Quality Over Speed** - Working demo > broken prototype

**The Scene Machine "WOW MOMENT":**
Upload a 3-page script → 10 minutes later → Download a 30-second movie with talking characters, music, and scene transitions.

**Let's build Scene Machine! 🎬**
