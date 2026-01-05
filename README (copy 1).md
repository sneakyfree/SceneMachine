# SceneMachine.ai

**Screenplay-to-Movie Generation Platform**

SceneMachine.ai enables users—including non-technical users such as screenwriters without production experience—to transform written screenplays into generated video content.

## Overview

SceneMachine functions as the "Adobe Premiere of generative video" where users do not edit filmed footage but instead **summon, generate, refine, and assemble cinematic scenes from text, structure, and creative intent**.

## Core User Journey

1. **Upload** - Screenplay (.fountain, .pdf, .fdx)
2. **Plan** - AI generates Movie Plan
3. **Character Laboratory** - Lock each character's likeness
4. **Scene Planning** - Shot design and breakdown
5. **Generate** - Execute generation jobs
6. **Review** - Watch generated scenes
7. **Refine** - Regenerate specific shots
8. **Export** - Final movie (.mp4, .mov, etc.)

## Project Structure

```
scenemachine/
├── apps/
│   ├── desktop/              # Electron + React application
│   └── web/                  # Future web application
├── packages/
│   ├── core/                 # Python backend
│   ├── shared-types/         # Shared TypeScript types
│   └── ui-components/        # Shared React components
├── tools/
│   ├── scripts/              # Build and utility scripts
│   └── docker/               # Docker configurations
├── docs/                     # Documentation
└── .github/workflows/        # CI/CD pipelines
```

## Technology Stack

| Layer | Technology |
|-------|------------|
| Desktop Application | Electron + React/TypeScript |
| Backend Core | Python 3.11+ (FastAPI) |
| Database | PostgreSQL + SQLite (local) |
| Video Processing | FFmpeg + Python bindings |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- npm or yarn

### Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/scenemachine.git
   cd scenemachine
   ```

2. Install Python dependencies:
   ```bash
   cd packages/core
   pip install -e ".[dev]"
   ```

3. Install Node.js dependencies:
   ```bash
   npm install
   ```

4. Start the development environment:
   ```bash
   # Terminal 1: Start Python backend
   cd packages/core
   python -m scenemachine.main
   
   # Terminal 2: Start Electron app
   cd apps/desktop
   npm run dev
   ```

## Design Principles

| Principle | Description |
|-----------|-------------|
| **Low-Tech Accessibility** | A grandmother who has written screenplays but has no technical background must be able to use this platform successfully |
| **Guided Workflow** | Every step is explicit, explained, and requires user understanding before proceeding |
| **Transparency** | Users always understand what the system is doing, why, and what it will cost |
| **Reversibility** | Every action can be undone, every decision can be revisited |
| **Quality Over Speed** | The system optimizes for output quality; speed is secondary |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## License

[License Type] - See [LICENSE](LICENSE) for details.

---

*Document Version: 0.1.0*
