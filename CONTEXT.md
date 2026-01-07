# SceneMachine - AI Context Document

> This file provides essential context for AI assistants working on the SceneMachine codebase.

## Project Overview

**SceneMachine** is a screenplay-to-movie generation platform that transforms written screenplays into AI-generated video content. It functions as the "Adobe Premiere of generative video" - users summon, generate, refine, and assemble cinematic scenes from text rather than editing filmed footage.

### Core Workflow
1. **Import** - Upload screenplay (.fountain, .fdx, .pdf)
2. **Plan** - AI generates comprehensive movie plan with characters, scenes, visual themes
3. **Design** - Define character appearances in the Character Laboratory
4. **Break Down** - AI creates shot-by-shot breakdowns for each scene
5. **Generate** - Queue shots for video generation across multiple providers
6. **Assemble** - Combine generated clips into final movie with audio/music

---

## Technology Stack

### Frontend (Electron Desktop App)
| Technology | Version | Purpose |
|------------|---------|---------|
| Node.js | >=20.0.0 | Runtime requirement |
| Electron | ^28.3.3 | Desktop app framework |
| React | ^18.2.0 | UI framework |
| TypeScript | ^5.3.0 | Type safety |
| Vite | ^5.0.0 | Build tool / dev server |
| TailwindCSS | ^3.4.0 | Styling |
| Zustand | ^4.5.0 | State management |
| React Query | ^5.17.0 | Server state / caching |
| Framer Motion | ^10.18.0 | Animations |

### Backend (Python)
| Technology | Version | Purpose |
|------------|---------|---------|
| Python | >=3.11 | Runtime |
| FastAPI | >=0.109.0 | REST API framework |
| SQLAlchemy | >=2.0.0 | Async ORM |
| Pydantic | >=2.5.0 | Data validation |
| Alembic | >=1.13.0 | Database migrations |
| Uvicorn | >=0.27.0 | ASGI server |
| HTTPX | >=0.26.0 | Async HTTP client |

### Database
- **Production**: PostgreSQL 15+
- **Development**: SQLite with WAL mode
- **ORM**: SQLAlchemy 2.0 async

### Testing
| Tool | Purpose |
|------|---------|
| Vitest | Frontend unit tests |
| Playwright | E2E tests |
| pytest | Backend tests |
| pytest-asyncio | Async test support |

---

## Project Structure

```
scenemachine/
├── apps/
│   └── desktop/                    # Electron application
│       ├── src/
│       │   ├── main/               # Electron main process
│       │   │   └── index.ts        # ← ENTRY POINT (main process)
│       │   ├── renderer/           # React application
│       │   │   └── main.tsx        # ← ENTRY POINT (renderer)
│       │   └── preload/            # Preload scripts
│       └── package.json
├── packages/
│   ├── core/                       # Python backend
│   │   ├── scenemachine/
│   │   │   ├── main.py             # ← ENTRY POINT (backend)
│   │   │   ├── api/                # FastAPI routes & middleware
│   │   │   │   ├── routes/         # 20 route modules (200+ endpoints)
│   │   │   │   └── middleware/     # Security, logging, etc.
│   │   │   ├── ipc/                # IPC communication
│   │   │   │   └── handlers/       # 14 handler modules (200+ handlers)
│   │   │   ├── services/           # Business logic (20+ services)
│   │   │   ├── models/             # SQLAlchemy models (19 models)
│   │   │   ├── generators/         # Video generation providers
│   │   │   └── utils/              # Caching, helpers
│   │   ├── tests/
│   │   └── pyproject.toml
│   ├── shared-types/               # Shared TypeScript types
│   └── ui-components/              # Shared React components
├── docs/                           # Documentation
└── tools/                          # Build scripts, Docker
```

