# SceneMachine Architecture

This document provides a comprehensive overview of the SceneMachine.ai architecture, designed to transform screenplays into AI-generated video content.

## System Overview

SceneMachine is a desktop application built with a hybrid architecture:

- **Frontend**: Electron + React TypeScript application
- **Backend**: Python FastAPI server with async SQLAlchemy
- **Communication**: IPC via Unix domain sockets
- **Database**: PostgreSQL for persistence

```
┌─────────────────────────────────────────────────────────────────┐
│                     Electron Desktop App                         │
│  ┌────────────────────────┐    ┌─────────────────────────────┐  │
│  │     Renderer Process   │    │       Main Process          │  │
│  │  ┌──────────────────┐  │    │  ┌─────────────────────┐   │  │
│  │  │  React + TypeScript  │  │    │  │   IPC Bridge       │   │  │
│  │  │  - Components     │  │    │  │   - Socket Client   │   │  │
│  │  │  - Zustand Stores │◄─┼────┼─►│   - Message Routing │   │  │
│  │  │  - React Query    │  │    │  └─────────────────────┘   │  │
│  │  └──────────────────┘  │    │            │                │  │
│  └────────────────────────┘    └────────────┼────────────────┘  │
└─────────────────────────────────────────────┼───────────────────┘
                                              │ Unix Socket
                                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Python Backend Server                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐  │
│  │   IPC Handlers  │  │    Services     │  │    Models      │  │
│  │  - projects.*   │  │  - ProjectSvc   │  │  - Project     │  │
│  │  - screenplay.* │  │  - ScreenplaySvc│  │  - Screenplay  │  │
│  │  - scenes.*     │  │  - CharacterSvc │  │  - Character   │  │
│  │  - generation.* │  │  - GenerationSvc│  │  - Scene       │  │
│  │  - audio.*      │  │  - AudioSvc     │  │  - Shot        │  │
│  └────────┬────────┘  └────────┬────────┘  └────────┬───────┘  │
│           │                    │                    │          │
│           └────────────────────┼────────────────────┘          │
│                                ▼                               │
│                    ┌─────────────────────┐                     │
│                    │    PostgreSQL DB    │                     │
│                    └─────────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
SceneMachine/
├── apps/
│   ├── desktop/                 # Electron desktop application
│   │   ├── src/
│   │   │   ├── main/           # Electron main process
│   │   │   ├── preload/        # Preload scripts (IPC bridge)
│   │   │   └── renderer/       # React frontend
│   │   │       ├── components/ # UI components
│   │   │       ├── pages/      # Route pages
│   │   │       ├── stores/     # Zustand state stores
│   │   │       ├── hooks/      # Custom React hooks
│   │   │       ├── api/        # API client
│   │   │       └── lib/        # Utilities
│   │   └── e2e/               # Playwright E2E tests
│   └── web/                    # Future web application
│
├── packages/
│   ├── core/                   # Python backend
│   │   ├── scenemachine/
│   │   │   ├── api/           # FastAPI routes
│   │   │   ├── services/      # Business logic
│   │   │   ├── models/        # SQLAlchemy models
│   │   │   ├── ipc/           # IPC handler definitions
│   │   │   ├── parsers/       # Screenplay parsers
│   │   │   ├── generators/    # Video generation providers
│   │   │   ├── workflows/     # Multi-step workflows
│   │   │   ├── schemas/       # Pydantic schemas
│   │   │   └── utils/         # Utilities
│   │   ├── tests/             # Pytest test suite
│   │   └── alembic/           # Database migrations
│   │
│   ├── shared-types/          # Shared TypeScript types
│   └── ui-components/         # Shared UI component library
│
├── tools/
│   ├── scripts/               # Build and utility scripts
│   └── docker/                # Docker configurations
│
└── docs/
    ├── architecture/          # Architecture documentation
    ├── api/                   # API documentation
    └── user-guide/            # User documentation
```

## Core Components

### Frontend (Electron + React)

#### Main Process (`apps/desktop/src/main/`)
- Manages application lifecycle
- Creates browser windows
- Handles native OS integration
- Spawns and manages Python backend process
- Routes IPC messages to backend

#### Preload Scripts (`apps/desktop/src/preload/`)
- Secure bridge between renderer and main process
- Exposes limited API via `contextBridge`
- Handles IPC communication abstraction

#### Renderer Process (`apps/desktop/src/renderer/`)
- React 18 with TypeScript
- **State Management**: Zustand with immer middleware
- **Data Fetching**: TanStack React Query
- **Routing**: React Router with hash router
- **Styling**: Tailwind CSS with custom design system
- **Icons**: Lucide React

