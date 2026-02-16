# SceneMachine — Production Deployment Checklist

## Prerequisites

- [ ] **Python 3.11+** installed
- [ ] **Node.js 18+** installed
- [ ] **FFmpeg** installed: `ffmpeg -version`
- [ ] At least one AI provider key available

## Security

```bash
# Generate production secrets
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))"
```

- [ ] Set `SECRET_KEY` to generated value in `.env`
- [ ] Set `JWT_SECRET_KEY` to generated value in `.env`
- [ ] Set `ENVIRONMENT=production` in `.env`
- [ ] Verify CORS_ORIGINS is restrictive (no `*`)
- [ ] Run `pip-audit` for Python dependency vulnerabilities
- [ ] Run `npm audit` for Node dependency vulnerabilities

## Database

```bash
cd packages/core
alembic upgrade head
```

- [ ] Migrations applied successfully
- [ ] Database URL points to production database

## AI Providers

Set at least one of each in `.env`:

**LLM (required for screenplay parsing):**
- [ ] `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`

**Video Generation (required for shot generation):**
- [ ] `REPLICATE_API_TOKEN`, `FAL_API_KEY`, `RUNPOD_API_KEY`, or ComfyUI running

**Voice (optional, for TTS):**
- [ ] `ELEVENLABS_API_KEY`

## Verify

```bash
cd packages/core

# 1. App starts without error
python -m scenemachine &
sleep 3

# 2. Health check passes
curl http://localhost:8000/api/health

# 3. Readiness check passes (DB + FFmpeg)
curl http://localhost:8000/ready

# 4. Secret validation works
ENVIRONMENT=production python -c \
  "from scenemachine.config import get_settings, validate_secrets_for_production; validate_secrets_for_production(get_settings())"
```

## Build Desktop App

```bash
cd apps/desktop
npm install
npm run build
npm run package  # Creates distributable
```