---

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Electron Desktop App                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐    ┌──────────────────────────────────┐  │
│  │   Main Process    │    │        Renderer Process          │  │
│  │   (index.ts)      │    │         (React App)              │  │
│  │                   │    │                                  │  │
│  │  BackendManager ──┼────┼─► IPC Bridge                     │  │
│  │  WindowManager    │    │   React Query                    │  │
│  │  IPC Handlers     │    │   Zustand Store                  │  │
│  └────────┬──────────┘    └──────────────────────────────────┘  │
│           │                                                      │
│           │ Unix Socket (~/.scenemachine/ipc.sock)              │
│           │ or Named Pipe (Windows)                              │
│           ▼                                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Python Backend                          │   │
│  │  ┌────────────┐  ┌────────────┐  ┌──────────────────┐    │   │
│  │  │ IPC Server │  │  REST API  │  │ Generation Queue │    │   │
│  │  │ (200+ hdlr)│  │ (FastAPI)  │  │   (Background)   │    │   │
│  │  └─────┬──────┘  └─────┬──────┘  └────────┬─────────┘    │   │
│  │        │               │                   │              │   │
│  │        └───────────────┼───────────────────┘              │   │
│  │                        ▼                                  │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │              Service Layer (20+ services)           │  │   │
│  │  │  ProjectService, CharacterService, GenerationSvc... │  │   │
│  │  └────────────────────────┬───────────────────────────┘  │   │
│  │                           ▼                              │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │         SQLAlchemy Async ORM (19 models)            │  │   │
│  │  │   PostgreSQL (prod) / SQLite (dev)                  │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────────┐
              │      External AI Providers         │
              │  ┌─────────┐ ┌─────────┐ ┌──────┐ │
              │  │Replicate│ │   Fal   │ │RunPod│ │
              │  └─────────┘ └─────────┘ └──────┘ │
              │  ┌─────────┐ ┌─────────────────┐  │
              │  │ ComfyUI │ │    ActCore      │  │
              │  └─────────┘ └─────────────────┘  │
              └───────────────────────────────────┘