### Backend (Python FastAPI)

#### API Layer (`packages/core/scenemachine/api/`)
- FastAPI REST endpoints
- Swagger/OpenAPI documentation
- Request validation with Pydantic

#### IPC Handlers (`packages/core/scenemachine/ipc/`)
- Socket-based IPC communication
- Handler registry pattern
- Async message processing

#### Services (`packages/core/scenemachine/services/`)
| Service | Purpose |
|---------|---------|
| `ProjectService` | Project CRUD operations |
| `ScreenplayService` | Screenplay parsing and management |
| `CharacterService` | Character extraction and management |
| `ScenePlanningService` | Scene analysis and shot breakdown |
| `GenerationService` | Video generation orchestration |
| `AssemblyService` | Video assembly and export |
| `AudioService` | TTS and voice management |
| `SettingsService` | User preferences and API keys |
| `StorageService` | File and asset management |

#### Models (`packages/core/scenemachine/models/`)
- SQLAlchemy async ORM models
- PostgreSQL with UUID primary keys
- JSON columns for flexible data

## Data Flow

### Screenplay Processing Pipeline

```
1. Upload Screenplay (.fountain/.fdx)
         │
         ▼
2. Parse Screenplay
   - Extract metadata (title, author)
   - Identify scenes, characters, dialogue
         │
         ▼
3. Create Movie Plan
   - LLM analyzes screenplay
   - Generates cinematic breakdown
   - Identifies visual requirements
         │
         ▼
4. Character Definition
   - User defines appearances
   - Assigns voices (TTS)
   - Uploads reference images
         │
         ▼
5. Scene Planning
   - AI generates shot breakdowns
   - User reviews/edits shots
   - Locks approved shots
         │
         ▼
6. Generation Queue
   - Shots queued for generation
   - Multiple providers supported
   - Progress tracking
         │
         ▼
7. Assembly & Export
   - Shots assembled into scenes
   - Audio/dialogue added
   - Final video export
```

### IPC Communication

```typescript
// Frontend calls backend
const result = await window.electronAPI.backendRequest(
  'projects.create',
  { name: 'My Project' }
);

// IPC message flow:
// 1. Renderer → Main (via contextBridge)
// 2. Main → Backend (via Unix socket)
// 3. Backend processes request
// 4. Backend → Main (response via socket)
// 5. Main → Renderer (via IPC)
```

## State Management

### Zustand Stores

| Store | Purpose |
|-------|---------|
| `projectStore` | Current project, UI state |
| `settingsStore` | User settings, API keys |
| `toastStore` | Toast notifications |
| `audioStore` | TTS providers, voices |

### React Query

Used for server state management:
- Automatic caching
- Background refetching
- Optimistic updates
- Error handling

## Security Considerations

### API Key Storage
- API keys encrypted at rest using Fernet (AES-128-CBC)
- Encryption key derived from machine-specific data
- Keys stored in database, never in plain text

### Electron Security
- Context isolation enabled
- Node integration disabled in renderer
- Content Security Policy enforced
- Preload scripts for safe IPC

### Input Validation
- All inputs validated with Pydantic schemas
- SQL injection prevented via SQLAlchemy ORM
- Path traversal protection in file operations

## Performance Optimizations

### Frontend
- Code splitting with React.lazy
- Memoization with useMemo/useCallback
- Virtual scrolling for large lists
- Image lazy loading

### Backend
- Async I/O throughout
- Connection pooling for database
- LRU caching for settings
- Batch operations where possible

## Error Handling

### Frontend
- React Error Boundaries
- Toast notifications for user feedback
- Graceful degradation

### Backend
- Structured error responses
- Retry logic for external APIs
- Transaction rollback on failures

## Testing Strategy

### Unit Tests
- **Frontend**: Vitest + Testing Library
- **Backend**: Pytest with async support

### E2E Tests
- Playwright for browser automation
- Test critical user journeys

### Coverage Targets
- Statements: 50%+
- Branches: 50%+
- Functions: 50%+

## Deployment

### Development
```bash
# Backend
cd packages/core
pip install -e ".[dev]"
python -m scenemachine.main

# Frontend
cd apps/desktop
npm install
npm run dev
```

### Production Build
```bash
# Build desktop app
cd apps/desktop
npm run package

# Creates platform-specific installers
```

## Future Considerations

1. **Web Application**: Shared UI components for web deployment
2. **Cloud Services**: Optional cloud-based generation
3. **Collaboration**: Multi-user project sharing
4. **Plugin System**: Custom generation providers
5. **Mobile Companion**: Preview and review on mobile
