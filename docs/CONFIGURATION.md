# SceneMachine Configuration Reference

Complete reference for all environment variables, runtime settings, and configuration best practices.

## Table of Contents

- [Overview](#overview)
- [Configuration Sources](#configuration-sources)
- [Environment Variables Reference](#environment-variables-reference)
  - [Application Settings](#application-settings)
  - [Server Settings](#server-settings)
  - [Database Settings](#database-settings)
  - [Storage Settings](#storage-settings)
  - [Security Settings](#security-settings)
  - [AI/ML Provider Settings](#aiml-provider-settings)
  - [Video Generation Settings](#video-generation-settings)
  - [IPC Settings](#ipc-settings)
  - [Logging Settings](#logging-settings)
- [Configuration File Examples](#configuration-file-examples)
- [Runtime Configuration (Database)](#runtime-configuration-database)
- [Validation Rules](#validation-rules)
- [Best Practices](#best-practices)

---

## Overview

SceneMachine uses a layered configuration system:

1. **Environment Variables** - Highest priority, set in shell or container
2. **`.env` File** - Development convenience, loaded from project root
3. **Defaults** - Sensible defaults for development
4. **Runtime Settings** - User-configurable settings stored in database

**Configuration Framework:** Pydantic Settings v2
**Validation:** Automatic type coercion and validation
**Caching:** Settings are cached at startup (use `reset_settings()` to reload)

---

## Configuration Sources

### Priority Order (Highest to Lowest)

```
1. Environment Variables (OS level)
2. .env File (project root)
3. Default Values (in code)
```

### Loading Behavior

```python
# packages/core/scenemachine/config.py

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",              # Load from .env file
        env_file_encoding="utf-8",    # UTF-8 encoding
        case_sensitive=False,         # ENV_VAR = env_var
        extra="ignore",               # Ignore unknown variables
    )
```

### Accessing Settings

```python
from scenemachine.config import get_settings

settings = get_settings()  # Cached singleton

if settings.is_production:
    # Production-specific behavior
    pass

print(settings.database_url)
```

---

## Environment Variables Reference

### Application Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `APP_NAME` | str | `SceneMachine` | Application name |
| `VERSION` | str | `0.1.0` | Application version |
| `DEBUG` | bool | `false` | Enable debug mode |
| `ENVIRONMENT` | str | `development` | Environment name |

**Environment Values:**
- `development` - Local development (debug features enabled)
- `production` - Production deployment (hardened security)
- `testing` - Test suite execution

**Usage:**

```bash
# Production deployment
export ENVIRONMENT=production
export DEBUG=false
```

---

### Server Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `HOST` | str | `127.0.0.1` | Server bind address |
| `PORT` | int | `8000` | Server port |
| `WORKERS` | int | `1` | Number of worker processes |

**Production Recommendations:**
- Use `HOST=0.0.0.0` only behind a reverse proxy
- Set `WORKERS` to CPU count for API servers
- Desktop app should keep `WORKERS=1`

```bash
# Production API server
export HOST=0.0.0.0
export PORT=8000
export WORKERS=4
```

---

### Database Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DATABASE_URL` | str | `sqlite:///./data/scenemachine.db` | Database connection URL |
| `DATABASE_ECHO` | bool | `false` | Echo SQL statements (debugging) |

**SQLite (Development):**
```bash
export DATABASE_URL="sqlite:///./data/scenemachine.db"
```

**PostgreSQL (Production):**
```bash
export DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/scenemachine"
```

**PostgreSQL with SSL:**
```bash
export DATABASE_URL="postgresql+asyncpg://user:password@host:5432/scenemachine?ssl=require"
```

---

### Storage Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DATA_DIR` | Path | `./data` | Root data directory |
| `UPLOAD_DIR` | Path | `./data/uploads` | User uploads directory |
| `OUTPUT_DIR` | Path | `./data/outputs` | Generated outputs directory |
| `MODEL_CACHE_DIR` | Path | `./data/models` | AI model cache directory |

**Auto-Creation:** Directories are automatically created if they don't exist.

**Production Example:**
```bash
export DATA_DIR=/var/lib/scenemachine
export UPLOAD_DIR=/var/lib/scenemachine/uploads
export OUTPUT_DIR=/var/lib/scenemachine/outputs
export MODEL_CACHE_DIR=/var/lib/scenemachine/models
```

**Docker Volume Mapping:**
```yaml
volumes:
  - ./data:/var/lib/scenemachine
```

---

### Security Settings

| Variable | Type | Default | Sensitive | Description |
|----------|------|---------|-----------|-------------|
| `SECRET_KEY` | str | `change-me...` | **YES** | Encryption key for API keys |
| `CORS_ORIGINS` | list | `["http://localhost:3000", "http://localhost:5173"]` | No | Allowed CORS origins |

**SECRET_KEY Requirements:**
- **MUST** be changed in production
- Minimum 32 characters recommended
- Used for API key encryption (Fernet/PBKDF2)
- Keep consistent across deployments (or re-encrypt keys)

**Generating a Strong Secret:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

**CORS_ORIGINS Format:**
```bash
# Single origin
export CORS_ORIGINS="https://app.scenemachine.io"

# Multiple origins (comma-separated)
export CORS_ORIGINS="https://app.scenemachine.io,https://staging.scenemachine.io"
```

---

### AI/ML Provider Settings

| Variable | Type | Default | Sensitive | Description |
|----------|------|---------|-----------|-------------|
| `DEFAULT_LLM_PROVIDER` | str | `anthropic` | No | Default LLM provider |
| `ANTHROPIC_API_KEY` | str | None | **YES** | Anthropic Claude API key |
| `OPENAI_API_KEY` | str | None | **YES** | OpenAI API key |

**Supported LLM Providers:**
- `anthropic` - Claude (recommended for screenplay analysis)
- `openai` - GPT-4 (alternative)

**Example:**
```bash
export DEFAULT_LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-api...
```

---

### Video Generation Settings

| Variable | Type | Default | Sensitive | Description |
|----------|------|---------|-----------|-------------|
| `DEFAULT_VIDEO_MODEL` | str | `local` | No | Default video provider |
| `MAX_CONCURRENT_GENERATIONS` | int | `2` | No | Max parallel jobs |
| `GENERATION_TIMEOUT_SECONDS` | int | `600` | No | Job timeout (10 min) |

**Replicate.com Settings:**

| Variable | Type | Default | Sensitive | Description |
|----------|------|---------|-----------|-------------|
| `REPLICATE_API_TOKEN` | str | None | **YES** | Replicate API token |
| `REPLICATE_VIDEO_MODEL` | str | None | No | Model name (minimax, luma, kling) |

**Fal.ai Settings:**

| Variable | Type | Default | Sensitive | Description |
|----------|------|---------|-----------|-------------|
| `FAL_API_KEY` | str | None | **YES** | Fal.ai API key |
| `FAL_VIDEO_MODEL` | str | None | No | Model name (ltx, cogvideox, hunyuan) |

**RunPod Settings:**

| Variable | Type | Default | Sensitive | Description |
|----------|------|---------|-----------|-------------|
| `RUNPOD_API_KEY` | str | None | **YES** | RunPod API key |
| `RUNPOD_ENDPOINT_ID` | str | None | No | Serverless endpoint ID |

**ComfyUI Settings (Local):**

| Variable | Type | Default | Sensitive | Description |
|----------|------|---------|-----------|-------------|
| `COMFYUI_URL` | str | `http://127.0.0.1:8188` | No | ComfyUI server URL |
| `COMFYUI_DEFAULT_MODEL` | str | None | No | Default workflow model |

**ElevenLabs Settings (TTS):**

| Variable | Type | Default | Sensitive | Description |
|----------|------|---------|-----------|-------------|
| `ELEVENLABS_API_KEY` | str | None | **YES** | ElevenLabs API key |
| `ELEVENLABS_VOICE_ID` | str | None | No | Default voice ID |

**Provider Priority Configuration:**
```bash
# Use Replicate as primary, fall back to local
export DEFAULT_VIDEO_MODEL=replicate
export REPLICATE_API_TOKEN=r8_...
export REPLICATE_VIDEO_MODEL=minimax

# Fallback to local ComfyUI
export COMFYUI_URL=http://127.0.0.1:8188
```

---

### IPC Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `IPC_SOCKET_PATH` | str | `/tmp/scenemachine.sock` | Unix socket path |

**Windows Configuration:**
```bash
# Windows uses named pipes (automatic)
# Or TCP socket
export IPC_SOCKET_PATH="tcp://127.0.0.1:9999"
```

**Docker Configuration:**
```yaml
volumes:
  - /tmp/scenemachine.sock:/tmp/scenemachine.sock
```

---

### Logging Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `LOG_LEVEL` | str | `INFO` | Logging level |
| `LOG_FORMAT` | str | `%(asctime)s...` | Log message format |

**Log Levels:**
- `DEBUG` - Verbose debugging (development only)
- `INFO` - Normal operation
- `WARNING` - Warnings and above
- `ERROR` - Errors only
- `CRITICAL` - Critical errors only

**Production Logging:**
```bash
export LOG_LEVEL=WARNING
export LOG_FORMAT="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

**JSON Logging (for log aggregation):**
```bash
export LOG_FORMAT='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}'
```

---

## Configuration File Examples

### Development `.env`

```bash
# ===========================================
# SceneMachine Development Configuration
# ===========================================

# Application
ENVIRONMENT=development
DEBUG=true

# Server (desktop app)
HOST=127.0.0.1
PORT=8000
WORKERS=1

# Database (SQLite for development)
DATABASE_URL=sqlite:///./data/scenemachine.db
DATABASE_ECHO=false

# Storage (local directories)
DATA_DIR=./data
UPLOAD_DIR=./data/uploads
OUTPUT_DIR=./data/outputs
MODEL_CACHE_DIR=./data/models

# Security (CHANGE IN PRODUCTION!)
SECRET_KEY=dev-only-change-me-in-production-use-strong-key
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# AI Providers (add your keys)
DEFAULT_LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...

# Video Generation (local by default)
DEFAULT_VIDEO_MODEL=local
MAX_CONCURRENT_GENERATIONS=2
GENERATION_TIMEOUT_SECONDS=600

# ComfyUI (local GPU)
COMFYUI_URL=http://127.0.0.1:8188
# COMFYUI_DEFAULT_MODEL=animatediff-v3

# Cloud Providers (optional)
# REPLICATE_API_TOKEN=r8_...
# FAL_API_KEY=...
# RUNPOD_API_KEY=...

# IPC
IPC_SOCKET_PATH=/tmp/scenemachine.sock

# Logging
LOG_LEVEL=DEBUG
```

### Production `.env`

```bash
# ===========================================
# SceneMachine Production Configuration
# ===========================================

# Application
ENVIRONMENT=production
DEBUG=false

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=4

# Database (PostgreSQL)
DATABASE_URL=postgresql+asyncpg://scenemachine:${DB_PASSWORD}@db.internal:5432/scenemachine?ssl=require
DATABASE_ECHO=false

# Storage (persistent volumes)
DATA_DIR=/var/lib/scenemachine
UPLOAD_DIR=/var/lib/scenemachine/uploads
OUTPUT_DIR=/var/lib/scenemachine/outputs
MODEL_CACHE_DIR=/var/lib/scenemachine/models

# Security (MUST BE CHANGED!)
SECRET_KEY=${SCENEMACHINE_SECRET_KEY}
CORS_ORIGINS=https://app.scenemachine.io

# AI Providers
DEFAULT_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}

# Video Generation
DEFAULT_VIDEO_MODEL=replicate
MAX_CONCURRENT_GENERATIONS=10
GENERATION_TIMEOUT_SECONDS=900

# Replicate (primary)
REPLICATE_API_TOKEN=${REPLICATE_API_TOKEN}
REPLICATE_VIDEO_MODEL=minimax

# Logging
LOG_LEVEL=WARNING
```

### Testing `.env.test`

```bash
# ===========================================
# SceneMachine Test Configuration
# ===========================================

ENVIRONMENT=testing
DEBUG=false

# In-memory SQLite for tests
DATABASE_URL=sqlite:///:memory:

# Temporary directories
DATA_DIR=/tmp/scenemachine_test
UPLOAD_DIR=/tmp/scenemachine_test/uploads
OUTPUT_DIR=/tmp/scenemachine_test/outputs

# Test secret
SECRET_KEY=test-secret-key-not-for-production

# Mock providers
DEFAULT_LLM_PROVIDER=anthropic
DEFAULT_VIDEO_MODEL=local

# Logging
LOG_LEVEL=WARNING
```

### Docker `.env.docker`

```bash
# ===========================================
# SceneMachine Docker Configuration
# ===========================================

ENVIRONMENT=production
DEBUG=false

HOST=0.0.0.0
PORT=8000

# Database from Docker service
DATABASE_URL=postgresql+asyncpg://scenemachine:password@postgres:5432/scenemachine

# Volumes
DATA_DIR=/app/data
UPLOAD_DIR=/app/data/uploads
OUTPUT_DIR=/app/data/outputs
MODEL_CACHE_DIR=/app/data/models

# Security
SECRET_KEY=${SCENEMACHINE_SECRET_KEY}
CORS_ORIGINS=http://localhost:3000

# IPC (internal)
IPC_SOCKET_PATH=/app/sockets/scenemachine.sock

LOG_LEVEL=INFO
```

---

## Runtime Configuration (Database)

Some settings can be changed at runtime without restarting, stored in the `user_settings` table:

### User-Configurable Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `llm_provider` | enum | anthropic | Active LLM provider |
| `video_provider` | enum | local | Active video provider |
| `max_concurrent_generations` | int | 2 | Concurrent job limit |
| `generation_timeout_seconds` | int | 600 | Job timeout |
| `default_video_resolution` | str | 1920x1080 | Default resolution |
| `default_video_fps` | int | 24 | Default frame rate |
| `theme_mode` | enum | dark | UI theme |
| `auto_save_enabled` | bool | true | Auto-save projects |
| `auto_cleanup_temp_files` | bool | true | Clean temp files |
| `max_cache_size_gb` | int | 10 | Cache size limit |
| `default_export_format` | str | mp4_h264 | Export format |
| `default_export_quality` | str | high | Export quality |

### Accessibility Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `font_size_scale` | enum | medium | Font size (small/medium/large/extra-large) |
| `high_contrast_enabled` | bool | false | High contrast mode |
| `reduce_motion_enabled` | bool | false | Reduce animations |
| `large_click_targets_enabled` | bool | false | Larger click areas |

### API Key Storage (Encrypted)

API keys entered via the UI are stored encrypted in the database:

| Field | Encryption | Description |
|-------|------------|-------------|
| `anthropic_api_key` | Fernet (AES-128-CBC) | Anthropic key |
| `openai_api_key` | Fernet (AES-128-CBC) | OpenAI key |
| `replicate_api_key` | Fernet (AES-128-CBC) | Replicate key |
| `fal_api_key` | Fernet (AES-128-CBC) | Fal.ai key |
| `runwayml_api_key` | Fernet (AES-128-CBC) | RunwayML key |

See [SECURITY.md](SECURITY.md) for encryption details.

### Modifying Runtime Settings

**Via REST API:**
```bash
curl -X PATCH http://localhost:8000/api/v1/settings/config \
  -H "Content-Type: application/json" \
  -d '{"max_concurrent_generations": 4}'
```

**Via IPC:**
```json
{
  "type": "request",
  "method": "settings.update",
  "params": {"max_concurrent_generations": 4}
}
```

---

## Validation Rules

### Automatic Type Coercion

Pydantic automatically coerces compatible types:

```python
# String "true" -> bool True
DEBUG=true

# String "8000" -> int 8000
PORT=8000

# String "1,2,3" -> list ["1", "2", "3"]
CORS_ORIGINS=http://a.com,http://b.com
```

### Directory Auto-Creation

Storage directories are automatically created:

```python
@field_validator("data_dir", "upload_dir", "output_dir", "model_cache_dir", mode="after")
@classmethod
def ensure_directory_exists(cls, v: Path) -> Path:
    v.mkdir(parents=True, exist_ok=True)
    return v
```

### CORS Origins Parsing

```python
# Both formats work:
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"]
```

---

## Best Practices

### Security

1. **Never commit `.env` files** to version control
2. **Use different SECRET_KEY** for each environment
3. **Rotate API keys** regularly
4. **Store production secrets** in secure vault (HashiCorp, AWS Secrets Manager)
5. **Use environment variables** for sensitive values in containers

### Development

1. **Copy `.env.example` to `.env`** for local setup
2. **Use SQLite** for local development
3. **Enable DEBUG** and DATABASE_ECHO for troubleshooting
4. **Keep LOG_LEVEL=DEBUG** during development

### Production

1. **Use PostgreSQL** for production databases
2. **Disable DEBUG** mode completely
3. **Set appropriate WORKERS** count (CPU cores)
4. **Use WARNING or ERROR** log level
5. **Configure SSL** for database connections
6. **Set restrictive CORS_ORIGINS**

### Docker/Kubernetes

1. **Use environment variables** instead of .env files
2. **Mount persistent volumes** for storage directories
3. **Use secrets management** for sensitive values
4. **Configure health checks** for container orchestration

### Example: Kubernetes ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: scenemachine-config
data:
  ENVIRONMENT: "production"
  HOST: "0.0.0.0"
  PORT: "8000"
  LOG_LEVEL: "WARNING"
---
apiVersion: v1
kind: Secret
metadata:
  name: scenemachine-secrets
type: Opaque
stringData:
  SECRET_KEY: "your-production-secret-key"
  DATABASE_URL: "postgresql+asyncpg://..."
  ANTHROPIC_API_KEY: "sk-ant-..."
```

---

## Related Documentation

- [SECURITY.md](SECURITY.md) - Security settings and API key encryption
- [DATABASE.md](DATABASE.md) - Database configuration and settings storage
- [PERFORMANCE.md](PERFORMANCE.md) - Performance tuning settings
