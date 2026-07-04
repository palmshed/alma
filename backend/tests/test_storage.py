# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT

import hashlib
import os
import tempfile

import pytest

from services.storage import (
    StorageConfig,
    StorageService,
    StorageObject,
    StorageResult,
    StorageStatus,
    StorageMetrics,
    StorageError,
    StorageValidationError,
    StorageHealth,
    ProviderCapabilities,
    ProviderRegistry,
)
from services.storage.providers import (
    MockStorageProvider,
    LocalStorageProvider,
    CloudStorageProvider,
    get_provider,
)


class TestStorageModels:
    def test_storage_object_defaults(self):
        obj = StorageObject(id="1", name="test.txt")
        assert obj.size == 0
        assert obj.content_type == "application/octet-stream"
        assert obj.metadata == {}

    def test_storage_object_with_fields(self):
        obj = StorageObject(
            id="1",
            name="test.txt",
            size=100,
            content_type="text/plain",
            etag="abc123",
            metadata={"key": "value"},
        )
        assert obj.size == 100
        assert obj.content_type == "text/plain"
        assert obj.etag == "abc123"

    def test_storage_result_creation(self):
        result = StorageResult(
            status=StorageStatus.UPLOADED,
            provider="mock",
        )
        assert result.status == StorageStatus.UPLOADED

    def test_storage_result_with_object(self):
        obj = StorageObject(id="1", name="test.txt")
        result = StorageResult(
            status=StorageStatus.UPLOADED,
            object=obj,
            provider="mock",
        )
        assert result.object.name == "test.txt"

    def test_storage_result_with_data(self):
        result = StorageResult(
            status=StorageStatus.DOWNLOADED,
            data=b"hello",
            provider="mock",
        )
        assert result.data == b"hello"

    def test_storage_health(self):
        h = StorageHealth(
            provider="mock",
            config_valid=True,
            bucket="alma",
            healthy=True,
        )
        assert h.provider == "mock"
        assert h.config_valid
        assert h.healthy

    def test_storage_health_with_errors(self):
        h = StorageHealth(
            provider="mock",
            config_valid=False,
            config_errors=["bad config"],
            healthy=False,
        )
        assert not h.config_valid
        assert "bad config" in h.config_errors
        assert not h.healthy

    def test_storage_status_values(self):
        assert StorageStatus.UPLOADED.value == "uploaded"
        assert StorageStatus.DOWNLOADED.value == "downloaded"
        assert StorageStatus.DELETED.value == "deleted"
        assert StorageStatus.EXISTS.value == "exists"
        assert StorageStatus.NOT_FOUND.value == "not_found"
        assert StorageStatus.FAILED.value == "failed"


class TestStorageConfig:
    def test_default_config(self):
        config = StorageConfig()
        assert config.provider == "mock"
        assert config.bucket == "alma"
        assert config.max_upload_size_mb == 50
        assert config.max_upload_size_bytes == 50 * 1024 * 1024

    def test_config_validation_valid(self):
        config = StorageConfig()
        valid, errors = config.is_valid()
        assert valid
        assert errors == []

    def test_config_validation_invalid_provider(self):
        config = StorageConfig(provider="nonexistent")
        valid, errors = config.is_valid()
        assert not valid
        assert any("provider" in e.lower() for e in errors)

    def test_config_validation_invalid_max_size(self):
        config = StorageConfig(max_upload_size_mb=0)
        valid, errors = config.is_valid()
        assert not valid
        assert any("max_upload_size_mb" in e for e in errors)

    def test_config_validation_local_no_base_path(self):
        config = StorageConfig(provider="local")
        valid, errors = config.is_valid()
        assert not valid
        assert any("base_path" in e.lower() for e in errors)

    def test_config_validation_local_with_base_path(self):
        config = StorageConfig(provider="local", base_path="/tmp/test")
        valid, errors = config.is_valid()
        assert valid

    def test_from_env_defaults(self, monkeypatch):
        monkeypatch.delenv("STORAGE_PROVIDER", raising=False)
        config = StorageConfig.from_env()
        assert config.provider == "mock"

    def test_from_env_override(self, monkeypatch):
        monkeypatch.setenv("STORAGE_PROVIDER", "local")
        monkeypatch.setenv("STORAGE_BASE_PATH", "/tmp/test")
        config = StorageConfig.from_env()
        assert config.provider == "local"
        assert config.base_path == "/tmp/test"


