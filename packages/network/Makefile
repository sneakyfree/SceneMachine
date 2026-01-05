# SceneMachine Network - Makefile
# Common commands for development and deployment

.PHONY: help install dev up down logs migrate test lint clean build

# Default target
help:
	@echo "SceneMachine Network - Available Commands:"
	@echo ""
	@echo "Development:"
	@echo "  make install     - Install Python dependencies"
	@echo "  make dev         - Start all services in development mode"
	@echo "  make up          - Start Docker Compose services"
	@echo "  make down        - Stop Docker Compose services"
	@echo "  make logs        - View Docker Compose logs"
	@echo ""
	@echo "Database:"
	@echo "  make migrate     - Run database migrations"
	@echo "  make db-reset    - Reset database (WARNING: deletes all data)"
	@echo ""
	@echo "Testing:"
	@echo "  make test        - Run all tests"
	@echo "  make test-unit   - Run unit tests only"
	@echo "  make lint        - Run linter"
	@echo ""
	@echo "Build:"
	@echo "  make build       - Build all Docker images"
	@echo "  make clean       - Remove build artifacts"
	@echo ""
	@echo "Production:"
	@echo "  make prod        - Start in production mode"

# =============================================================================
# DEVELOPMENT
# =============================================================================

install:
	pip install -r requirements.txt

dev:
	@echo "Starting development services..."
	docker-compose up -d postgres redis minio mailhog
	@echo "Waiting for services to be ready..."
	sleep 5
	@echo "Services ready. Run individual services with:"
	@echo "  cd services/auth && uvicorn main:app --reload --port 8001"
	@echo "  cd services/content && uvicorn main:app --reload --port 8002"
	@echo "  etc."

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

logs-service:
	@read -p "Service name: " service; \
	docker-compose logs -f $$service

# =============================================================================
# DATABASE
# =============================================================================

migrate:
	cd migrations && alembic upgrade head

migrate-create:
	@read -p "Migration message: " msg; \
	cd migrations && alembic revision --autogenerate -m "$$msg"

migrate-down:
	cd migrations && alembic downgrade -1

db-reset:
	@echo "WARNING: This will delete all data!"
	@read -p "Are you sure? [y/N] " confirm; \
	if [ "$$confirm" = "y" ]; then \
		docker-compose down -v postgres; \
		docker-compose up -d postgres; \
		sleep 5; \
		make migrate; \
	fi

# =============================================================================
# TESTING
# =============================================================================

test:
	pytest tests/ -v

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

test-coverage:
	pytest tests/ -v --cov=services --cov=shared --cov-report=html
	@echo "Coverage report: htmlcov/index.html"

lint:
	ruff check .
	mypy services/ shared/ --ignore-missing-imports

format:
	ruff format .

# =============================================================================
# BUILD
# =============================================================================

build:
	docker-compose build

build-no-cache:
	docker-compose build --no-cache

# Build individual services
build-auth:
	docker build -t smn-auth -f services/auth/Dockerfile .

build-content:
	docker build -t smn-content -f services/content/Dockerfile .

build-web:
	docker build -t smn-web -f web/Dockerfile web/

# =============================================================================
# PRODUCTION
# =============================================================================

prod:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

prod-down:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

# =============================================================================
# CLEANUP
# =============================================================================

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf htmlcov .coverage 2>/dev/null || true

clean-docker:
	docker-compose down -v --rmi local
	docker system prune -f

# =============================================================================
# CELERY
# =============================================================================

celery-worker:
	celery -A services.content.tasks worker --loglevel=info

celery-beat:
	celery -A services.content.tasks beat --loglevel=info

celery-flower:
	celery -A services.content.tasks flower --port=5555

# =============================================================================
# UTILITIES
# =============================================================================

shell:
	docker-compose exec postgres psql -U postgres -d scenemachine_network

redis-cli:
	docker-compose exec redis redis-cli

minio-console:
	@echo "MinIO Console: http://localhost:9001"
	@echo "Login: minioadmin / minioadmin"

mailhog:
	@echo "Mailhog UI: http://localhost:8025"

# Create initial bucket in MinIO
setup-minio:
	@echo "Creating bucket in MinIO..."
	docker-compose exec minio mc alias set local http://localhost:9000 minioadmin minioadmin
	docker-compose exec minio mc mb local/scenemachine-network --ignore-existing
	@echo "Bucket created!"

# Generate secret key
generate-secret:
	@openssl rand -hex 32
