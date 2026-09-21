import logging
from app.providers.storage.s3_provider import S3StorageProvider

logger = logging.getLogger("app.providers.storage.minio")


class MinioStorageProvider(S3StorageProvider):
    """
    MinIO Object Storage Provider.
    Configured specifically for local and self-hosted MinIO servers using path-style addressing.
    """

    def __init__(
        self,
        endpoint_url: str = "http://localhost:9000",
        access_key: str = "minioadmin",
        secret_key: str = "minioadmin",
        bucket_name: str = "ar-documents",
        secure: bool = False,
    ):
        # Format endpoint URL if schema is missing
        if not endpoint_url.startswith("http://") and not endpoint_url.startswith("https://"):
            protocol = "https" if secure else "http"
            formatted_endpoint = f"{protocol}://{endpoint_url}"
        else:
            formatted_endpoint = endpoint_url

        super().__init__(
            bucket_name=bucket_name,
            endpoint_url=formatted_endpoint,
            access_key=access_key,
            secret_key=secret_key,
            region_name="us-east-1",
            use_ssl=secure,
            addressing_style="path",  # MinIO requires path-style addressing
        )