class TestStorageMetrics:
    def test_initial_state(self):
        m = StorageMetrics()
        assert m.uploads == 0
        assert m.downloads == 0
        assert m.deletes == 0
        assert m.lists == 0
        assert m.failures == 0
        assert m.avg_duration_ms == 0.0

    def test_record_counts(self):
        m = StorageMetrics()
        m.record_upload()
        m.record_download()
        m.record_delete()
        m.record_list()
        m.record_failure()
        snap = m.snapshot()
        assert snap["uploads"] == 1
        assert snap["downloads"] == 1
        assert snap["deletes"] == 1
        assert snap["lists"] == 1
        assert snap["failures"] == 1

    def test_average_duration(self):
        m = StorageMetrics()
        m.record_duration(0.1)
        m.record_duration(0.2)
        assert m.avg_duration_ms == pytest.approx(150.0, abs=0.001)

    def test_snapshot(self):
        m = StorageMetrics()
        m.record_upload()
        snap = m.snapshot()
        assert isinstance(snap, dict)
        assert "uploads" in snap
        assert "avg_duration_ms" in snap


class TestProviderCapabilities:
    def test_default_capabilities(self):
        caps = ProviderCapabilities()
        assert caps.public_urls
        assert caps.signed_urls
        assert caps.multipart_upload
        assert caps.versioning
        assert caps.metadata
        assert caps.streaming


class TestMockStorageProvider:
    @pytest.fixture
    def provider(self):
        return MockStorageProvider()

    def test_upload_returns_result(self, provider):
        result = provider.upload("test.txt", b"hello")
        assert result.status == StorageStatus.UPLOADED
        assert result.object.name == "test.txt"

    def test_upload_sets_size_and_etag(self, provider):
        data = b"hello world"
        result = provider.upload("test.txt", data)
        assert result.object.size == len(data)
        assert result.object.etag == hashlib.md5(data).hexdigest()

    def test_upload_with_content_type(self, provider):
        result = provider.upload("test.txt", b"hello", content_type="text/plain")
        assert result.object.content_type == "text/plain"

    def test_upload_with_metadata(self, provider):
        result = provider.upload("test.txt", b"hello", metadata={"author": "test"})
        assert result.object.metadata["author"] == "test"

    def test_download_existing(self, provider):
        provider.upload("test.txt", b"hello")
        result = provider.download("test.txt")
        assert result.status == StorageStatus.DOWNLOADED
        assert result.data == b"hello"

    def test_download_nonexistent(self, provider):
        result = provider.download("nonexistent.txt")
        assert result.status == StorageStatus.NOT_FOUND

    def test_delete_existing(self, provider):
        provider.upload("test.txt", b"hello")
        result = provider.delete("test.txt")
        assert result.status == StorageStatus.DELETED

    def test_delete_nonexistent(self, provider):
        result = provider.delete("nonexistent.txt")
        assert result.status == StorageStatus.NOT_FOUND

    def test_exists_existing(self, provider):
        provider.upload("test.txt", b"hello")
        result = provider.exists("test.txt")
        assert result.status == StorageStatus.EXISTS

    def test_exists_nonexistent(self, provider):
        result = provider.exists("nonexistent.txt")
        assert result.status == StorageStatus.NOT_FOUND

    def test_metadata_existing(self, provider):
        provider.upload("test.txt", b"hello")
        result = provider.metadata("test.txt")
        assert result.status == StorageStatus.EXISTS
        assert result.object.name == "test.txt"

    def test_metadata_nonexistent(self, provider):
        result = provider.metadata("nonexistent.txt")
        assert result.status == StorageStatus.NOT_FOUND

    def test_list_with_prefix(self, provider):
        provider.upload("a/file1.txt", b"1")
        provider.upload("a/file2.txt", b"2")
        provider.upload("b/file3.txt", b"3")
        result = provider.list("a/")
        assert result.status == StorageStatus.EXISTS
        names = eval(result.data.decode())
        assert len(names) == 2
        assert "a/file1.txt" in names

    def test_list_empty_prefix(self, provider):
        provider.upload("a.txt", b"1")
        provider.upload("b.txt", b"2")
        result = provider.list("")
        assert result.status == StorageStatus.EXISTS
        names = eval(result.data.decode())
        assert len(names) == 2

    def test_signed_url_existing(self, provider):
        provider.upload("test.txt", b"hello")
        result = provider.signed_url("test.txt")
        assert result.status == StorageStatus.EXISTS

    def test_signed_url_nonexistent(self, provider):
        result = provider.signed_url("nonexistent.txt")
        assert result.status == StorageStatus.NOT_FOUND

    def test_capabilities(self, provider):
        caps = provider.capabilities
        assert caps.public_urls
        assert caps.signed_urls
        assert caps.streaming

    def test_reset(self, provider):
        provider.upload("test.txt", b"hello")
        provider.reset()
        result = provider.exists("test.txt")
        assert result.status == StorageStatus.NOT_FOUND

    def test_upload_after_reset(self, provider):
        provider.upload("test.txt", b"hello")
        provider.reset()
        result = provider.upload("test.txt", b"world")
        assert result.status == StorageStatus.UPLOADED


