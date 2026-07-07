# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT

import io
import os
import uuid

import pytest

from palmshed_ai import create_app

os.environ["GEMINI_API_KEY"] = "dummy"


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


PNG_HEADER = b"\x89PNG\r\n\x1a\n"


class TestAttachmentUpload:
    def test_upload_png(self, client):
        data = {"file": (io.BytesIO(PNG_HEADER + b"fake-data"), "photo.png")}
        resp = client.post(
            "/api/attachments",
            data=data,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["filename"] == "photo.png"
        assert body["mime_type"] == "image/png"
        assert body["size"] == len(PNG_HEADER + b"fake-data")
        assert "id" in body
        assert "checksum" in body
        assert uuid.UUID(body["id"])

    def test_upload_jpeg(self, client):
        data = {"file": (io.BytesIO(b"fake-jpeg"), "photo.jpg", "image/jpeg")}
        resp = client.post(
            "/api/attachments",
            data=data,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["mime_type"] == "image/jpeg"

    def test_upload_pdf(self, client):
        data = {
            "file": (io.BytesIO(b"%PDF-1.4 fake"), "doc.pdf", "application/pdf")
        }
        resp = client.post(
            "/api/attachments",
            data=data,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["mime_type"] == "application/pdf"

    def test_upload_text(self, client):
        data = {
            "file": (io.BytesIO(b"hello world"), "notes.txt", "text/plain")
        }
        resp = client.post(
            "/api/attachments",
            data=data,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["mime_type"] == "text/plain"

    def test_upload_markdown(self, client):
        data = {
            "file": (
                io.BytesIO(b"# Hello"),
                "readme.md",
                "text/markdown",
            )
        }
        resp = client.post(
            "/api/attachments",
            data=data,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["mime_type"] == "text/markdown"

    def test_upload_checksum_sha256(self, client):
        content = b"hello-world-checksum"
        data = {"file": (io.BytesIO(content), "test.txt", "text/plain")}
        resp = client.post(
            "/api/attachments",
            data=data,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 201
        body = resp.get_json()
        import hashlib
        expected = hashlib.sha256(content).hexdigest()
        assert body["checksum"] == expected


class TestAttachmentUploadErrors:
    def test_no_file(self, client):
        resp = client.post(
            "/api/attachments",
            data={},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
        assert "No file" in resp.get_json()["error"]

    def test_empty_filename(self, client):
        data = {"file": (io.BytesIO(b"data"), "", "text/plain")}
        resp = client.post(
            "/api/attachments",
            data=data,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
        assert "No file" in resp.get_json()["error"]

    def test_empty_file(self, client):
        data = {"file": (io.BytesIO(b""), "empty.txt", "text/plain")}
        resp = client.post(
            "/api/attachments",
            data=data,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
        assert "Empty" in resp.get_json()["error"]

    def test_unsupported_mime_type(self, client):
        data = {
            "file": (
                io.BytesIO(b"<html></html>"),
                "page.html",
                "text/html",
            )
        }
        resp = client.post(
            "/api/attachments",
            data=data,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 415
        assert "Unsupported" in resp.get_json()["error"]

    def test_file_too_large(self, client):
        large_data = b"x" * (10 * 1024 * 1024 + 1)
        data = {"file": (io.BytesIO(large_data), "large.bin", "text/plain")}
        resp = client.post(
            "/api/attachments",
            data=data,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 413
        assert "too large" in resp.get_json()["error"]


class TestAttachmentDownload:
    def test_download_returns_file(self, client):
        content = b"downloadable-content"
        data = {"file": (io.BytesIO(content), "download.txt", "text/plain")}
        upload_resp = client.post(
            "/api/attachments",
            data=data,
            content_type="multipart/form-data",
        )
        att_id = upload_resp.get_json()["id"]

        download_resp = client.get(f"/api/attachments/{att_id}")
        assert download_resp.status_code == 200
        assert download_resp.data == content
        assert download_resp.content_type.startswith("text/plain")

    def test_download_nonexistent(self, client):
        resp = client.get("/api/attachments/nonexistent-id")
        assert resp.status_code == 404


class TestAttachmentMetadata:
    def test_get_metadata(self, client):
        content = b"metadata-test"
        data = {"file": (io.BytesIO(content), "meta.txt", "text/plain")}
        upload_resp = client.post(
            "/api/attachments",
            data=data,
            content_type="multipart/form-data",
        )
        body = upload_resp.get_json()
        att_id = body["id"]

        meta_resp = client.get(f"/api/attachments/{att_id}/metadata")
        assert meta_resp.status_code == 200
        meta = meta_resp.get_json()
        assert meta["id"] == att_id
        assert meta["filename"] == "meta.txt"
        assert meta["mime_type"] == "text/plain"
        assert meta["size"] == len(content)
        assert "checksum" in meta
        assert "created_at" in meta

    def test_get_metadata_nonexistent(self, client):
        resp = client.get("/api/attachments/nonexistent/metadata")
        assert resp.status_code == 404


class TestAttachmentDelete:
    def test_delete_attachment(self, client):
        data = {"file": (io.BytesIO(b"to-delete"), "delete.txt", "text/plain")}
        upload_resp = client.post(
            "/api/attachments",
            data=data,
            content_type="multipart/form-data",
        )
        att_id = upload_resp.get_json()["id"]

        del_resp = client.delete(f"/api/attachments/{att_id}")
        assert del_resp.status_code == 204

        get_resp = client.get(f"/api/attachments/{att_id}")
        assert get_resp.status_code == 404

    def test_delete_nonexistent(self, client):
        resp = client.delete("/api/attachments/nonexistent")
        assert resp.status_code == 404

    def test_delete_twice(self, client):
        data = {"file": (io.BytesIO(b"twice"), "twice.txt", "text/plain")}
        upload_resp = client.post(
            "/api/attachments",
            data=data,
            content_type="multipart/form-data",
        )
        att_id = upload_resp.get_json()["id"]

        client.delete(f"/api/attachments/{att_id}")
        resp = client.delete(f"/api/attachments/{att_id}")
        assert resp.status_code == 404


class TestAttachmentWorkflow:
    def test_upload_download_delete_cycle(self, client):
        content = b"full-cycle-test"
        upload_resp = client.post(
            "/api/attachments",
            data={"file": (io.BytesIO(content), "cycle.txt", "text/plain")},
            content_type="multipart/form-data",
        )
        assert upload_resp.status_code == 201
        att_id = upload_resp.get_json()["id"]

        meta_resp = client.get(f"/api/attachments/{att_id}/metadata")
        assert meta_resp.status_code == 200

        download_resp = client.get(f"/api/attachments/{att_id}")
        assert download_resp.status_code == 200
        assert download_resp.data == content

        del_resp = client.delete(f"/api/attachments/{att_id}")
        assert del_resp.status_code == 204

        get_resp = client.get(f"/api/attachments/{att_id}")
        assert get_resp.status_code == 404

    def test_multiple_uploads_isolation(self, client):
        ids = []
        for i in range(3):
            content = f"file-{i}".encode()
            data = {
                "file": (
                    io.BytesIO(content),
                    f"file{i}.txt",
                    "text/plain",
                )
            }
            resp = client.post(
                "/api/attachments",
                data=data,
                content_type="multipart/form-data",
            )
            assert resp.status_code == 201
            ids.append(resp.get_json()["id"])

        # delete the middle one
        client.delete(f"/api/attachments/{ids[1]}")

        assert client.get(f"/api/attachments/{ids[0]}").status_code == 200
        assert client.get(f"/api/attachments/{ids[1]}").status_code == 404
        assert client.get(f"/api/attachments/{ids[2]}").status_code == 200
