"""Regression tests for alembic migration 007_add_lipsync_jobs.

Guards against the original P0 where the LipsyncJob model existed but no
migration created its table — fresh DBs failed with "relation lipsync_jobs
does not exist" the moment any IPC lipsync handler ran.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


def _alembic_config_for(db_path: Path) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_INI.parent / "alembic"))
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    return cfg


def test_migration_007_is_wired_into_chain() -> None:
    """Migration 007 must descend from 006_accessibility and be a head."""
    cfg = Config(str(ALEMBIC_INI))
    sd = ScriptDirectory.from_config(cfg)

    rev = sd.get_revision("007_lipsync_jobs")
    assert rev is not None, "migration 007_lipsync_jobs must be present"
    assert rev.down_revision == "006_accessibility"
    assert "007_lipsync_jobs" in sd.get_heads()


def test_migration_007_upgrade_downgrade_cycle(tmp_path: Path) -> None:
    """Upgrade → downgrade → re-upgrade leaves the table in the expected state."""
    db_path = tmp_path / "sm_mig007.db"
    cfg = _alembic_config_for(db_path)

    # Stamp the prereq state — we test 007 in isolation because the full chain
    # uses ALTER constraints that sqlite can't handle (migration 004 issue).
    # We stub the FK targets so 007's foreign keys reference real tables.
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        cur.execute(
            "CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY)"
        )
        cur.execute("INSERT INTO alembic_version VALUES ('006_accessibility')")
        cur.execute("CREATE TABLE shots (id BLOB PRIMARY KEY)")
        cur.execute("CREATE TABLE assets (id BLOB PRIMARY KEY)")
        con.commit()

    # Upgrade to 007 — must create lipsync_jobs.
    command.upgrade(cfg, "007_lipsync_jobs")
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='lipsync_jobs'"
        )
        assert cur.fetchone() is not None, "lipsync_jobs must exist after upgrade"

        cur.execute("PRAGMA table_info(lipsync_jobs)")
        cols = {row[1] for row in cur.fetchall()}
        expected = {
            "id",
            "created_at",
            "updated_at",
            "shot_id",
            "video_asset_id",
            "audio_asset_id",
            "output_asset_id",
            "status",
            "progress_percent",
            "progress_message",
            "error_message",
            "provider",
            "output_path",
            "completed_at",
        }
        missing = expected - cols
        assert not missing, f"lipsync_jobs missing expected columns: {missing}"

        cur.execute("PRAGMA index_list(lipsync_jobs)")
        idx_names = {row[1] for row in cur.fetchall()}
        for required_idx in (
            "ix_lipsync_jobs_shot_id",
            "ix_lipsync_jobs_video_asset_id",
            "ix_lipsync_jobs_audio_asset_id",
            "ix_lipsync_jobs_status",
        ):
            assert required_idx in idx_names, f"missing index {required_idx}"

    # Downgrade — must drop the table cleanly.
    command.downgrade(cfg, "006_accessibility")
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='lipsync_jobs'"
        )
        assert cur.fetchone() is None, "lipsync_jobs must be gone after downgrade"

    # Re-upgrade — must succeed (proves downgrade left a clean slate).
    command.upgrade(cfg, "007_lipsync_jobs")
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='lipsync_jobs'"
        )
        assert cur.fetchone() is not None, "lipsync_jobs must re-create cleanly"


@pytest.fixture(autouse=True)
def _clean_database_url_env() -> None:
    """Don't leak DATABASE_URL between tests."""
    saved = os.environ.get("DATABASE_URL")
    yield
    if saved is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = saved
