import io
import logging
from typing import Optional
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.exceptions import AppException, NotFoundError
from app.providers.storage.base import StorageProvider

logger = logging.getLogger("app.providers.storage.s3")


class S3StorageProvider(StorageProvider):
    """
    AWS S3 / S3-compatible Object Storage Provider.
    Encapsulates boto3 S3 client operations with signature v4 and bucket auto-initialization.
    """

    def __init__(
        self,
        bucket_name: str,
        endpoint_url: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        region_name: str = "us-east-1",
        use_ssl: bool = True,
        addressing_style: str = "auto",
    ):
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url
        self.region_name = region_name

        client_kwargs = {
            "service_name": "s3",
            "region_name": region_name,
            "use_ssl": use_ssl,
            "config": Config(
                signature_version="s3v4",
                s3={"addressing_style": addressing_style},
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        }

        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url
        if access_key and secret_key:
            client_kwargs["aws_access_key_id"] = access_key
            client_kwargs["aws_secret_access_key"] = secret_key

        self.client = boto3.client(**client_kwargs)
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        """Idempotently ensures target bucket is created if storage endpoint is reachable."""
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ("404", "NoSuchBucket"):
                try:
                    if self.region_name == "us-east-1" or self.endpoint_url:
                        self.client.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={"LocationConstraint": self.region_name},
                        )
                    logger.info(f"Storage bucket '{self.bucket_name}' created successfully.")
                except Exception as create_exc:
                    logger.warning(f"Could not auto-create bucket '{self.bucket_name}': {str(create_exc)}")
            else:
                logger.warning(f"Storage bucket check emitted: {str(e)}")
        except Exception as exc:
            # Standard failure handling: intercept network unreachability without crashing provider initialization
            logger.warning(f"Storage service at {self.endpoint_url or 'AWS S3'} is currently unreachable: {str(exc)}")

    def upload_file(
        self,
        file_data: bytes,
        object_name: str,
        content_type: str = "application/pdf",
        metadata: Optional[dict] = None,
    ) -> str:
        """Uploads binary file data to the bucket and returns the object key/path."""
        extra_args = {"ContentType": content_type}
        if metadata:
            extra_args["Metadata"] = {k: str(v) for k, v in metadata.items()}

        try:
            self.client.upload_fileobj(
                Fileobj=io.BytesIO(file_data),
                Bucket=self.bucket_name,
                Key=object_name,
                ExtraArgs=extra_args,
            )
            return f"s3://{self.bucket_name}/{object_name}"
        except ClientError as exc:
            logger.error(f"S3 upload failed for {object_name}: {str(exc)}")
            raise AppException(f"Failed to persist file in storage: {str(exc)}")

    def download_file(self, object_name: str) -> bytes:
        """Retrieves raw binary bytes of a stored object."""
        try:
            buffer = io.BytesIO()
            self.client.download_fileobj(Bucket=self.bucket_name, Key=object_name, Fileobj=buffer)
            buffer.seek(0)
            return buffer.read()
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            if error_code in ("404", "NoSuchKey"):
                raise NotFoundError(f"Document object '{object_name}' not found in storage.")
            logger.error(f"S3 download failed for {object_name}: {str(exc)}")
            raise AppException(f"Failed to retrieve file from storage: {str(exc)}")

    def get_file_url(self, object_name: str, expires_in_seconds: int = 3600) -> str:
        """Generates a secure presigned access URL."""
        try:
            url = self.client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.bucket_name, "Key": object_name},
                ExpiresIn=expires_in_seconds,
            )
            return url
        except ClientError as exc:
            logger.error(f"Failed to generate presigned URL for {object_name}: {str(exc)}")
            raise AppException(f"Could not generate document preview URL: {str(exc)}")

    def delete_file(self, object_name: str) -> bool:
        """Deletes object from storage bucket."""
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=object_name)
            return True
        except ClientError as exc:
            logger.error(f"Failed to delete {object_name}: {str(exc)}")
            return False

    def check_health(self) -> bool:
        """Verifies storage bucket connectivity and permissions."""
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
            return True
        except Exception:
            return False