class TestLocalStorageProvider:
    @pytest.fixture
    def tmpdir(self):
        with tempfile.TemporaryDirectory() as d:
            yield d

    @pytest.fixture
    def provider(self, tmpdir):
        config = StorageConfig(provider="local", base_path=tmpdir)
        return LocalStorageProvider(config)

    def test_upload_and_download(self, provider):
        result = provider.upload("test.txt", b"hello")
        assert result.status == StorageStatus.UPLOADED
        dl = provider.download("test.txt")
        assert dl.status == StorageStatus.DOWNLOADED
        assert dl.data == b"hello"

    def test_upload_nested_path(self, provider):
        result = provider.upload("dir/subdir/test.txt", b"nested")
        assert result.status == StorageStatus.UPLOADED
        dl = provider.download("dir/subdir/test.txt")
        assert dl.data == b"nested"

    def test_upload_rejects_path_traversal(self, provider):
        with pytest.raises(ValueError, match="Path traversal"):
            provider.upload("../outside.txt", b"bad")

    def test_download_nonexistent(self, provider):
        result = provider.download("nonexistent.txt")
        assert result.status == StorageStatus.NOT_FOUND

    def test_delete_existing(self, provider):
        provider.upload("test.txt", b"hello")
        result = provider.delete("test.txt")
        assert result.status == StorageStatus.DELETED

    def test_delete_nonexistent(self, provider):
        result = provider.delete("nonexistent.txt")
        assert result.status == StorageStatus.NOT_FOUND

    def test_exists(self, provider):
        provider.upload("test.txt", b"hello")
        assert provider.exists("test.txt").status == StorageStatus.EXISTS
        assert provider.exists("nope.txt").status == StorageStatus.NOT_FOUND

    def test_metadata(self, provider):
        provider.upload("test.txt", b"hello")
        result = provider.metadata("test.txt")
        assert result.status == StorageStatus.EXISTS
        assert result.object.size == 5

    def test_list(self, provider):
        provider.upload("a/1.txt", b"1")
        provider.upload("a/2.txt", b"2")
        provider.upload("b/3.txt", b"3")
        result = provider.list("a/")
        assert result.status == StorageStatus.EXISTS
        names = eval(result.data.decode())
        assert len(names) == 2

    def test_signed_url_unsupported(self, provider):
        result = provider.signed_url("test.txt")
        assert result.status == StorageStatus.FAILED

    def test_capabilities(self, provider):
        caps = provider.capabilities
        assert not caps.public_urls
        assert not caps.signed_urls
        assert caps.metadata


