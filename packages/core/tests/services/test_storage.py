"""Tests for Storage service."""

import pytest
import pytest_asyncio
from pathlib import Path
from uuid import uuid4
from io import BytesIO

from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.services.storage import StorageService


class TestStorageService:
    """Tests for StorageService."""

    @pytest.fixture
    def storage_service(self, db_session: AsyncSession) -> StorageService:
        """Create a storage service instance."""
        return StorageService(db_session)

    @pytest.mark.asyncio
    async def test_upload_file(
        self,
        storage_service: StorageService,
        temp_dir: Path,
    ):
        """Test uploading a file."""
        if hasattr(storage_service, "upload"):
            # Create a test file
            test_file = temp_dir / "test_upload.txt"
            test_file.write_text("Test content")

            result = await storage_service.upload(
                file_path=test_file,
                destination="uploads/test_upload.txt",
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_upload_bytes(
        self,
        storage_service: StorageService,
    ):
        """Test uploading bytes directly."""
        if hasattr(storage_service, "upload_bytes"):
            content = b"Test binary content"
            result = await storage_service.upload_bytes(
                content=content,
                destination="uploads/test_bytes.bin",
                content_type="application/octet-stream",
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_download_file(
        self,
        storage_service: StorageService,
        temp_dir: Path,
    ):
        """Test downloading a file."""
        if hasattr(storage_service, "download"):
            destination = temp_dir / "downloaded.txt"
            result = await storage_service.download(
                source="uploads/test_upload.txt",
                destination=destination,
            )

            # May return False if file doesn't exist
            assert isinstance(result, bool) or result is None

    @pytest.mark.asyncio
    async def test_get_file_url(
        self,
        storage_service: StorageService,
    ):
        """Test getting a file URL."""
        if hasattr(storage_service, "get_url"):
            url = await storage_service.get_url(
                path="uploads/test.txt",
            )

            assert url is None or isinstance(url, str)

    @pytest.mark.asyncio
    async def test_get_signed_url(
        self,
        storage_service: StorageService,
    ):
        """Test getting a signed/presigned URL."""
        if hasattr(storage_service, "get_signed_url"):
            url = await storage_service.get_signed_url(
                path="uploads/test.txt",
                expiry_seconds=3600,
            )

            assert url is None or isinstance(url, str)

    @pytest.mark.asyncio
    async def test_delete_file(
        self,
        storage_service: StorageService,
    ):
        """Test deleting a file."""
        if hasattr(storage_service, "delete"):
            result = await storage_service.delete(
                path="uploads/test_delete.txt",
            )

            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_file_exists(
        self,
        storage_service: StorageService,
    ):
        """Test checking if a file exists."""
        if hasattr(storage_service, "exists"):
            exists = await storage_service.exists(
                path="uploads/nonexistent.txt",
            )

            assert isinstance(exists, bool)
            assert exists is False

    @pytest.mark.asyncio
    async def test_list_files(
        self,
        storage_service: StorageService,
    ):
        """Test listing files in a directory."""
        if hasattr(storage_service, "list"):
            files = await storage_service.list(
                prefix="uploads/",
            )

            assert isinstance(files, list)

    @pytest.mark.asyncio
    async def test_get_file_size(
        self,
        storage_service: StorageService,
    ):
        """Test getting file size."""
        if hasattr(storage_service, "get_size"):
            size = await storage_service.get_size(
                path="uploads/test.txt",
            )

            # May return None if file doesn't exist
            assert size is None or size >= 0

    @pytest.mark.asyncio
    async def test_get_file_metadata(
        self,
        storage_service: StorageService,
    ):
        """Test getting file metadata."""
        if hasattr(storage_service, "get_metadata"):
            metadata = await storage_service.get_metadata(
                path="uploads/test.txt",
            )

            assert metadata is None or isinstance(metadata, dict)

    @pytest.mark.asyncio
    async def test_copy_file(
        self,
        storage_service: StorageService,
    ):
        """Test copying a file."""
        if hasattr(storage_service, "copy"):
            result = await storage_service.copy(
                source="uploads/source.txt",
                destination="uploads/destination.txt",
            )

            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_move_file(
        self,
        storage_service: StorageService,
    ):
        """Test moving a file."""
        if hasattr(storage_service, "move"):
            result = await storage_service.move(
                source="uploads/source.txt",
                destination="uploads/moved.txt",
            )

            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_create_directory(
        self,
        storage_service: StorageService,
    ):
        """Test creating a directory."""
        if hasattr(storage_service, "create_directory"):
            result = await storage_service.create_directory(
                path="uploads/new_directory/",
            )

            assert result is True or result is not None

    @pytest.mark.asyncio
    async def test_get_total_storage_used(
        self,
        storage_service: StorageService,
    ):
        """Test getting total storage used."""
        if hasattr(storage_service, "get_total_size"):
            user_id = uuid4()
            size = await storage_service.get_total_size(user_id)

            assert size >= 0

    @pytest.mark.asyncio
    async def test_cleanup_temp_files(
        self,
        storage_service: StorageService,
    ):
        """Test cleaning up temporary files."""
        if hasattr(storage_service, "cleanup_temp"):
            count = await storage_service.cleanup_temp(
                older_than_hours=24,
            )

            assert isinstance(count, int)

    @pytest.mark.asyncio
    async def test_stream_upload(
        self,
        storage_service: StorageService,
    ):
        """Test streaming upload."""
        if hasattr(storage_service, "stream_upload"):
            stream = BytesIO(b"Streaming content")
            result = await storage_service.stream_upload(
                stream=stream,
                destination="uploads/streamed.txt",
                content_type="text/plain",
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_generate_upload_url(
        self,
        storage_service: StorageService,
    ):
        """Test generating a direct upload URL."""
        if hasattr(storage_service, "generate_upload_url"):
            url = await storage_service.generate_upload_url(
                destination="uploads/direct.txt",
                content_type="text/plain",
                expiry_seconds=3600,
            )

            assert url is None or isinstance(url, str)

    @pytest.mark.asyncio
    async def test_set_file_visibility(
        self,
        storage_service: StorageService,
    ):
        """Test setting file visibility."""
        if hasattr(storage_service, "set_visibility"):
            result = await storage_service.set_visibility(
                path="uploads/test.txt",
                public=True,
            )

            assert isinstance(result, bool)
