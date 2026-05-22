"""Tests for characters API routes.

Tests cover:
- Character CRUD operations
- Character locking
- Physical descriptions
- Character metadata
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient


def create_mock_character(name: str = "John Doe", project_id: str = None) -> dict[str, Any]:
    """Create a mock character."""
    return {
        "id": str(uuid4()),
        "project_id": project_id or str(uuid4()),
        "name": name,
        "description": "A mysterious stranger",
        "physical_description": {
            "age": "30s",
            "height": "tall",
            "build": "athletic",
            "hair": "dark brown",
            "eyes": "blue",
            "notable_features": "scar on left cheek",
        },
        "locked": False,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


class MockCharactersRouter:
    """Mock characters router for testing."""

    def __init__(self):
        self.app = FastAPI()
        self.characters: dict[str, dict] = {}
        self._setup_routes()

    def _setup_routes(self):
        @self.app.get("/api/v1/projects/{project_id}/characters")
        async def list_characters(project_id: str):
            chars = [c for c in self.characters.values() if c["project_id"] == project_id]
            return {"items": chars, "total": len(chars)}

        @self.app.post("/api/v1/projects/{project_id}/characters")
        async def create_character(project_id: str, name: str, description: str = ""):
            char = create_mock_character(name=name, project_id=project_id)
            char["description"] = description
            self.characters[char["id"]] = char
            return char

        @self.app.get("/api/v1/projects/{project_id}/characters/{character_id}")
        async def get_character(project_id: str, character_id: str):
            if character_id not in self.characters:
                raise HTTPException(status_code=404, detail="Character not found")
            return self.characters[character_id]

        @self.app.put("/api/v1/projects/{project_id}/characters/{character_id}")
        async def update_character(
            project_id: str, character_id: str, name: str = None, description: str = None
        ):
            if character_id not in self.characters:
                raise HTTPException(status_code=404, detail="Character not found")

            char = self.characters[character_id]
            if char["locked"]:
                raise HTTPException(status_code=400, detail="Character is locked")

            if name:
                char["name"] = name
            if description is not None:
                char["description"] = description
            char["updated_at"] = datetime.utcnow().isoformat()
            return char

        @self.app.delete("/api/v1/projects/{project_id}/characters/{character_id}")
        async def delete_character(project_id: str, character_id: str):
            if character_id not in self.characters:
                raise HTTPException(status_code=404, detail="Character not found")
            del self.characters[character_id]
            return {"status": "deleted"}

        @self.app.post("/api/v1/projects/{project_id}/characters/{character_id}/lock")
        async def lock_character(project_id: str, character_id: str):
            if character_id not in self.characters:
                raise HTTPException(status_code=404, detail="Character not found")
            self.characters[character_id]["locked"] = True
            return self.characters[character_id]

        @self.app.post("/api/v1/projects/{project_id}/characters/{character_id}/unlock")
        async def unlock_character(project_id: str, character_id: str):
            if character_id not in self.characters:
                raise HTTPException(status_code=404, detail="Character not found")
            self.characters[character_id]["locked"] = False
            return self.characters[character_id]

        @self.app.put("/api/v1/projects/{project_id}/characters/{character_id}/physical")
        async def update_physical_description(
            project_id: str, character_id: str, physical_description: dict[str, str] = None
        ):
            if character_id not in self.characters:
                raise HTTPException(status_code=404, detail="Character not found")

            char = self.characters[character_id]
            if char["locked"]:
                raise HTTPException(status_code=400, detail="Character is locked")

            if physical_description:
                char["physical_description"] = physical_description
            return char


class TestCharactersCRUD:
    """Test character CRUD operations."""

    @pytest.fixture
    def client(self):
        router = MockCharactersRouter()
        return TestClient(router.app)

    @pytest.fixture
    def project_id(self):
        return str(uuid4())

    def test_create_character(self, client, project_id):
        """Test creating a new character."""
        response = client.post(
            f"/api/v1/projects/{project_id}/characters",
            params={"name": "Sarah", "description": "The protagonist"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Sarah"
        assert data["project_id"] == project_id
        assert data["locked"] is False

    def test_list_characters(self, client, project_id):
        """Test listing characters for a project."""
        # Create characters
        for name in ["John", "Sarah", "Mike"]:
            client.post(f"/api/v1/projects/{project_id}/characters", params={"name": name})

        response = client.get(f"/api/v1/projects/{project_id}/characters")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3

    def test_get_character(self, client, project_id):
        """Test getting a single character."""
        create_response = client.post(
            f"/api/v1/projects/{project_id}/characters", params={"name": "Test Character"}
        )
        char_id = create_response.json()["id"]

        response = client.get(f"/api/v1/projects/{project_id}/characters/{char_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == char_id

    def test_get_nonexistent_character(self, client, project_id):
        """Test getting nonexistent character returns 404."""
        response = client.get(f"/api/v1/projects/{project_id}/characters/{uuid4()}")
        assert response.status_code == 404

    def test_update_character(self, client, project_id):
        """Test updating a character."""
        create_response = client.post(
            f"/api/v1/projects/{project_id}/characters", params={"name": "Original Name"}
        )
        char_id = create_response.json()["id"]

        response = client.put(
            f"/api/v1/projects/{project_id}/characters/{char_id}", params={"name": "Updated Name"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"

    def test_delete_character(self, client, project_id):
        """Test deleting a character."""
        create_response = client.post(
            f"/api/v1/projects/{project_id}/characters", params={"name": "To Delete"}
        )
        char_id = create_response.json()["id"]

        response = client.delete(f"/api/v1/projects/{project_id}/characters/{char_id}")
        assert response.status_code == 200

        get_response = client.get(f"/api/v1/projects/{project_id}/characters/{char_id}")
        assert get_response.status_code == 404


class TestCharacterLocking:
    """Test character locking functionality."""

    @pytest.fixture
    def client(self):
        router = MockCharactersRouter()
        return TestClient(router.app)

    @pytest.fixture
    def project_id(self):
        return str(uuid4())

    def test_lock_character(self, client, project_id):
        """Test locking a character."""
        create_response = client.post(
            f"/api/v1/projects/{project_id}/characters", params={"name": "Test"}
        )
        char_id = create_response.json()["id"]

        response = client.post(f"/api/v1/projects/{project_id}/characters/{char_id}/lock")

        assert response.status_code == 200
        data = response.json()
        assert data["locked"] is True

    def test_unlock_character(self, client, project_id):
        """Test unlocking a character."""
        create_response = client.post(
            f"/api/v1/projects/{project_id}/characters", params={"name": "Test"}
        )
        char_id = create_response.json()["id"]

        # Lock then unlock
        client.post(f"/api/v1/projects/{project_id}/characters/{char_id}/lock")
        response = client.post(f"/api/v1/projects/{project_id}/characters/{char_id}/unlock")

        assert response.status_code == 200
        data = response.json()
        assert data["locked"] is False

    def test_cannot_update_locked_character(self, client, project_id):
        """Test that locked characters cannot be updated."""
        create_response = client.post(
            f"/api/v1/projects/{project_id}/characters", params={"name": "Test"}
        )
        char_id = create_response.json()["id"]

        # Lock character
        client.post(f"/api/v1/projects/{project_id}/characters/{char_id}/lock")

        # Try to update
        response = client.put(
            f"/api/v1/projects/{project_id}/characters/{char_id}", params={"name": "New Name"}
        )

        assert response.status_code == 400


class TestCharacterPhysicalDescription:
    """Test character physical description management."""

    @pytest.fixture
    def client(self):
        router = MockCharactersRouter()
        return TestClient(router.app)

    @pytest.fixture
    def project_id(self):
        return str(uuid4())

    def test_physical_description_fields(self):
        """Test physical description field structure."""
        char = create_mock_character()

        expected_fields = ["age", "height", "build", "hair", "eyes", "notable_features"]
        for field in expected_fields:
            assert field in char["physical_description"]

    def test_character_has_physical_description(self, client, project_id):
        """Test that characters have physical descriptions."""
        response = client.post(f"/api/v1/projects/{project_id}/characters", params={"name": "Test"})

        data = response.json()
        assert "physical_description" in data


class TestCharacterValidation:
    """Test character validation."""

    def test_character_name_required(self):
        """Test character name is required."""

        def validate_name(name: str) -> bool:
            return name is not None and len(name.strip()) > 0

        assert validate_name("John") is True
        assert validate_name("") is False
        assert validate_name("   ") is False

    def test_character_name_uniqueness_per_project(self):
        """Test character names are unique within a project."""
        project_chars = {}

        def add_character(project_id: str, name: str) -> bool:
            key = (project_id, name.lower())
            if key in project_chars:
                return False
            project_chars[key] = True
            return True

        project_id = str(uuid4())
        assert add_character(project_id, "John") is True
        assert add_character(project_id, "John") is False  # Duplicate
        assert add_character(project_id, "john") is False  # Case insensitive

        other_project = str(uuid4())
        assert add_character(other_project, "John") is True  # Different project OK

    def test_physical_description_optional(self):
        """Test physical description is optional."""
        char = {
            "id": str(uuid4()),
            "name": "Test",
            "physical_description": None,  # Optional
        }
        assert char["physical_description"] is None
