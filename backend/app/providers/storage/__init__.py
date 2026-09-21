import logging
from typing import Dict, Optional

from app.core.config import settings
from app.providers.storage.base import StorageProvider
from app.providers.storage.minio_provider import MinioStorageProvider
from app.providers.storage.s3_provider import S3StorageProvider

logger = logging.getLogger("app.providers.storage")


class MemoryStorageProvider(StorageProvider):
    """In-memory StorageProvider implementation for deterministic test environments."""

    def __init__(self, bucket_name: str = "test-bucket"):
        self.bucket_name = bucket_name
        self._store: Dict[str, bytes] = {}

    def upload_file(
        self,
        file_data: bytes,
        object_name: str,
        content_type: str = "application/pdf",
        metadata: Optional[dict] = None,
    ) -> str:
        self._store[object_name] = file_data
        return f"memory://{self.bucket_name}/{object_name}"

    def download_file(self, object_name: str) -> bytes:
        from app.core.exceptions import NotFoundError
        if object_name not in self._store:
            raise NotFoundError(f"Object {object_name} not found in memory store.")
        return self._store[object_name]

    def get_file_url(self, object_name: str, expires_in_seconds: int = 3600) -> str:
        return f"https://mock-storage.local/{self.bucket_name}/{object_name}?expires={expires_in_seconds}"

    def delete_file(self, object_name: str) -> bool:
        if object_name in self._store:
            del self._store[object_name]
            return True
        return False

    def check_health(self) -> bool:
        return True


def get_storage_provider() -> StorageProvider:
    """Factory creating configured StorageProvider based on system settings."""
    if settings.STORAGE_PROVIDER == "s3":
        return S3StorageProvider(
            bucket_name=settings.AWS_S3_BUCKET,
            access_key=settings.AWS_ACCESS_KEY_ID or None,
            secret_key=settings.AWS_SECRET_ACCESS_KEY or None,
            region_name=settings.AWS_REGION,
        )
    elif settings.STORAGE_PROVIDER == "memory":
        return MemoryStorageProvider(bucket_name=settings.MINIO_BUCKET)
    else:
        return MinioStorageProvider(
            endpoint_url=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            bucket_name=settings.MINIO_BUCKET,
            secure=settings.MINIO_SECURE,
        )


__all__ = [
    "StorageProvider",
    "S3StorageProvider",
    "MinioStorageProvider",
    "MemoryStorageProvider",
    "get_storage_provider",
]
