"""
Storage utilities for Cloudflare R2 and S3-compatible storage.

Provides async upload/download operations for video files.
Supports MinIO for local development.
"""

import asyncio
import hashlib
import mimetypes
import os
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator, BinaryIO, Optional
from urllib.parse import urljoin

import aioboto3
from botocore.config import Config

from .config import get_settings


class R2Storage:
    """
    Cloudflare R2 storage client.

    Uses S3-compatible API with aioboto3 for async operations.
    """

    def __init__(self):
        self.settings = get_settings()
        self._session: Optional[aioboto3.Session] = None

    @property
    def session(self) -> aioboto3.Session:
        """Get or create the aioboto3 session."""
        if self._session is None:
            self._session = aioboto3.Session()
        return self._session

    @property
    def endpoint_url(self) -> str:
        """Get the R2 endpoint URL, with fallback for local development."""
        # Check for override (for MinIO/local development)
        override = os.environ.get("R2_ENDPOINT_URL")
        if override:
            return override
        # Default to R2
        if self.settings.r2_account_id:
            return f"https://{self.settings.r2_account_id}.r2.cloudflarestorage.com"
        # Fallback to MinIO for local dev
        return "http://localhost:9000"

    def _get_client_config(self) -> Config:
        """Get boto3 client configuration."""
        return Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},  # Required for MinIO compatibility
            retries={"max_attempts": 3, "mode": "adaptive"},
        )

    def _get_credentials(self) -> tuple[str, str]:
        """Get access credentials with fallback for local development."""
        # Check for overrides (for MinIO/local development)
        access_key = os.environ.get("R2_ACCESS_KEY_ID") or self.settings.r2_access_key_id
        secret_key = os.environ.get("R2_SECRET_ACCESS_KEY") or self.settings.r2_secret_access_key
        # Fallback to MinIO defaults for local dev
        if not access_key:
            access_key = "minioadmin"
        if not secret_key:
            secret_key = "minioadmin"
        return access_key, secret_key

    async def _get_client(self):
        """Get an async S3 client context manager."""
        access_key, secret_key = self._get_credentials()
        return self.session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=self._get_client_config(),
        )

    async def upload_file(
        self,
        file_path: str,
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """
        Upload a file to R2.

        Args:
            file_path: Path to the local file
            key: Object key (path in bucket)
            content_type: MIME type (auto-detected if not provided)
            metadata: Optional metadata dict

        Returns:
            Dict with upload details including ETag and file size
        """
        if content_type is None:
            content_type, _ = mimetypes.guess_type(file_path)
            content_type = content_type or "application/octet-stream"

        file_size = os.path.getsize(file_path)
        extra_args = {"ContentType": content_type}
        if metadata:
            extra_args["Metadata"] = metadata

        async with await self._get_client() as client:
            with open(file_path, "rb") as f:
                response = await client.upload_fileobj(
                    f,
                    self.settings.r2_bucket_name,
                    key,
                    ExtraArgs=extra_args,
                )

        return {
            "key": key,
            "size": file_size,
            "content_type": content_type,
            "etag": response.get("ETag", "").strip('"'),
        }

    async def upload_bytes(
        self,
        data: bytes,
        key: str,
        content_type: str = "application/octet-stream",
        metadata: Optional[dict] = None,
    ) -> dict:
        """
        Upload bytes directly to R2.

        Args:
            data: Bytes to upload
            key: Object key
            content_type: MIME type
            metadata: Optional metadata dict

        Returns:
            Dict with upload details
        """
        extra_args = {"ContentType": content_type}
        if metadata:
            extra_args["Metadata"] = metadata

        async with await self._get_client() as client:
            response = await client.put_object(
                Bucket=self.settings.r2_bucket_name,
                Key=key,
                Body=data,
                **extra_args,
            )

        return {
            "key": key,
            "size": len(data),
            "content_type": content_type,
            "etag": response.get("ETag", "").strip('"'),
        }

    async def upload_multipart(
        self,
        file_path: str,
        key: str,
        content_type: Optional[str] = None,
        chunk_size: int = 100 * 1024 * 1024,  # 100MB chunks
        progress_callback: Optional[callable] = None,
    ) -> dict:
        """
        Upload a large file using multipart upload.

        Args:
            file_path: Path to the local file
            key: Object key
            content_type: MIME type
            chunk_size: Size of each part in bytes
            progress_callback: Optional callback(bytes_uploaded, total_bytes)

        Returns:
            Dict with upload details
        """
        if content_type is None:
            content_type, _ = mimetypes.guess_type(file_path)
            content_type = content_type or "application/octet-stream"

        file_size = os.path.getsize(file_path)

        async with await self._get_client() as client:
            # Initiate multipart upload
            response = await client.create_multipart_upload(
                Bucket=self.settings.r2_bucket_name,
                Key=key,
                ContentType=content_type,
            )
            upload_id = response["UploadId"]

            parts = []
            bytes_uploaded = 0
            part_number = 1

            try:
                with open(file_path, "rb") as f:
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break

                        # Upload part
                        part_response = await client.upload_part(
                            Bucket=self.settings.r2_bucket_name,
                            Key=key,
                            UploadId=upload_id,
                            PartNumber=part_number,
                            Body=chunk,
                        )

                        parts.append({
                            "PartNumber": part_number,
                            "ETag": part_response["ETag"],
                        })

                        bytes_uploaded += len(chunk)
                        if progress_callback:
                            progress_callback(bytes_uploaded, file_size)

                        part_number += 1

                # Complete multipart upload
                await client.complete_multipart_upload(
                    Bucket=self.settings.r2_bucket_name,
                    Key=key,
                    UploadId=upload_id,
                    MultipartUpload={"Parts": parts},
                )

            except Exception as e:
                # Abort on failure
                await client.abort_multipart_upload(
                    Bucket=self.settings.r2_bucket_name,
                    Key=key,
                    UploadId=upload_id,
                )
                raise e

        return {
            "key": key,
            "size": file_size,
            "content_type": content_type,
            "parts": len(parts),
        }

    async def download_file(self, key: str, file_path: str) -> dict:
        """
        Download a file from R2.

        Args:
            key: Object key
            file_path: Path to save the file

        Returns:
            Dict with download details
        """
        async with await self._get_client() as client:
            response = await client.get_object(
                Bucket=self.settings.r2_bucket_name,
                Key=key,
            )

            with open(file_path, "wb") as f:
                async for chunk in response["Body"]:
                    f.write(chunk)

        return {
            "key": key,
            "size": response["ContentLength"],
            "content_type": response["ContentType"],
        }

    async def get_signed_url(
        self,
        key: str,
        expires_in: int = 3600,
        method: str = "get_object",
    ) -> str:
        """
        Generate a presigned URL for an object.

        Args:
            key: Object key
            expires_in: URL expiration time in seconds
            method: S3 method (get_object, put_object)

        Returns:
            Presigned URL string
        """
        async with await self._get_client() as client:
            url = await client.generate_presigned_url(
                method,
                Params={
                    "Bucket": self.settings.r2_bucket_name,
                    "Key": key,
                },
                ExpiresIn=expires_in,
            )
        return url

    async def get_upload_url(
        self,
        key: str,
        content_type: str,
        expires_in: int = 3600,
    ) -> str:
        """
        Generate a presigned URL for uploading.

        Args:
            key: Object key
            content_type: Expected content type
            expires_in: URL expiration time in seconds

        Returns:
            Presigned upload URL
        """
        async with await self._get_client() as client:
            url = await client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.settings.r2_bucket_name,
                    "Key": key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_in,
            )
        return url

    async def delete_object(self, key: str) -> bool:
        """
        Delete an object from R2.

        Args:
            key: Object key

        Returns:
            True if deleted successfully
        """
        async with await self._get_client() as client:
            await client.delete_object(
                Bucket=self.settings.r2_bucket_name,
                Key=key,
            )
        return True

    async def delete_objects(self, keys: list[str]) -> int:
        """
        Delete multiple objects from R2.

        Args:
            keys: List of object keys

        Returns:
            Number of objects deleted
        """
        if not keys:
            return 0

        async with await self._get_client() as client:
            response = await client.delete_objects(
                Bucket=self.settings.r2_bucket_name,
                Delete={
                    "Objects": [{"Key": key} for key in keys],
                },
            )
        return len(response.get("Deleted", []))

    async def object_exists(self, key: str) -> bool:
        """
        Check if an object exists.

        Args:
            key: Object key

        Returns:
            True if object exists
        """
        try:
            async with await self._get_client() as client:
                await client.head_object(
                    Bucket=self.settings.r2_bucket_name,
                    Key=key,
                )
            return True
        except Exception:
            return False

    async def get_object_info(self, key: str) -> Optional[dict]:
        """
        Get object metadata.

        Args:
            key: Object key

        Returns:
            Dict with object info or None if not found
        """
        try:
            async with await self._get_client() as client:
                response = await client.head_object(
                    Bucket=self.settings.r2_bucket_name,
                    Key=key,
                )
            return {
                "key": key,
                "size": response["ContentLength"],
                "content_type": response["ContentType"],
                "last_modified": response["LastModified"],
                "etag": response["ETag"].strip('"'),
            }
        except Exception:
            return None

    def get_public_url(self, key: str) -> Optional[str]:
        """
        Get the public URL for an object (if bucket is public).

        Args:
            key: Object key

        Returns:
            Public URL or None if not configured
        """
        if self.settings.r2_public_url:
            return urljoin(self.settings.r2_public_url, key)
        return None


