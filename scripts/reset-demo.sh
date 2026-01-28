#!/bin/bash
# Reset demo data to clean state
# Use this to restore demo environment before investor presentation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🔄 SceneMachine Demo Reset"
echo "=========================="

cd "$ROOT_DIR/packages/core"

# Delete existing database
echo "[1/3] Deleting database..."
rm -f data/scenemachine.db
echo "      ✅ Database cleared"

# Reinitialize database
echo "[2/3] Rebuilding database..."
python -c "
from scenemachine.database import get_db_manager
import asyncio
async def init():
    db = get_db_manager()
    await db.initialize()
    await db.close()
asyncio.run(init())
"
echo "      ✅ Database rebuilt"

# Seed all demo data
echo "[3/3] Seeding demo data..."
python -c "
import asyncio
from scenemachine.database import get_db_manager
from scenemachine.seeds.performers import seed_performers
from scenemachine.seeds.demo_project import seed_demo_project

async def seed_all():
    db = get_db_manager()
    await db.initialize()
    
    async with db.session() as session:
        await seed_performers(session, force=True)
        await seed_demo_project(session, force=True)
    
    await db.close()

asyncio.run(seed_all())
"
echo "      ✅ Demo data seeded"

echo ""
echo "=========================="
echo "✅ Demo reset complete!"
echo ""
echo "   Ready for investor demo."
echo "   Run ./scripts/start-demo.sh to start servers."
echo "=========================="
