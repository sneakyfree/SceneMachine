#!/bin/bash
# Demo startup script for SceneMachine
# Starts both API and frontend servers

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🎬 SceneMachine Demo Startup"
echo "============================"

# Check if API is already running
if lsof -i :8000 > /dev/null 2>&1; then
    echo "⚠️  Port 8000 already in use. Killing existing process..."
    pkill -f "uvicorn.*8000" || true
    sleep 2
fi

# Check if frontend is already running
if lsof -i :51913 > /dev/null 2>&1; then
    echo "⚠️  Port 51913 already in use. Killing existing process..."
    pkill -f "vite.*51913" || true
    sleep 2
fi

# Initialize database
echo ""
echo "[1/4] Initializing database..."
cd "$ROOT_DIR/packages/core"
python -c "
from scenemachine.database import get_db_manager
import asyncio
async def init():
    db = get_db_manager()
    await db.initialize()
    await db.close()
asyncio.run(init())
"
echo "      ✅ Database ready"

# Seed demo data
echo ""
echo "[2/4] Seeding demo data..."
python -m scenemachine.seeds.demo_project 2>/dev/null || echo "      ⚠️  Demo seed skipped (may already exist)"
echo "      ✅ Demo data ready"

# Start API server
echo ""
echo "[3/4] Starting API server on :8000..."
uvicorn scenemachine.api.app:app --host 0.0.0.0 --port 8000 > /tmp/scenemachine-api.log 2>&1 &
API_PID=$!
sleep 3

# Verify API is running
if curl -s http://localhost:8000/health > /dev/null; then
    echo "      ✅ API server running (PID: $API_PID)"
else
    echo "      ❌ API server failed to start. Check /tmp/scenemachine-api.log"
    exit 1
fi

# Start frontend server
echo ""
echo "[4/4] Starting frontend on :51913..."
cd "$ROOT_DIR/apps/desktop"
npm run dev > /tmp/scenemachine-frontend.log 2>&1 &
FRONTEND_PID=$!
sleep 5

# Verify frontend is running
if lsof -i :51913 > /dev/null 2>&1; then
    echo "      ✅ Frontend running (PID: $FRONTEND_PID)"
else
    echo "      ❌ Frontend failed to start. Check /tmp/scenemachine-frontend.log"
    exit 1
fi

echo ""
echo "============================"
echo "🚀 SceneMachine is ready!"
echo ""
echo "   Frontend: http://localhost:51913"
echo "   API:      http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "   Logs:"
echo "     API:      /tmp/scenemachine-api.log"
echo "     Frontend: /tmp/scenemachine-frontend.log"
echo ""
echo "   To stop: pkill -f uvicorn && pkill -f vite"
echo "============================"
