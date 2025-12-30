# SceneMachine Production Deployment Guide

This guide covers building, packaging, and deploying SceneMachine for production use.

## Prerequisites

### System Requirements

- **Node.js**: v18.0.0 or higher
- **Python**: 3.10 or higher
- **PostgreSQL**: 14 or higher (production) or SQLite (development)
- **FFmpeg**: Required for video assembly
- **OS**: Windows 10+, macOS 11+, or Linux (Ubuntu 20.04+)

### Development Tools

```bash
# Install Node.js dependencies manager
npm install -g pnpm

# Install Python package manager
pip install poetry
```

## Project Setup

### 1. Clone and Install Dependencies

```bash
# Clone the repository
git clone https://github.com/scenemachine/scenemachine.git
cd scenemachine

# Install frontend dependencies
cd apps/desktop
pnpm install

# Install backend dependencies
cd ../../packages/core
poetry install
```

### 2. Environment Configuration

Create environment files for each component:

#### Backend Configuration (`packages/core/.env`)

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/scenemachine

# Security
SECRET_KEY=your-secure-secret-key-min-32-chars
ENCRYPTION_KEY=your-fernet-encryption-key

# API Keys (optional, can be set in app)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
REPLICATE_API_TOKEN=r8_...
ELEVENLABS_API_KEY=...

# Storage
DATA_DIR=/path/to/data
UPLOAD_DIR=/path/to/uploads
OUTPUT_DIR=/path/to/outputs

# Server
HOST=127.0.0.1
PORT=8000
ENVIRONMENT=production
LOG_LEVEL=INFO
```

#### Frontend Configuration (`apps/desktop/.env`)

```env
# Backend connection
VITE_BACKEND_URL=http://localhost:8000
VITE_IPC_SOCKET_PATH=/tmp/scenemachine.sock

# Feature flags
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_TELEMETRY=false
```

## Building for Production

### Backend Build

```bash
cd packages/core

# Install production dependencies only
poetry install --no-dev

# Run database migrations
poetry run alembic upgrade head

# Test the build
poetry run python -m scenemachine.main --help
```

### Frontend Build

```bash
cd apps/desktop

# Build the renderer
pnpm run build

# Package for current platform
pnpm run package

# Package for specific platform
pnpm run package:win    # Windows
pnpm run package:mac    # macOS
pnpm run package:linux  # Linux
```

### Build Outputs

After packaging, installers are created in:

```
apps/desktop/release/
├── SceneMachine-1.0.0-win.exe      # Windows installer
├── SceneMachine-1.0.0.dmg          # macOS installer
├── SceneMachine-1.0.0.AppImage     # Linux AppImage
└── SceneMachine-1.0.0.deb          # Debian package
```

## Deployment Options

### Option 1: Standalone Desktop Application

The default deployment bundles the Python backend with the Electron app.

#### Windows

1. Run the NSIS installer (`.exe`)
2. Follow installation wizard
3. Application installs to `%LOCALAPPDATA%/SceneMachine`
4. Data stored in `%APPDATA%/SceneMachine`

#### macOS

1. Mount the `.dmg` file
2. Drag SceneMachine to Applications
3. On first run, right-click and select "Open" to bypass Gatekeeper
4. Data stored in `~/Library/Application Support/SceneMachine`

#### Linux

```bash
# AppImage (universal)
chmod +x SceneMachine-1.0.0.AppImage
./SceneMachine-1.0.0.AppImage

# Debian/Ubuntu
sudo dpkg -i SceneMachine-1.0.0.deb
sudo apt-get install -f  # Fix dependencies if needed

# Data stored in ~/.config/scenemachine
```

### Option 2: Separate Backend Server

For team deployments or advanced configurations, run the backend separately.

#### Backend Server Setup

```bash
# Production server with Uvicorn
cd packages/core
poetry run uvicorn scenemachine.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --ssl-keyfile=/path/to/key.pem \
  --ssl-certfile=/path/to/cert.pem

# Or with Gunicorn (recommended for production)
poetry run gunicorn scenemachine.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  -b 0.0.0.0:8000 \
  --certfile=/path/to/cert.pem \
  --keyfile=/path/to/key.pem
```

#### Systemd Service

Create `/etc/systemd/system/scenemachine.service`:

```ini
[Unit]
Description=SceneMachine Backend Server
After=network.target postgresql.service

[Service]
Type=simple
User=scenemachine
Group=scenemachine
WorkingDirectory=/opt/scenemachine
Environment="PATH=/opt/scenemachine/.venv/bin"
ExecStart=/opt/scenemachine/.venv/bin/gunicorn scenemachine.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  -b 127.0.0.1:8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable scenemachine
sudo systemctl start scenemachine
sudo systemctl status scenemachine
```

### Option 3: Docker Deployment

#### Docker Compose

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./packages/core
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/scenemachine
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - ./data:/app/data
    depends_on:
      - db

  db:
    image: postgres:14-alpine
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=scenemachine
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

#### Build and Run

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

## Database Setup

### PostgreSQL Production Setup

```sql
-- Create database and user
CREATE USER scenemachine WITH PASSWORD 'secure_password';
CREATE DATABASE scenemachine OWNER scenemachine;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE scenemachine TO scenemachine;

-- Enable UUID extension
\c scenemachine
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

### Run Migrations

