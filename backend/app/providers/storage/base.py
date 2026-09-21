from abc import ABC, abstractmethod
from typing import Optional


class StorageProvider(ABC):
    """
    Abstract Storage Provider Interface.
    Enforces Rule 02 & ADR-001 by isolating object storage mechanics (MinIO/S3/R2)
    behind a unified contract, allowing zero-friction swapping between local dev and cloud.
    """

    @abstractmethod
    def upload_file(
        self,
        file_data: bytes,
        object_name: str,
        content_type: str = "application/pdf",
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Persists raw binary bytes to the storage bucket.
        Returns the persistent storage URI or object key.
        """
        pass

    @abstractmethod
    def download_file(self, object_name: str) -> bytes:
        """
        Retrieves raw binary bytes of a stored object.
        Raises NotFoundError if the object does not exist.
        """
        pass

    @abstractmethod
    def get_file_url(self, object_name: str, expires_in_seconds: int = 3600) -> str:
        """
        Generates a secure presigned access URL for operator document review.
        """
        pass

    @abstractmethod
    def delete_file(self, object_name: str) -> bool:
        """
        Removes an object from storage. Returns True if deleted, False otherwise.
        """
        pass

    @abstractmethod
    def check_health(self) -> bool:
        """
        Verifies bucket accessibility and credential validity.
        Used by service health probes.
        """
        pass