class TestCloudStorageProvider:
    @pytest.fixture
    def provider(self):
        config = StorageConfig(provider="cloud")
        return CloudStorageProvider(config)

    def test_all_operations_fail(self, provider):
        assert provider.upload("x", b"data").status == StorageStatus.FAILED
        assert provider.download("x").status == StorageStatus.FAILED
        assert provider.delete("x").status == StorageStatus.FAILED
        assert provider.exists("x").status == StorageStatus.FAILED
        assert provider.metadata("x").status == StorageStatus.FAILED
        assert provider.list().status == StorageStatus.FAILED
        assert provider.signed_url("x").status == StorageStatus.FAILED

    def test_capabilities(self, provider):
        caps = provider.capabilities
        assert caps.public_urls
        assert caps.signed_urls
        assert caps.multipart_upload

    def test_error_message(self, provider):
        result = provider.upload("x", b"data")
        assert "interface" in result.error.lower()


class TestProviderRegistry:
    def test_register_and_create(self):
        ProviderRegistry.register("test_provider", MockStorageProvider)
        config = StorageConfig(provider="test_provider")
        provider = ProviderRegistry.create("test_provider", config)
        assert isinstance(provider, MockStorageProvider)

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown storage provider"):
            ProviderRegistry.create("does_not_exist", StorageConfig())

    def test_available_includes_registered(self):
        available = ProviderRegistry.available()
        assert "mock" in available
        assert "local" in available
        assert "cloud" in available

    def test_get_returns_none_for_unknown(self):
        assert ProviderRegistry.get("nonexistent") is None

    def test_get_returns_class(self):
        cls = ProviderRegistry.get("mock")
        assert cls is MockStorageProvider


class TestGetProvider:
    def test_get_provider_default(self):
        provider = get_provider()
        assert isinstance(provider, MockStorageProvider)

    def test_get_provider_with_config(self):
        config = StorageConfig(provider="local", base_path="/tmp/test")
        provider = get_provider(config)
        assert isinstance(provider, LocalStorageProvider)

    def test_get_provider_unknown(self):
        config = StorageConfig(provider="nope")
        with pytest.raises(ValueError, match="Unknown storage provider"):
            get_provider(config)


class TestStorageService:
    def test_upload_returns_object(self):
        svc = StorageService()
        obj = svc.upload("test.txt", b"hello")
        assert isinstance(obj, StorageObject)
        assert obj.name == "test.txt"
        assert obj.size == 5

    def test_upload_with_content_type(self):
        svc = StorageService()
        obj = svc.upload("test.txt", b"hello", content_type="text/plain")
        assert obj.content_type == "text/plain"

    def test_upload_with_metadata(self):
        svc = StorageService()
        obj = svc.upload("test.txt", b"hello", metadata={"key": "val"})
        assert obj.metadata["key"] == "val"

    def test_download_returns_data(self):
        svc = StorageService()
        svc.upload("test.txt", b"hello")
        obj, data = svc.download("test.txt")
        assert data == b"hello"
        assert obj.name == "test.txt"

    def test_download_nonexistent_raises(self):
        svc = StorageService()
        with pytest.raises(StorageError, match="not found"):
            svc.download("nonexistent.txt")

    def test_delete(self):
        svc = StorageService()
        svc.upload("test.txt", b"hello")
        obj = svc.delete("test.txt")
        assert obj.name == "test.txt"

    def test_delete_nonexistent_raises(self):
        svc = StorageService()
        with pytest.raises(StorageError, match="not found"):
            svc.delete("nonexistent.txt")

    def test_exists_uploaded(self):
        svc = StorageService()
        svc.upload("test.txt", b"hello")
        assert svc.exists("test.txt")

    def test_exists_missing(self):
        svc = StorageService()
        assert not svc.exists("nope.txt")

    def test_exists_after_delete(self):
        svc = StorageService()
        svc.upload("test.txt", b"hello")
        svc.delete("test.txt")
        assert not svc.exists("test.txt")

    def test_metadata(self):
        svc = StorageService()
        svc.upload("test.txt", b"hello")
        obj = svc.metadata("test.txt")
        assert obj.size == 5

    def test_list(self):
        svc = StorageService()
        svc.upload("a/1.txt", b"1")
        svc.upload("a/2.txt", b"2")
        names = svc.list("a/")
        assert len(names) == 2
        assert "a/1.txt" in names

    def test_list_empty(self):
        svc = StorageService()
        names = svc.list("nonexistent/")
        assert names == []

    def test_signed_url(self):
        svc = StorageService()
        svc.upload("test.txt", b"hello")
        url = svc.signed_url("test.txt")
        assert url == "/mock/test.txt"

    def test_signed_url_nonexistent_raises(self):
        svc = StorageService()
        with pytest.raises(StorageError, match="not found"):
            svc.signed_url("nonexistent.txt")


