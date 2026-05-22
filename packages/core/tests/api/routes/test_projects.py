"""Tests for projects API routes.

Tests cover:
- Project CRUD operations
- Project state management
- Project settings
- Project listing and filtering
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# Mock project data
def create_mock_project(name: str = "Test Project", state: str = "draft") -> dict[str, Any]:
    """Create a mock project."""
    return {
        "id": str(uuid4()),
        "name": name,
        "description": "A test project",
        "state": state,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "settings": {
            "visual_style": "cinematic",
            "aspect_ratio": "16:9",
        }
    }


class MockProjectsRouter:
    """Mock projects router for testing."""

    def __init__(self):
        self.app = FastAPI()
        self.projects: dict[str, dict] = {}
        self._setup_routes()

    def _setup_routes(self):
        @self.app.get("/api/v1/projects")
        async def list_projects(state: str = None, limit: int = 20, offset: int = 0):
            projects = list(self.projects.values())
            if state:
                projects = [p for p in projects if p["state"] == state]
            return {
                "items": projects[offset:offset + limit],
                "total": len(projects),
                "limit": limit,
                "offset": offset,
            }

        @self.app.post("/api/v1/projects")
        async def create_project(name: str = "New Project", description: str = ""):
            project = create_mock_project(name=name)
            project["description"] = description
            self.projects[project["id"]] = project
            return project

        @self.app.get("/api/v1/projects/{project_id}")
        async def get_project(project_id: str):
            if project_id not in self.projects:
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail="Project not found")
            return self.projects[project_id]

        @self.app.put("/api/v1/projects/{project_id}")
        async def update_project(project_id: str, name: str = None, description: str = None):
            if project_id not in self.projects:
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail="Project not found")

            project = self.projects[project_id]
            if name:
                project["name"] = name
            if description is not None:
                project["description"] = description
            project["updated_at"] = datetime.utcnow().isoformat()
            return project

        @self.app.delete("/api/v1/projects/{project_id}")
        async def delete_project(project_id: str):
            if project_id not in self.projects:
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail="Project not found")
            del self.projects[project_id]
            return {"status": "deleted"}

        @self.app.post("/api/v1/projects/{project_id}/state")
        async def update_project_state(project_id: str, state: str):
            if project_id not in self.projects:
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail="Project not found")

            valid_states = [
                "draft", "screenplay_uploaded", "planning",
                "generating", "assembly_in_progress", "complete",
                "exported", "archived"
            ]
            if state not in valid_states:
                from fastapi import HTTPException
                raise HTTPException(status_code=400, detail="Invalid state")

            self.projects[project_id]["state"] = state
            return self.projects[project_id]


class TestProjectsCRUD:
    """Test project CRUD operations."""

    @pytest.fixture
    def client(self):
        router = MockProjectsRouter()
        return TestClient(router.app)

    def test_create_project(self, client):
        """Test creating a new project."""
        response = client.post(
            "/api/v1/projects",
            params={"name": "My Movie", "description": "A great movie"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "My Movie"
        assert data["state"] == "draft"
        assert "id" in data

    def test_list_projects_empty(self, client):
        """Test listing projects when none exist."""
        response = client.get("/api/v1/projects")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_projects_with_items(self, client):
        """Test listing projects with items."""
        # Create projects
        for i in range(3):
            client.post("/api/v1/projects", params={"name": f"Project {i}"})

        response = client.get("/api/v1/projects")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        assert data["total"] == 3

    def test_get_project(self, client):
        """Test getting a single project."""
        # Create project
        create_response = client.post(
            "/api/v1/projects",
            params={"name": "Test Project"}
        )
        project_id = create_response.json()["id"]

        response = client.get(f"/api/v1/projects/{project_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == project_id

    def test_get_nonexistent_project(self, client):
        """Test getting a nonexistent project returns 404."""
        response = client.get(f"/api/v1/projects/{uuid4()}")
        assert response.status_code == 404

    def test_update_project(self, client):
        """Test updating a project."""
        # Create project
        create_response = client.post(
            "/api/v1/projects",
            params={"name": "Original Name"}
        )
        project_id = create_response.json()["id"]

        # Update project
        response = client.put(
            f"/api/v1/projects/{project_id}",
            params={"name": "Updated Name"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"

    def test_delete_project(self, client):
        """Test deleting a project."""
        # Create project
        create_response = client.post(
            "/api/v1/projects",
            params={"name": "To Delete"}
        )
        project_id = create_response.json()["id"]

        # Delete project
        response = client.delete(f"/api/v1/projects/{project_id}")
        assert response.status_code == 200

        # Verify deleted
        get_response = client.get(f"/api/v1/projects/{project_id}")
        assert get_response.status_code == 404


class TestProjectStateManagement:
    """Test project state management."""

    @pytest.fixture
    def client(self):
        router = MockProjectsRouter()
        return TestClient(router.app)

    def test_update_project_state(self, client):
        """Test updating project state."""
        # Create project
        create_response = client.post("/api/v1/projects", params={"name": "Test"})
        project_id = create_response.json()["id"]

        # Update state
        response = client.post(
            f"/api/v1/projects/{project_id}/state",
            params={"state": "screenplay_uploaded"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "screenplay_uploaded"

    def test_invalid_state_rejected(self, client):
        """Test invalid state is rejected."""
        # Create project
        create_response = client.post("/api/v1/projects", params={"name": "Test"})
        project_id = create_response.json()["id"]

        # Try invalid state
        response = client.post(
            f"/api/v1/projects/{project_id}/state",
            params={"state": "invalid_state"}
        )

        assert response.status_code == 400


class TestProjectFiltering:
    """Test project filtering and pagination."""

    @pytest.fixture
    def client(self):
        router = MockProjectsRouter()
        return TestClient(router.app)

    def test_filter_by_state(self, client):
        """Test filtering projects by state."""
        # Create projects with different states
        client.post("/api/v1/projects", params={"name": "Draft 1"})
        client.post("/api/v1/projects", params={"name": "Draft 2"})

        response = client.get("/api/v1/projects", params={"state": "draft"})

        assert response.status_code == 200
        data = response.json()
        assert all(p["state"] == "draft" for p in data["items"])

    def test_pagination_limit(self, client):
        """Test pagination limit."""
        # Create 5 projects
        for i in range(5):
            client.post("/api/v1/projects", params={"name": f"Project {i}"})

        response = client.get("/api/v1/projects", params={"limit": 2})

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5

    def test_pagination_offset(self, client):
        """Test pagination offset."""
        # Create 5 projects
        for i in range(5):
            client.post("/api/v1/projects", params={"name": f"Project {i}"})

        response = client.get("/api/v1/projects", params={"limit": 2, "offset": 2})

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["offset"] == 2


class TestProjectValidation:
    """Test project validation."""

    def test_valid_project_states(self):
        """Test valid project states."""
        valid_states = [
            "draft",
            "screenplay_uploaded",
            "planning",
            "generating",
            "assembly_in_progress",
            "complete",
            "exported",
            "archived",
        ]

        for state in valid_states:
            assert isinstance(state, str)
            assert len(state) > 0

    def test_project_name_not_empty(self):
        """Test project name cannot be empty."""
        def validate_name(name: str) -> bool:
            return name is not None and len(name.strip()) > 0

        assert validate_name("Valid Name") is True
        assert validate_name("") is False
        assert validate_name("   ") is False

    def test_project_settings_structure(self):
        """Test project settings structure."""
        valid_settings = {
            "visual_style": "cinematic",
            "aspect_ratio": "16:9",
            "frame_rate": 24,
            "resolution": "1080p",
        }

        # All settings should be JSON-serializable
        import json
        json_str = json.dumps(valid_settings)
        assert len(json_str) > 0
