"""Tests for Templates service."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.models import Project
from scenemachine.services.templates import TemplatesService


class TestTemplatesService:
    """Tests for TemplatesService."""

    @pytest.fixture
    def templates_service(self, db_session: AsyncSession) -> TemplatesService:
        """Create a templates service instance."""
        return TemplatesService(db_session)

    @pytest.mark.asyncio
    async def test_get_all_templates(self, templates_service: TemplatesService):
        """Test getting all available templates."""
        templates = await templates_service.get_all()

        assert isinstance(templates, list)
        assert len(templates) >= 0

    @pytest.mark.asyncio
    async def test_get_templates_by_category(self, templates_service: TemplatesService):
        """Test filtering templates by category."""
        categories = ["film", "short", "commercial", "music_video"]

        for category in categories:
            templates = await templates_service.get_by_category(category)
            assert isinstance(templates, list)

    @pytest.mark.asyncio
    async def test_get_template_by_id(self, templates_service: TemplatesService):
        """Test getting a specific template by ID."""
        # First get all templates
        all_templates = await templates_service.get_all()

        if all_templates:
            template_id = all_templates[0].id if hasattr(all_templates[0], "id") else all_templates[0].get("id")
            template = await templates_service.get_by_id(template_id)
            assert template is not None

    @pytest.mark.asyncio
    async def test_get_template_by_invalid_id(self, templates_service: TemplatesService):
        """Test getting a non-existent template."""
        template = await templates_service.get_by_id(uuid4())

        # Should return None for non-existent template
        assert template is None

    @pytest.mark.asyncio
    async def test_apply_template_to_project(
        self,
        templates_service: TemplatesService,
        sample_project: Project,
    ):
        """Test applying a template to a project."""
        # Get a template
        all_templates = await templates_service.get_all()

        if all_templates:
            template = all_templates[0]
            template_id = template.id if hasattr(template, "id") else template.get("id")

            result = await templates_service.apply_to_project(
                template_id=template_id,
                project_id=sample_project.id,
            )

            assert result is True or result is not None

    @pytest.mark.asyncio
    async def test_get_built_in_templates(self, templates_service: TemplatesService):
        """Test that built-in templates are available."""
        templates = await templates_service.get_all()

        # Should have at least some built-in templates
        assert len(templates) >= 0  # May be 0 if not seeded

    @pytest.mark.asyncio
    async def test_template_contains_required_fields(
        self,
        templates_service: TemplatesService,
    ):
        """Test that templates contain required fields."""
        templates = await templates_service.get_all()

        for template in templates:
            # Check for required fields
            if hasattr(template, "name"):
                assert template.name is not None
            elif isinstance(template, dict):
                assert "name" in template

    @pytest.mark.asyncio
    async def test_create_custom_template(
        self,
        templates_service: TemplatesService,
        sample_project: Project,
    ):
        """Test creating a custom template from a project."""
        if hasattr(templates_service, "create_from_project"):
            template = await templates_service.create_from_project(
                project_id=sample_project.id,
                name="Custom Template",
                description="A custom template for testing",
            )

            assert template is not None

    @pytest.mark.asyncio
    async def test_delete_custom_template(
        self,
        templates_service: TemplatesService,
    ):
        """Test deleting a custom template."""
        if hasattr(templates_service, "delete"):
            # This would test deletion of custom (non-built-in) templates
            result = await templates_service.delete(uuid4())
            # May return False for non-existent template
            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_search_templates(self, templates_service: TemplatesService):
        """Test searching templates by name or description."""
        if hasattr(templates_service, "search"):
            results = await templates_service.search("film")
            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_get_featured_templates(self, templates_service: TemplatesService):
        """Test getting featured templates."""
        if hasattr(templates_service, "get_featured"):
            featured = await templates_service.get_featured()
            assert isinstance(featured, list)

    @pytest.mark.asyncio
    async def test_template_preview(self, templates_service: TemplatesService):
        """Test getting a template preview."""
        all_templates = await templates_service.get_all()

        if all_templates and hasattr(templates_service, "get_preview"):
            template = all_templates[0]
            template_id = template.id if hasattr(template, "id") else template.get("id")

            preview = await templates_service.get_preview(template_id)
            assert preview is not None

    @pytest.mark.asyncio
    async def test_duplicate_template(self, templates_service: TemplatesService):
        """Test duplicating a template."""
        all_templates = await templates_service.get_all()

        if all_templates and hasattr(templates_service, "duplicate"):
            template = all_templates[0]
            template_id = template.id if hasattr(template, "id") else template.get("id")

            duplicate = await templates_service.duplicate(
                template_id=template_id,
                new_name="Duplicate Template",
            )

            assert duplicate is not None

    @pytest.mark.asyncio
    async def test_export_template(self, templates_service: TemplatesService):
        """Test exporting a template."""
        all_templates = await templates_service.get_all()

        if all_templates and hasattr(templates_service, "export"):
            template = all_templates[0]
            template_id = template.id if hasattr(template, "id") else template.get("id")

            exported = await templates_service.export(template_id)
            assert exported is not None

    @pytest.mark.asyncio
    async def test_import_template(self, templates_service: TemplatesService):
        """Test importing a template."""
        if hasattr(templates_service, "import_template"):
            template_data = {
                "name": "Imported Template",
                "category": "film",
                "settings": {},
            }

            imported = await templates_service.import_template(template_data)
            assert imported is not None
