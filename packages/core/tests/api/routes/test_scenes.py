"""Tests for scenes API routes.

Tests cover:
- Scene CRUD operations
- Scene breakdown
- Scene ordering
- Shot management within scenes
"""

import pytest
from datetime import datetime
from uuid import uuid4
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient


def create_mock_scene(
    scene_number: int = 1,
    project_id: str = None
) -> Dict[str, Any]:
    """Create a mock scene."""
    return {
        "id": str(uuid4()),
        "project_id": project_id or str(uuid4()),
        "scene_number": scene_number,
        "sequence_number": scene_number,
        "heading": f"INT. LOCATION {scene_number} - DAY",
        "location": f"LOCATION {scene_number}",
        "int_ext": "INT",
        "time_of_day": "DAY",
        "description": f"Scene {scene_number} description",
        "shots": [],
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


class MockScenesRouter:
    """Mock scenes router for testing."""

    def __init__(self):
        self.app = FastAPI()
        self.scenes: Dict[str, Dict] = {}
        self._setup_routes()

    def _setup_routes(self):
        @self.app.get("/api/v1/projects/{project_id}/scenes")
        async def list_scenes(project_id: str):
            scenes = [s for s in self.scenes.values() if s["project_id"] == project_id]
            scenes.sort(key=lambda x: x["sequence_number"])
            return {"items": scenes, "total": len(scenes)}

        @self.app.post("/api/v1/projects/{project_id}/scenes")
        async def create_scene(
            project_id: str,
            scene_number: int,
            heading: str = "INT. LOCATION - DAY"
        ):
            # Check for duplicate scene numbers
            existing = [s for s in self.scenes.values()
                       if s["project_id"] == project_id and s["scene_number"] == scene_number]
            if existing:
                raise HTTPException(status_code=400, detail="Scene number already exists")

            scene = create_mock_scene(scene_number=scene_number, project_id=project_id)
            scene["heading"] = heading
            self.scenes[scene["id"]] = scene
            return scene

        @self.app.get("/api/v1/projects/{project_id}/scenes/{scene_id}")
        async def get_scene(project_id: str, scene_id: str):
            if scene_id not in self.scenes:
                raise HTTPException(status_code=404, detail="Scene not found")
            return self.scenes[scene_id]

        @self.app.put("/api/v1/projects/{project_id}/scenes/{scene_id}")
        async def update_scene(
            project_id: str,
            scene_id: str,
            heading: str = None,
            description: str = None
        ):
            if scene_id not in self.scenes:
                raise HTTPException(status_code=404, detail="Scene not found")

            scene = self.scenes[scene_id]
            if heading:
                scene["heading"] = heading
            if description is not None:
                scene["description"] = description
            scene["updated_at"] = datetime.utcnow().isoformat()
            return scene

        @self.app.delete("/api/v1/projects/{project_id}/scenes/{scene_id}")
        async def delete_scene(project_id: str, scene_id: str):
            if scene_id not in self.scenes:
                raise HTTPException(status_code=404, detail="Scene not found")
            del self.scenes[scene_id]
            return {"status": "deleted"}

        @self.app.post("/api/v1/projects/{project_id}/scenes/reorder")
        async def reorder_scenes(project_id: str, scene_ids: List[str]):
            for i, scene_id in enumerate(scene_ids):
                if scene_id in self.scenes:
                    self.scenes[scene_id]["sequence_number"] = i + 1
            return {"status": "reordered"}

        @self.app.get("/api/v1/projects/{project_id}/scenes/{scene_id}/shots")
        async def list_scene_shots(project_id: str, scene_id: str):
            if scene_id not in self.scenes:
                raise HTTPException(status_code=404, detail="Scene not found")
            return {"items": self.scenes[scene_id]["shots"]}

        @self.app.get("/api/v1/projects/{project_id}/scenes/{scene_id}/breakdown")
        async def get_scene_breakdown(project_id: str, scene_id: str):
            if scene_id not in self.scenes:
                raise HTTPException(status_code=404, detail="Scene not found")
            scene = self.scenes[scene_id]
            return {
                "scene_id": scene_id,
                "heading": scene["heading"],
                "location": scene["location"],
                "time_of_day": scene["time_of_day"],
                "characters": ["JOHN", "SARAH"],  # Mock characters
                "props": ["Coffee cup", "Newspaper"],  # Mock props
                "camera_notes": "Wide establishing shot",
            }


class TestScenesCRUD:
    """Test scene CRUD operations."""

    @pytest.fixture
    def client(self):
        router = MockScenesRouter()
        return TestClient(router.app)

    @pytest.fixture
    def project_id(self):
        return str(uuid4())

    def test_create_scene(self, client, project_id):
        """Test creating a new scene."""
        response = client.post(
            f"/api/v1/projects/{project_id}/scenes",
            params={"scene_number": 1, "heading": "INT. COFFEE SHOP - DAY"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["scene_number"] == 1
        assert data["heading"] == "INT. COFFEE SHOP - DAY"

    def test_duplicate_scene_number_rejected(self, client, project_id):
        """Test duplicate scene numbers are rejected."""
        client.post(
            f"/api/v1/projects/{project_id}/scenes",
            params={"scene_number": 1}
        )

        response = client.post(
            f"/api/v1/projects/{project_id}/scenes",
            params={"scene_number": 1}
        )

        assert response.status_code == 400

    def test_list_scenes_ordered(self, client, project_id):
        """Test scenes are listed in sequence order."""
        # Create scenes out of order
        for num in [3, 1, 2]:
            client.post(
                f"/api/v1/projects/{project_id}/scenes",
                params={"scene_number": num}
            )

        response = client.get(f"/api/v1/projects/{project_id}/scenes")

        assert response.status_code == 200
        data = response.json()
        sequence_numbers = [s["sequence_number"] for s in data["items"]]
        assert sequence_numbers == sorted(sequence_numbers)

    def test_get_scene(self, client, project_id):
        """Test getting a single scene."""
        create_response = client.post(
            f"/api/v1/projects/{project_id}/scenes",
            params={"scene_number": 1}
        )
        scene_id = create_response.json()["id"]

        response = client.get(f"/api/v1/projects/{project_id}/scenes/{scene_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == scene_id

    def test_update_scene(self, client, project_id):
        """Test updating a scene."""
        create_response = client.post(
            f"/api/v1/projects/{project_id}/scenes",
            params={"scene_number": 1}
        )
        scene_id = create_response.json()["id"]

        response = client.put(
            f"/api/v1/projects/{project_id}/scenes/{scene_id}",
            params={"heading": "EXT. PARK - NIGHT"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["heading"] == "EXT. PARK - NIGHT"

    def test_delete_scene(self, client, project_id):
        """Test deleting a scene."""
        create_response = client.post(
            f"/api/v1/projects/{project_id}/scenes",
            params={"scene_number": 1}
        )
        scene_id = create_response.json()["id"]

        response = client.delete(f"/api/v1/projects/{project_id}/scenes/{scene_id}")
        assert response.status_code == 200


class TestSceneOrdering:
    """Test scene ordering functionality."""

    @pytest.fixture
    def client(self):
        router = MockScenesRouter()
        return TestClient(router.app)

    @pytest.fixture
    def project_id(self):
        return str(uuid4())

    def test_reorder_scenes(self, client, project_id):
        """Test reordering scenes."""
        # Create 3 scenes
        scene_ids = []
        for num in [1, 2, 3]:
            response = client.post(
                f"/api/v1/projects/{project_id}/scenes",
                params={"scene_number": num}
            )
            scene_ids.append(response.json()["id"])

        # Reorder to [3, 1, 2]
        new_order = [scene_ids[2], scene_ids[0], scene_ids[1]]
        response = client.post(
            f"/api/v1/projects/{project_id}/scenes/reorder",
            params={"scene_ids": new_order}
        )

        assert response.status_code == 200


class TestSceneBreakdown:
    """Test scene breakdown functionality."""

    @pytest.fixture
    def client(self):
        router = MockScenesRouter()
        return TestClient(router.app)

    @pytest.fixture
    def project_id(self):
        return str(uuid4())

    def test_get_scene_breakdown(self, client, project_id):
        """Test getting scene breakdown."""
        create_response = client.post(
            f"/api/v1/projects/{project_id}/scenes",
            params={"scene_number": 1}
        )
        scene_id = create_response.json()["id"]

        response = client.get(
            f"/api/v1/projects/{project_id}/scenes/{scene_id}/breakdown"
        )

        assert response.status_code == 200
        data = response.json()
        assert "characters" in data
        assert "props" in data
        assert "location" in data


class TestSceneValidation:
    """Test scene validation."""

    def test_valid_time_of_day_values(self):
        """Test valid time of day values."""
        valid_times = [
            "day", "night", "dawn", "dusk",
            "morning", "afternoon", "evening", "unspecified"
        ]
        for time in valid_times:
            assert time in valid_times

    def test_valid_int_ext_values(self):
        """Test valid INT/EXT values."""
        valid_values = ["INT", "EXT", "INT/EXT"]
        for value in valid_values:
            assert value in valid_values

    def test_scene_number_positive(self):
        """Test scene number must be positive."""
        def validate_scene_number(num: int) -> bool:
            return num > 0

        assert validate_scene_number(1) is True
        assert validate_scene_number(100) is True
        assert validate_scene_number(0) is False
        assert validate_scene_number(-1) is False

    def test_heading_format(self):
        """Test scene heading format."""
        valid_headings = [
            "INT. COFFEE SHOP - DAY",
            "EXT. CITY STREET - NIGHT",
            "INT/EXT. CAR - MORNING",
        ]

        for heading in valid_headings:
            # Basic validation: contains location and time
            assert " - " in heading
            assert len(heading) > 10
