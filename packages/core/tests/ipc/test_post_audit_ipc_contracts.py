"""Regression tests for the IPC handlers added/fixed on 2026-05-14.

These tests lock in the four IPC contract fixes that closed exec-summary
items 1, 2, 3, and 5 from the DNA-strand audit:

  PR #48  pipeline.start / pipeline.status aliases
  PR #49  blockers.analyze + blockers.apply_fix handlers
  PR #50  snapshots.list / snapshots.get / snapshots.compare end-to-end
  PR #51  ipAdapter.getSettings / ipAdapter.updateSettings with validation

Each test pins down the exact contract the renderer relies on. If a
future refactor renames a method, deletes a handler, or removes the
``feedback_no_silent_fallbacks``-aligned validation behavior, these
tests fail loudly instead of letting the bugs come back as silent UI
failures.
"""
from __future__ import annotations

import pytest

from scenemachine.ipc.handlers import register_handlers
from scenemachine.ipc.server import IPCServer


@pytest.fixture
def ipc_server(tmp_path):
    server = IPCServer(str(tmp_path / "test.sock"))
    register_handlers(server)
    return server


# ----------------------------------------------------------------------
# PR #48 — pipeline.start / pipeline.status aliases
# ----------------------------------------------------------------------

class TestPipelineIpcAliases:
    """The renderer's production-dashboard.tsx calls these names. The
    backend canonical names are ``pipeline.run`` and ``pipeline.getStatus``.
    Both pairs must point to the same handler so future devs can't
    accidentally divorce them."""

    def test_pipeline_start_is_registered(self, ipc_server):
        assert "pipeline.start" in ipc_server.handlers

    def test_pipeline_status_is_registered(self, ipc_server):
        assert "pipeline.status" in ipc_server.handlers

    def test_canonical_names_still_registered(self, ipc_server):
        assert "pipeline.run" in ipc_server.handlers
        assert "pipeline.getStatus" in ipc_server.handlers

    def test_start_and_run_share_handler(self, ipc_server):
        assert ipc_server.handlers["pipeline.start"] is ipc_server.handlers["pipeline.run"]

    def test_status_and_getStatus_share_handler(self, ipc_server):
        assert ipc_server.handlers["pipeline.status"] is ipc_server.handlers["pipeline.getStatus"]


# ----------------------------------------------------------------------
# PR #49 — blockers.analyze / blockers.apply_fix
# ----------------------------------------------------------------------

class TestBlockersIpcHandlers:
    """Renderer's blockers-panel.tsx invokes these. Engine is real;
    handlers must be registered with the right signature."""

    def test_blockers_analyze_registered(self, ipc_server):
        assert "blockers.analyze" in ipc_server.handlers

    def test_blockers_apply_fix_registered(self, ipc_server):
        assert "blockers.apply_fix" in ipc_server.handlers

    @pytest.mark.asyncio
    async def test_apply_fix_is_honest_acknowledgement(self, ipc_server):
        """Per the no-silent-fallbacks rule, apply_fix must return a
        structured response that tells the caller the action was
        acknowledged but not programmatically applied (since most
        unlocker actions are user-side)."""
        h = ipc_server.handlers["blockers.apply_fix"]
        result = await h(blocker_id="blk-1", fix_id="fix-a")
        assert result["acknowledged"] is True
        assert result["programmatic"] is False
        assert "message" in result
        assert result["blocker_id"] == "blk-1"
        assert result["fix_id"] == "fix-a"


# ----------------------------------------------------------------------
# PR #50 — snapshots end-to-end
# ----------------------------------------------------------------------

class TestSnapshotsIpcContract:
    """Audit view (explainability.tsx) calls snapshots.list. Compare
    used to have wrong signature. Both must work after PR #50."""

    def test_snapshots_list_registered(self, ipc_server):
        assert "snapshots.list" in ipc_server.handlers

    def test_snapshots_get_registered(self, ipc_server):
        assert "snapshots.get" in ipc_server.handlers

    def test_snapshots_compare_registered(self, ipc_server):
        assert "snapshots.compare" in ipc_server.handlers

    def test_pipeline_has_snapshot_helper(self):
        """Auto-create hook lives in ProductionPipeline._snapshot_stage.
        Without this method the run() loop's five snapshot calls would
        AttributeError; the test catches accidental deletion."""
        from scenemachine.services.production_pipeline import ProductionPipeline
        assert hasattr(ProductionPipeline, "_snapshot_stage"), (
            "ProductionPipeline._snapshot_stage was the auto-create hook "
            "wired in PR #50; deleting it silently drops the audit trail."
        )

    def test_pipeline_run_calls_snapshot_hook(self):
        """Source-level assertion that the run() method invokes the
        snapshot hook at the documented stage boundaries."""
        import inspect
        from scenemachine.services.production_pipeline import ProductionPipeline
        src = inspect.getsource(ProductionPipeline.run)
        # Five documented snapshot points
        assert src.count("await self._snapshot_stage(") >= 5, (
            "PR #50 wired snapshot creation at >=5 stage boundaries; "
            "fewer calls indicates the audit trail is incomplete."
        )


# ----------------------------------------------------------------------
# PR #51 — ipAdapter.getSettings / ipAdapter.updateSettings
# ----------------------------------------------------------------------

class TestIpAdapterIpcContract:
    """Renderer's ip-adapter-controls.tsx was using fetch() against a
    non-running HTTP endpoint. The IPC handlers added in PR #51 must
    persist updates within a session AND validate inputs (no silent
    coercion of bad data)."""

    def test_get_settings_registered(self, ipc_server):
        assert "ipAdapter.getSettings" in ipc_server.handlers

    def test_update_settings_registered(self, ipc_server):
        assert "ipAdapter.updateSettings" in ipc_server.handlers

    @pytest.mark.asyncio
    async def test_default_settings_shape(self, ipc_server):
        get_h = ipc_server.handlers["ipAdapter.getSettings"]
        result = await get_h()
        assert "mode" in result
        assert "strength" in result
        assert "available_modes" in result
        assert result["mode"] in result["available_modes"]
        assert 0.0 <= result["strength"] <= 1.0

    @pytest.mark.asyncio
    async def test_update_persists_within_session(self, ipc_server):
        get_h = ipc_server.handlers["ipAdapter.getSettings"]
        upd_h = ipc_server.handlers["ipAdapter.updateSettings"]
        # Roundtrip a valid update
        await upd_h(mode="face_only", strength=0.42)
        result = await get_h()
        assert result["mode"] == "face_only"
        assert result["strength"] == pytest.approx(0.42)

    @pytest.mark.asyncio
    async def test_invalid_mode_raises(self, ipc_server):
        upd_h = ipc_server.handlers["ipAdapter.updateSettings"]
        with pytest.raises(ValueError, match="invalid IPAdapter mode"):
            await upd_h(mode="this-does-not-exist")

    @pytest.mark.asyncio
    async def test_out_of_range_strength_raises(self, ipc_server):
        upd_h = ipc_server.handlers["ipAdapter.updateSettings"]
        with pytest.raises(ValueError, match=r"strength must be in \[0\.0, 1\.0\]"):
            await upd_h(strength=1.5)
        with pytest.raises(ValueError, match=r"strength must be in \[0\.0, 1\.0\]"):
            await upd_h(strength=-0.1)