```

### Startup Sequence

1. Electron main process starts (`apps/desktop/src/main/index.ts`)
2. `BackendManager` spawns Python backend as subprocess
3. Python backend creates Unix domain socket at `~/.scenemachine/ipc.sock`
4. IPC client connects with exponential backoff retry logic
5. Once backend signals ready, renderer process loads React app
6. React app communicates via IPC bridge through main process

### Communication Patterns

| Pattern | Use Case | Example |
|---------|----------|---------|
| IPC (Unix Socket) | Desktop app ↔ Backend | All UI operations |
| REST API | External integrations, testing | curl, web clients |
| WebSocket | Real-time updates | Generation progress |

---

## Database Schema

### Core Models (11)
| Model | Purpose |
|-------|---------|
| Project | Top-level container for all project data |
| Screenplay | Uploaded screenplay file and parsed content |
| Character | Character definitions with appearance/personality |
| Scene | Individual scenes from screenplay |
| Shot | Shot breakdowns within scenes |
| Asset | Media files (images, videos, audio) |
| GenerationJob | Video generation job queue |
| UserSettings | User preferences and encrypted API keys |
| ProjectShare | Sharing configuration |
| ProjectComment | Collaboration comments |
| ExportHistory | Export job records |

### ActForge Models (8)
| Model | Purpose |
|-------|---------|
| Performer | AI performer profiles |
| PerformanceTake | Individual performance recordings |
| Booking | Performer booking requests |
| Auction | Bid-based performer auctions |
| AuctionBid | Individual auction bids |
| PerformerRating | Performance ratings |
| AudioAsset | Sound effects and music |
| TextOverlay | Video text overlays |

### Key Relationships
```
Project (1) ←→ (1) Screenplay
Project (1) ←→ (N) Character
Project (1) ←→ (N) Scene
Scene   (1) ←→ (N) Shot
Shot    (1) ←→ (N) GenerationJob
Shot    (1) ←→ (N) Asset
```

---

## Development Commands

### Root Commands (Monorepo)
```bash
npm run dev           # Start desktop app in dev mode
npm run build         # Build desktop app
npm run test          # Run all tests (all workspaces)
npm run lint          # Lint all workspaces
npm run typecheck     # Type check all workspaces
npm run clean         # Clean all build artifacts
```

### Desktop App Commands
```bash
cd apps/desktop
npm run dev           # Full dev mode (main + renderer)
npm run dev:main      # Watch compile Electron main only
npm run dev:renderer  # Vite dev server only
npm run test          # Vitest unit tests
npm run test:watch    # Vitest watch mode
npm run test:coverage # Coverage report
npm run test:e2e      # Playwright E2E tests
npm run lint          # ESLint
npm run typecheck     # TypeScript check
npm run package:win   # Package for Windows
npm run package:mac   # Package for macOS
npm run package:linux # Package for Linux
```

### Backend Commands
```bash
cd packages/core
pip install -e ".[dev]"  # Install with dev dependencies
pytest                    # Run tests
pytest --cov              # With coverage
ruff check .              # Linting
mypy .                    # Type checking
alembic upgrade head      # Run migrations
alembic revision --autogenerate -m "description"  # Create migration
```

---

## Detailed Documentation

For in-depth information, see these comprehensive docs:

| Document | Description | Lines |
|----------|-------------|-------|
| [docs/SECURITY.md](docs/SECURITY.md) | Security architecture, API key encryption, rate limiting | ~780 |
| [docs/api/REST-API.md](docs/api/REST-API.md) | Complete REST API reference (200+ endpoints with curl examples) | ~2,800 |
| [docs/DATABASE.md](docs/DATABASE.md) | Database schema, ER diagrams, all 19 models | ~1,400 |
| [docs/CONFIGURATION.md](docs/CONFIGURATION.md) | Environment variables, runtime config | ~670 |
| [docs/PERFORMANCE.md](docs/PERFORMANCE.md) | Benchmarks, load testing, tuning guide | ~660 |
| [docs/CACHING.md](docs/CACHING.md) | LRU cache, LLM cache, file cache implementation | ~850 |
| [docs/api/README.md](docs/api/README.md) | IPC API documentation | ~690 |

---

## Key Files for AI Assistants

### When Adding New Features

| Task | Key Files |
|------|-----------|
| New API endpoint | `packages/core/scenemachine/api/routes/` |
| New IPC handler | `packages/core/scenemachine/ipc/handlers/` |
| New database model | `packages/core/scenemachine/models/` |
| New UI component | `apps/desktop/src/renderer/components/` |
| New service | `packages/core/scenemachine/services/` |

### When Debugging

| Area | Key Files |
|------|-----------|
| IPC issues | `apps/desktop/src/main/ipc/`, `packages/core/scenemachine/ipc/` |
| Database | `packages/core/scenemachine/models/`, `alembic/versions/` |
| Generation | `packages/core/scenemachine/generators/`, `services/generation_service.py` |
| Security | `packages/core/scenemachine/api/middleware/security.py` |

### Configuration Files

| File | Purpose |
|------|---------|
| `package.json` (root) | Workspace config, root scripts |
| `apps/desktop/package.json` | Frontend dependencies |
| `packages/core/pyproject.toml` | Backend dependencies, tool config |
| `.env` / `.env.example` | Environment variables |
| `tailwind.config.js` | Tailwind configuration |
| `vite.config.ts` | Vite build configuration |
| `electron-builder.yml` | Electron packaging config |

---

## Coding Conventions

### TypeScript/React
- Functional components with hooks
- Type imports: `import type { X } from 'y'`
- Named exports preferred over default exports
- Use `clsx` for conditional classNames
- State: Zustand for global, useState for local
- Server state: React Query with optimistic updates

### Python
- Async/await throughout (FastAPI, SQLAlchemy)
- Type hints required (strict mypy)
- Pydantic models for validation
- ruff for linting/formatting
- 100 character line limit

### Database
- UUID primary keys
- snake_case table/column names
- Soft deletes where appropriate
- Indexes on foreign keys and frequently queried columns

### Git
- Conventional commits (`feat:`, `fix:`, `docs:`, etc.)
- PR template with description and test plan
- Pre-commit hooks for linting

---

## Areas Requiring Special Attention

### Security (See [SECURITY.md](docs/SECURITY.md))
- API keys are Fernet-encrypted in database
- PBKDF2HMAC key derivation with 480K iterations
- Rate limiting: Token Bucket + Sliding Window
- Always validate `SECRET_KEY` environment variable

### Database Migrations
- Always create migrations for schema changes
- Test migrations in both directions (upgrade/downgrade)
- Never modify existing migration files
- Use `alembic revision --autogenerate` as starting point

### Video Generation Providers
- 5 providers with different capabilities
- Provider health endpoints available
- Circuit breaker pattern for failures
- Cost estimation before generation

### IPC Communication
- JSON-RPC style over Unix socket
- All handlers must be async
- Errors should use structured error responses
- See `docs/api/README.md` for IPC protocol

---

## Common Tasks

### Adding a New API Endpoint

1. Create route in `packages/core/scenemachine/api/routes/`
2. Add to router in `api/app.py`
3. Create service method if needed
4. Add tests in `tests/api/`
5. Document in `docs/api/REST-API.md`

### Adding a New Database Model

1. Create model in `packages/core/scenemachine/models/`
2. Export in `models/__init__.py`
3. Generate migration: `alembic revision --autogenerate -m "Add X"`
4. Run migration: `alembic upgrade head`
5. Document in `docs/DATABASE.md`

### Adding a New IPC Handler

1. Create handler in `packages/core/scenemachine/ipc/handlers/`
2. Register in handler registry
3. Add TypeScript types in `packages/shared-types/`
4. Document in `docs/api/README.md`

---

## Environment Setup

### Required Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/scenemachine
# Or for development:
DATABASE_URL=sqlite+aiosqlite:///./data/scenemachine.db

# Security (REQUIRED - generate with: openssl rand -hex 32)
SECRET_KEY=your-secret-key-here

# AI Providers (optional, configure as needed)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
REPLICATE_API_TOKEN=r8_...
FAL_KEY=...

# Paths
DATA_DIR=./data
CACHE_DIR=./data/cache
```

