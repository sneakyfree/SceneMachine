
# SceneMachine
SceneMachine is the ultimate screenplay-to-movie one stop shop.

# SceneMachine.ai

A screenplay-to-movie platform that enables users to transform written screenplays into generated video content.

## Overview

SceneMachine.ai is the "Adobe Premiere of generative video" - a platform where users summon, generate, refine, and assemble cinematic scenes from text, structure, and creative intent rather than editing filmed footage.

### Key Features

- **Screenplay Import**: Upload .fountain, .pdf, or .fdx screenplay files
- **AI Movie Planning**: Automatic generation of comprehensive movie plans
- **Character Laboratory**: Define and lock character likenesses for consistency
- **Scene Planning**: AI-assisted shot breakdowns with user control
- **Video Generation**: Multi-provider generation orchestration
- **Assembly & Export**: Professional-grade final movie assembly

## Project Structure

```
scenemachine/
├── apps/
│   ├── desktop/          # Electron application
│   └── web/              # Future web application
├── packages/
│   ├── core/             # Python backend
│   ├── shared-types/     # Shared TypeScript types
│   └── ui-components/    # Shared React components
├── tools/
│   ├── scripts/          # Build and utility scripts
│   └── docker/           # Docker configurations
└── docs/                 # Documentation
```

## Prerequisites

- **Node.js** 20.x or later
- **Python** 3.11 or later
- **PostgreSQL** 15.x or later (for production)
- **FFmpeg** (for video processing)

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/scenemachine.git
cd scenemachine
```

### 2. Install Dependencies

```bash
# Install Node.js dependencies
npm install

# Install Python dependencies
cd packages/core
pip install -e ".[dev]"
cd ../..
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 4. Start Development

```bash
# Start the desktop application in development mode
npm run dev
```

## Development

### Running Tests

```bash
# Run all tests
npm test

# Run Python tests
cd packages/core
pytest

# Run TypeScript tests
cd apps/desktop
npm test
```

### Linting and Type Checking

```bash
# Python
cd packages/core
ruff check .
mypy .

# TypeScript
cd apps/desktop
npm run lint
npm run typecheck
```

## Architecture

SceneMachine uses a hybrid architecture:

- **Frontend**: Electron with React/TypeScript
- **Backend**: Python FastAPI running as a subprocess
- **Communication**: IPC via Unix sockets (Linux/macOS) or named pipes (Windows)
- **Database**: PostgreSQL (production) / SQLite (local development)

See [docs/architecture/](docs/architecture/) for detailed architecture documentation.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

