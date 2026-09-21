import pytest
from app.core.exceptions import NotFoundError
from app.providers.storage import (
    MemoryStorageProvider,
    MinioStorageProvider,
    S3StorageProvider,
    get_storage_provider,
)


def test_memory_storage_provider_crud():
    provider = MemoryStorageProvider(bucket_name="test-invoices")
    payload = b"%PDF-1.4 Mock Invoice Content"
    object_key = "invoices/2026/09/inv_001.pdf"

    # 1. Upload
    uri = provider.upload_file(payload, object_key, content_type="application/pdf")
    assert uri == f"memory://test-invoices/{object_key}"

    # 2. Download
    downloaded = provider.download_file(object_key)
    assert downloaded == payload

    # 3. Presigned URL
    url = provider.get_file_url(object_key, expires_in_seconds=1800)
    assert "test-invoices" in url
    assert object_key in url

    # 4. Health
    assert provider.check_health() is True

    # 5. Delete
    assert provider.delete_file(object_key) is True
    assert provider.delete_file("non_existent_key") is False

    with pytest.raises(NotFoundError):
        provider.download_file(object_key)


def test_minio_storage_provider_initialization():
    provider = MinioStorageProvider(
        endpoint_url="http://localhost:9000",
        access_key="test_user",
        secret_key="test_pass",
        bucket_name="ar-test-bucket",
        secure=False,
    )
    assert provider.bucket_name == "ar-test-bucket"
    assert provider.endpoint_url == "http://localhost:9000"


def test_storage_factory(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.STORAGE_PROVIDER", "memory")
    provider = get_storage_provider()
    assert isinstance(provider, MemoryStorageProvider)
