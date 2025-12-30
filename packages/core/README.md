# SceneMachine Core

Python backend for SceneMachine.ai - the screenplay-to-movie generation platform.

## Installation

### Development Installation

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install with development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### ML Dependencies (Optional)

For local ML model execution:

```bash
pip install -e ".[ml]"
```

## Development

### Running Tests

```bash
pytest
```

### Linting and Type Checking

```bash
# Run ruff linter
ruff check .

# Run ruff formatter
ruff format .

# Run mypy type checker
mypy .
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

## Project Structure

```
scenemachine/
├── api/              # FastAPI routes and application
│   └── routes/       # Route handlers by domain
├── models/           # SQLAlchemy ORM models
├── schemas/          # Pydantic schemas for validation
├── services/         # Business logic layer
├── parsers/          # Screenplay parsing (Fountain, PDF, etc.)
├── generators/       # Video generation orchestration
├── workflows/        # Long-running workflow definitions
├── ipc/              # Electron IPC communication
└── utils/            # Shared utilities
```

## API Documentation

When running in development mode, API documentation is available at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
