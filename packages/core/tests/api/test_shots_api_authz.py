"""
Authorization tests for the Shots API ownership model.

A shot inherits its scene's project owner (shot → scene → project). A
*different* authenticated user must not be able to delete it (403); unowned
projects and unauthenticated (desktop/IPC) callers stay allowed for
back-compat. Mirrors test_projects_api_authz.py / test_screenplay_api_authz.py.
"""

import uuid
from types import SimpleNamespace

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from scenemachine.api.app import create_app
from scenemachine.api.dependencies import get_db
from scenemachine.auth.dependencies import get_optional_user
from scenemachine.database import get_session
from scenemachine.models.scene import Scene, SceneType, TimeOfDay
from scenemachine.models.shot import Shot, ShotType


def _user():
    return SimpleNamespace(id=uuid.uuid4())


@pytest_asyncio.fixture
async def app_and_session(db_session):
    app = create_app()
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


async def _make_owned_project(client, app, owner):
    _as_user(app, owner)
    resp = await client.post("/api/v1/projects", json={"name": "P"}, headers=_csrf(client))
    assert resp.status_code == 201, resp.text
    return uuid.UUID(resp.json()["id"])


async def _seed_shot(session, project_id):
    scene = Scene(
        project_id=project_id,
        scene_number="1",
        sequence_number=1,
        scene_type=SceneType.INTERIOR,
        location="A room",
        time_of_day=TimeOfDay.DAY,
        raw_content="INT. A ROOM - DAY",
    )
    session.add(scene)
    await session.flush()
    shot = Shot(
        scene_id=scene.id,
        shot_number="1",
        sequence_number=1,
        shot_type=ShotType.ESTABLISHING,
        description="Wide establishing shot.",
    )
    session.add(shot)
    await session.flush()
    shot_id = shot.id
    await session.commit()
    return shot_id


async def _delete(client, shot_id):
    return await client.delete(
        f"/api/v1/scenes/shots/{shot_id}", headers=_csrf(client)
    )


async def test_delete_shot_rejects_non_owner(app_and_session, client):
    app, session = app_and_session
    owner = _user()
    pid = await _make_owned_project(client, app, owner)
    shot_id = await _seed_shot(session, pid)
    _as_user(app, _user())  # different authenticated user
    resp = await _delete(client, shot_id)
    assert resp.status_code == 403


async def test_delete_shot_allows_owner(app_and_session, client):
    app, session = app_and_session
    owner = _user()
    pid = await _make_owned_project(client, app, owner)
    shot_id = await _seed_shot(session, pid)
    _as_user(app, owner)
    resp = await _delete(client, shot_id)
    assert resp.status_code == 200


async def test_delete_shot_nonexistent_returns_404(app_and_session, client):
    app, _ = app_and_session
    _as_user(app, _user())
    resp = await _delete(client, uuid.uuid4())
    assert resp.status_code == 404