class TestStorageValidation:
    def test_rejects_empty_name(self):
        svc = StorageService()
        with pytest.raises(StorageValidationError, match="name is required"):
            svc.upload("", b"data")

    def test_rejects_empty_data(self):
        svc = StorageService()
        with pytest.raises(StorageValidationError, match="empty"):
            svc.upload("test.txt", b"")

    def test_rejects_too_large_data(self):
        config = StorageConfig(max_upload_size_mb=1)
        svc = StorageService(config=config)
        with pytest.raises(StorageValidationError, match="too large"):
            svc.upload("test.txt", b"x" * (2 * 1024 * 1024))


class TestStorageServiceHealth:
    def test_health_returns_status(self):
        svc = StorageService()
        h = svc.health()
        assert isinstance(h, StorageHealth)
        assert h.provider == "mock"
        assert h.config_valid
        assert h.healthy

    def test_health_with_invalid_config(self):
        config = StorageConfig(provider="local")
        svc = StorageService(config=config)
        h = svc.health()
        assert not h.config_valid
        assert len(h.config_errors) > 0

    def test_health_has_bucket(self):
        svc = StorageService()
        h = svc.health()
        assert h.bucket == "alma"

    def test_health_with_local_provider(self):
        with tempfile.TemporaryDirectory() as d:
            config = StorageConfig(provider="local", base_path=d)
            svc = StorageService(config=config)
            h = svc.health()
            assert h.healthy


class TestStorageArchitectureBoundaries:
    def test_no_application_imports(self):
        import services.storage

        storage_dir = os.path.dirname(services.storage.__file__)
        for root, _dirs, files in os.walk(storage_dir):
            for f in files:
                if f.endswith(".py") and f != "__init__.py":
                    filepath = os.path.join(root, f)
                    with open(filepath) as fh:
                        content = fh.read()
                    assert (
                        "palmshed_ai" not in content
                    ), f"Application import found in {filepath}"

    def test_config_is_single_env_source(self):
        config = StorageConfig.from_env()
        assert hasattr(config, "from_env")
        assert hasattr(config, "is_valid")

    def test_mock_provider_extends_base(self):
        from services.storage.providers import StorageProvider as SP

        assert issubclass(MockStorageProvider, SP)

    def test_local_provider_extends_base(self):
        from services.storage.providers import StorageProvider as SP

        assert issubclass(LocalStorageProvider, SP)

    def test_cloud_provider_extends_base(self):
        from services.storage.providers import StorageProvider as SP

        assert issubclass(CloudStorageProvider, SP)

    def test_provider_capabilities_defined(self):
        caps = ProviderCapabilities()
        assert hasattr(caps, "public_urls")
        assert hasattr(caps, "signed_urls")
        assert hasattr(caps, "multipart_upload")
        assert hasattr(caps, "versioning")
        assert hasattr(caps, "metadata")
        assert hasattr(caps, "streaming")
