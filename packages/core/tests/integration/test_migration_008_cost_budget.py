"""Regression tests for alembic migration 008_add_cost_budget_settings.

Closes P0-8: before this migration the desktop "Set Budget" button was
backed only by an in-memory `CostTrackingService._budget_limit` lost on
every IPC call. The budget never persisted; the cost dashboard always
re-rendered as "no budget set."
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

from alembic import command

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


def _alembic_config_for(db_path: Path) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_INI.parent / "alembic"))
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    return cfg


def test_migration_008_is_wired_into_chain() -> None:
    cfg = Config(str(ALEMBIC_INI))
    sd = ScriptDirectory.from_config(cfg)
    rev = sd.get_revision("008_cost_budget")
    assert rev is not None
    assert rev.down_revision == "007_lipsync_jobs"
    assert "008_cost_budget" in sd.get_heads()


def test_migration_008_upgrade_downgrade_cycle(tmp_path: Path) -> None:
    """Upgrade adds both columns; downgrade drops them; re-upgrade succeeds."""
    db_path = tmp_path / "sm_mig008.db"
    cfg = _alembic_config_for(db_path)

    # Stamp at 007 with a stub user_settings table (the only column 008 touches).
    # The full chain through 004 needs ALTER constraints sqlite can't do.
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY)")
        cur.execute("INSERT INTO alembic_version VALUES ('007_lipsync_jobs')")
        cur.execute("CREATE TABLE user_settings (id BLOB PRIMARY KEY, settings_key TEXT)")
        con.commit()

    command.upgrade(cfg, "008_cost_budget")
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("PRAGMA table_info(user_settings)")
        cols = {row[1] for row in cur.fetchall()}
        assert "cost_budget_limit_usd" in cols
        assert "cost_budget_period_days" in cols

    command.downgrade(cfg, "007_lipsync_jobs")
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("PRAGMA table_info(user_settings)")
        cols = {row[1] for row in cur.fetchall()}
        assert "cost_budget_limit_usd" not in cols
        assert "cost_budget_period_days" not in cols

    command.upgrade(cfg, "008_cost_budget")
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("PRAGMA table_info(user_settings)")
        cols = {row[1] for row in cur.fetchall()}
        assert "cost_budget_limit_usd" in cols
        assert "cost_budget_period_days" in cols


@pytest.fixture(autouse=True)
def _clean_database_url_env() -> None:
    saved = os.environ.get("DATABASE_URL")
    yield
    if saved is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = saved