def generate_video_key(
    creator_id: str,
    video_id: str,
    filename: str,
    variant: Optional[str] = None,
) -> str:
    """
    Generate a storage key for a video file.

    Args:
        creator_id: Creator's UUID
        video_id: Video's UUID
        filename: Original filename
        variant: Optional variant suffix (e.g., "720p", "thumbnail")

    Returns:
        Storage key string
    """
    # Get file extension
    _, ext = os.path.splitext(filename)
    ext = ext.lower() or ".mp4"

    # Build key
    if variant:
        return f"videos/{creator_id}/{video_id}/{variant}{ext}"
    return f"videos/{creator_id}/{video_id}/source{ext}"


def generate_thumbnail_key(creator_id: str, video_id: str, index: int = 0) -> str:
    """
    Generate a storage key for a video thumbnail.

    Args:
        creator_id: Creator's UUID
        video_id: Video's UUID
        index: Thumbnail index (for multiple thumbnails)

    Returns:
        Storage key string
    """
    return f"videos/{creator_id}/{video_id}/thumbnails/thumb_{index}.jpg"


# Singleton storage instance
_storage: Optional[R2Storage] = None


def get_storage() -> R2Storage:
    """Get the storage singleton."""
    global _storage
    if _storage is None:
        _storage = R2Storage()
    return _storage


async def ensure_bucket_exists() -> bool:
    """
    Ensure the configured storage bucket exists.
    Creates it if necessary (useful for local development with MinIO).

    Returns:
        True if bucket exists or was created
    """
    storage = get_storage()
    try:
        async with await storage._get_client() as client:
            try:
                await client.head_bucket(Bucket=storage.settings.r2_bucket_name)
                return True
            except Exception:
                # Bucket doesn't exist, try to create it
                await client.create_bucket(Bucket=storage.settings.r2_bucket_name)
                return True
    except Exception as e:
        print(f"Warning: Could not ensure bucket exists: {e}")
        return False
