"""Object storage service backed by MinIO."""

from datetime import timedelta
from io import BytesIO
from typing import Protocol
from urllib.parse import urlparse, urlunparse

from minio import Minio

from app.core.config import Settings


class ObjectStorage(Protocol):
    """Interface used by photo services and API tests."""

    bucket: str

    def ensure_bucket(self) -> None:
        """Create the bucket if it does not exist."""

    def upload_bytes(self, object_key: str, data: bytes, content_type: str) -> None:
        """Upload an object from bytes."""

    def presigned_get_url(self, object_key: str, expires_seconds: int = 900) -> str:
        """Return a short-lived URL for reading an object."""

    def download_bytes(self, object_key: str) -> bytes:
        """Download an object into memory."""

    def delete_object(self, object_key: str) -> None:
        """Delete an object if it exists."""


class MinioObjectStorage:
    """MinIO object storage implementation."""

    def __init__(self, settings: Settings) -> None:
        self.bucket = settings.minio_bucket
        self._settings = settings
        self._client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )

    def ensure_bucket(self) -> None:
        if not self._client.bucket_exists(self.bucket):
            self._client.make_bucket(self.bucket)

    def upload_bytes(self, object_key: str, data: bytes, content_type: str) -> None:
        self._client.put_object(
            self.bucket,
            object_key,
            BytesIO(data),
            length=len(data),
            content_type=content_type,
        )

    def presigned_get_url(self, object_key: str, expires_seconds: int = 900) -> str:
        url = self._client.presigned_get_object(
            self.bucket,
            object_key,
            expires=timedelta(seconds=expires_seconds),
        )
        if self._settings.minio_public_endpoint:
            parsed = urlparse(url)
            public = urlparse(self._settings.minio_public_endpoint)
            parsed = parsed._replace(scheme=public.scheme, netloc=public.netloc)
            url = urlunparse(parsed)
        return url

    def download_bytes(self, object_key: str) -> bytes:
        response = self._client.get_object(self.bucket, object_key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def delete_object(self, object_key: str) -> None:
        self._client.remove_object(self.bucket, object_key)
