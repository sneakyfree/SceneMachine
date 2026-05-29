"""
Authorization tests for the Screenplays API ownership model.

A screenplay inherits its parent project's owner. A *different* authenticated
user must not be able to delete it (403); unowned projects and unauthenticated
(desktop/IPC) callers stay allowed for back-compat. Mirrors
test_projects_api_authz.py.
"""

import uuid
from types import SimpleNamespace

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from scenemachine.api.app import create_app
from scenemachine.api.dependencies import get_db
from scenemachine.auth.dependencies import get_optional_user
from scenemachine.database import get_session
from scenemachine.models import Screenplay


def _user():
    return SimpleNamespace(id=uuid.uuid4())


@pytest_asyncio.fixture
async def app_and_session(db_session):
    app = create_app()
    # projects route uses get_db; screenplay route uses get_session — override both.
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_session] = lambda: db_session
    yield app, db_session
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app_and_session):
    app, _ = app_and_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        await c.get("/api/v1/projects")  # prime CSRF cookie
        yield c


def _csrf(client):
    return {"X-CSRF-Token": client.cookies.get("csrf_token", "")}


def _as_user(app, user):
    app.dependency_overrides[get_optional_user] = lambda: user


def _as_anon(app):
    app.dependency_overrides[get_optional_user] = lambda: None


async def _make_owned_project(client, app, owner):
    _as_user(app, owner)
    resp = await client.post("/api/v1/projects", json={"name": "P"}, headers=_csrf(client))
    assert resp.status_code == 201, resp.text
    return uuid.UUID(resp.json()["id"])


async def _seed_screenplay(session, project_id):
    sp = Screenplay(
        project_id=project_id,
        original_filename="s.fountain",
        original_format="fountain",
        file_hash="0" * 64,
        original_file_path="/tmp/s.fountain",
    )
    session.add(sp)
    await session.flush()
    sp_id = sp.id
    await session.commit()
    return sp_id


async def _delete(client, sp_id):
    return await client.delete(
        f"/api/v1/screenplays/{sp_id}", headers=_csrf(client)
    )


async def test_delete_screenplay_rejects_non_owner(app_and_session, client):
    app, session = app_and_session
    owner = _user()
    pid = await _make_owned_project(client, app, owner)
    sp_id = await _seed_screenplay(session, pid)
    _as_user(app, _user())  # different authenticated user
    resp = await _delete(client, sp_id)
    assert resp.status_code == 403


async def test_delete_screenplay_allows_owner(app_and_session, client):
    app, session = app_and_session
    owner = _user()
    pid = await _make_owned_project(client, app, owner)
    sp_id = await _seed_screenplay(session, pid)
    _as_user(app, owner)
    resp = await _delete(client, sp_id)
    assert resp.status_code == 204


async def test_delete_screenplay_nonexistent_returns_404(app_and_session, client):
    app, _ = app_and_session
    _as_user(app, _user())
    resp = await _delete(client, uuid.uuid4())
    assert resp.status_code == 404