```bash
cd packages/core

# Generate new migration (development only)
poetry run alembic revision --autogenerate -m "description"

# Apply migrations
poetry run alembic upgrade head

# Rollback one migration
poetry run alembic downgrade -1

# View migration history
poetry run alembic history
```

## SSL/TLS Configuration

### Self-Signed Certificate (Development)

```bash
openssl req -x509 -newkey rsa:4096 \
  -keyout key.pem -out cert.pem \
  -days 365 -nodes \
  -subj "/CN=localhost"
```

### Let's Encrypt (Production)

```bash
# Install certbot
sudo apt install certbot

# Obtain certificate
sudo certbot certonly --standalone -d scenemachine.yourdomain.com

# Certificates stored in /etc/letsencrypt/live/
```

## Monitoring and Logging

### Log Configuration

Configure logging in `packages/core/scenemachine/config.py`:

```python
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
        "json": {
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/var/log/scenemachine/app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "formatter": "json"
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console", "file"]
    }
}
```

### Health Checks

The backend exposes health check endpoints:

```bash
# Basic health check
curl http://localhost:8000/health

# Detailed system status
curl http://localhost:8000/api/v1/system/status

# Database connectivity
curl http://localhost:8000/api/v1/system/db-check
```

### Prometheus Metrics

Enable metrics endpoint in configuration:

```python
ENABLE_METRICS = True
METRICS_PORT = 9090
```

Access metrics at `http://localhost:9090/metrics`

## Security Hardening

### Firewall Rules

```bash
# Allow only necessary ports
sudo ufw allow 22/tcp     # SSH
sudo ufw allow 443/tcp    # HTTPS
sudo ufw allow 8000/tcp   # Backend (if exposed)
sudo ufw enable
```

### Environment Variables

Never commit secrets to version control. Use:

- Environment variables
- Secret management services (AWS Secrets Manager, HashiCorp Vault)
- Encrypted configuration files

### Database Security

```sql
-- Limit connection sources
ALTER SYSTEM SET listen_addresses = 'localhost';

-- Enable SSL
ALTER SYSTEM SET ssl = on;

-- Require SSL connections
ALTER SYSTEM SET ssl_min_protocol_version = 'TLSv1.2';
```

## Backup and Recovery

### Database Backup

```bash
# Full backup
pg_dump -h localhost -U scenemachine -F c -b -v \
  -f /backup/scenemachine_$(date +%Y%m%d).backup scenemachine

# Restore from backup
pg_restore -h localhost -U scenemachine -d scenemachine \
  -v /backup/scenemachine_20240101.backup
```

### Automated Backups (Cron)

```bash
# Add to crontab
0 2 * * * /opt/scenemachine/scripts/backup.sh >> /var/log/scenemachine/backup.log 2>&1
```

### Data Directory Backup

```bash
# Backup uploads and outputs
rsync -avz /opt/scenemachine/data/ /backup/scenemachine-data/
```

## Troubleshooting

### Common Issues

#### Backend Won't Start

```bash
# Check logs
journalctl -u scenemachine -f

# Verify database connection
psql -h localhost -U scenemachine -d scenemachine -c "SELECT 1;"

# Check port availability
ss -tlnp | grep 8000
```

#### IPC Connection Failed

```bash
# Check socket file exists (Unix)
ls -la /tmp/scenemachine.sock

# Check TCP port (Windows)
netstat -an | findstr 19847

# Verify backend is running
curl http://localhost:8000/health
```

#### Generation Failures

```bash
# Check API key configuration
poetry run python -c "from scenemachine.config import get_settings; print(get_settings().openai_api_key[:10])"

# Test external API connectivity
curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Performance Tuning

#### Database Optimization

```sql
-- Analyze tables
ANALYZE;

-- Create indexes for common queries
CREATE INDEX idx_projects_updated ON projects(updated_at DESC);
CREATE INDEX idx_shots_scene_id ON shots(scene_id);
CREATE INDEX idx_generation_jobs_status ON generation_jobs(status);
```

#### Backend Tuning

```python
# Increase connection pool
DATABASE_POOL_SIZE = 20
DATABASE_MAX_OVERFLOW = 10

# Adjust worker count based on CPU cores
WORKERS = multiprocessing.cpu_count() * 2 + 1
```

## Updates and Migrations

### Updating SceneMachine

```bash
# Stop the service
sudo systemctl stop scenemachine

# Backup database
pg_dump -F c scenemachine > /backup/pre-update.backup

# Pull latest code
git pull origin main

# Update dependencies
cd packages/core && poetry install
cd apps/desktop && pnpm install

# Run migrations
poetry run alembic upgrade head

# Rebuild frontend
pnpm run build

# Restart service
sudo systemctl start scenemachine
```

### Rollback Procedure

```bash
# Stop service
sudo systemctl stop scenemachine

# Restore database
pg_restore -c -d scenemachine /backup/pre-update.backup

# Checkout previous version
git checkout v1.0.0

# Reinstall dependencies
cd packages/core && poetry install
cd apps/desktop && pnpm install

# Restart
sudo systemctl start scenemachine
```

## Support

For additional support:

- GitHub Issues: https://github.com/scenemachine/scenemachine/issues
- Documentation: https://docs.scenemachine.ai
- Community Discord: https://discord.gg/scenemachine
