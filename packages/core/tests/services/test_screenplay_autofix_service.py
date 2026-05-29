"""
DB-backed test for ScreenplayService.auto_fix_screenplay — verifies the full
load → fix → persist path that backs the P0-5 IPC handlers.
"""

import uuid

import pytest_asyncio

from scenemachine.models.screenplay import Screenplay
from scenemachine.services.screenplay import ScreenplayService


@pytest_asyncio.fixture
async def seeded_screenplay(db_session):
    sp = Screenplay(
        project_id=uuid.uuid4(),
        original_filename="s.fountain",
        original_format="fountain",
        file_hash="0" * 64,
        original_file_path="/tmp/s.fountain",
    )
    sp.parsed_content = {
        "elements": [
            {"type": "scene_heading", "text": "the kitchen"},  # missing slugline
            {"type": "character", "character_name": "", "text": ""},  # unnamed
            {"type": "scene_heading", "text": "INT. OFFICE - DAY"},  # fine
        ]
    }
    db_session.add(sp)
    await db_session.flush()
    sp_id = sp.id
    await db_session.commit()
    return sp_id


async def test_auto_fix_applies_and_persists(db_session, seeded_screenplay):
    svc = ScreenplayService(db_session)
    result = await svc.auto_fix_screenplay(seeded_screenplay)
    assert result["success"] is True
    assert result["fixedCount"] == 2  # slugline + unnamed character

    # Re-load to confirm persistence.
    refreshed = await svc._get_screenplay(seeded_screenplay)
    elements = refreshed.parsed_content["elements"]
    assert elements[0]["text"] == "INT. the kitchen"
    assert elements[1]["character_name"] == "CHARACTER 1"


async def test_auto_fix_unparsed_returns_unsuccessful(db_session):
    sp = Screenplay(
        project_id=uuid.uuid4(),
        original_filename="s.fountain",
        original_format="fountain",
        file_hash="1" * 64,
        original_file_path="/tmp/s2.fountain",
    )
    sp.parsed_content = None
    db_session.add(sp)
    await db_session.flush()
    sp_id = sp.id
    await db_session.commit()

    result = await ScreenplayService(db_session).auto_fix_screenplay(sp_id)
    assert result["success"] is False
    assert result["fixedCount"] == 0