See [CONFIGURATION.md](docs/CONFIGURATION.md) for complete reference.

---

## Testing Strategy

### Unit Tests
- Frontend: Vitest with React Testing Library
- Backend: pytest with pytest-asyncio
- Target: 80% coverage

### Integration Tests
- API tests with httpx test client
- Database tests with SQLite in-memory

### E2E Tests
- Playwright for full application testing
- Test critical user workflows

### Running Tests
```bash
# All tests
npm run test

# Frontend only
cd apps/desktop && npm run test

# Backend only
cd packages/core && pytest

# E2E
cd apps/desktop && npm run test:e2e
```

---

## Troubleshooting

### Backend Won't Start
1. Check Python version: `python --version` (needs 3.11+)
2. Check dependencies: `pip install -e ".[dev]"`
3. Check database URL in `.env`
4. Check IPC socket permissions

### IPC Connection Fails
1. Check if backend process is running
2. Verify socket path: `~/.scenemachine/ipc.sock`
3. Check for stale socket files
4. Review logs in `~/.scenemachine/logs/`

### Generation Jobs Stuck
1. Check provider API keys in settings
2. Check provider health: `GET /api/v1/generation/providers/health`
3. Check queue status: `GET /api/v1/generation/queue/status`
4. Check for rate limiting

### Database Issues
1. Run migrations: `alembic upgrade head`
2. Check connection string
3. For SQLite: ensure WAL mode is enabled
4. Check file permissions on data directory
