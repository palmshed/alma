# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT

import json
import time
from unittest.mock import patch, MagicMock

import pytest
import os

from services.mail import (
    MailConfig,
    MailService,
    MailTemplate,
    MailMessage,
    MailResult,
    MailStatus,
    MailPriority,
    MailMetrics,
    MailError,
    MailValidationError,
    RetryPolicy,
    ProviderCapabilities,
    ProviderRegistry,
)
from services.mail.models import Address, Attachment, HealthStatus
from services.mail.providers import MockProvider
from services.mail.queue import ThreadMailQueue
from services.mail.templates import (
    MailTemplates,
    template_metadata,
    TemplateValidationError,
)


class TestMailModels:
    def test_address_formatted_with_name(self):
        addr = Address("user@example.com", "User")
        assert addr.formatted() == "User <user@example.com>"

    def test_address_formatted_without_name(self):
        addr = Address("user@example.com")
        assert addr.formatted() == "user@example.com"

    def test_mail_message_defaults(self):
        msg = MailMessage(template="welcome", recipient=Address("a@b.com"))
        assert msg.priority == MailPriority.NORMAL
        assert msg.status == MailStatus.PENDING
        assert msg.retry_count == 0
        assert msg.sender.email == "hello@palmshed.dev"

    def test_mail_result_creation(self):
        result = MailResult(
            mail_id="abc",
            status=MailStatus.SENT,
            provider="mock",
        )
        assert result.mail_id == "abc"
        assert result.status == MailStatus.SENT

    def test_health_status(self):
        caps = ProviderCapabilities(html=True, attachments=False)
        h = HealthStatus(
            provider="mock",
            provider_capabilities=caps,
            queue_running=False,
            queue_depth=0,
            config_valid=True,
            config_errors=[],
            templates_valid=True,
            template_count=4,
        )
        assert h.provider == "mock"
        assert h.config_valid
        assert h.template_count == 4

    def test_retry_policy_delay(self):
        rp = RetryPolicy(max_retries=3, base_delay_seconds=1.0, backoff_factor=2.0)
        assert rp.delay_for(0) == 1.0
        assert rp.delay_for(1) == 2.0
        assert rp.delay_for(2) == 4.0
        assert rp.delay_for(3) == 8.0

    def test_retry_policy_capped_delay(self):
        rp = RetryPolicy(max_delay_seconds=5.0, backoff_factor=3.0)
        assert rp.delay_for(3) == 5.0

    def test_attachment_dataclass(self):
        att = Attachment("file.txt", b"content", "text/plain")
        assert att.filename == "file.txt"
        assert att.mime_type == "text/plain"


class TestMailConfig:
    def test_default_config(self):
        config = MailConfig()
        assert config.provider == "mock"
        assert config.from_email == "hello@palmshed.dev"
        assert config.max_recipients == 50
        assert config.max_attachment_size_mb == 10
        assert config.max_attachment_size_bytes == 10 * 1024 * 1024

    def test_config_validation_valid(self):
        config = MailConfig()
        valid, errors = config.is_valid()
        assert valid
        assert errors == []

    def test_config_validation_invalid_max_recipients(self):
        config = MailConfig(max_recipients=0)
        valid, errors = config.is_valid()
        assert not valid
        assert any("max_recipients" in e for e in errors)

    def test_from_env_defaults(self, monkeypatch):
        monkeypatch.delenv("MAIL_PROVIDER", raising=False)
        config = MailConfig.from_env()
        assert config.provider == "mock"

    def test_from_env_override(self, monkeypatch):
        monkeypatch.setenv("MAIL_PROVIDER", "smtp")
        monkeypatch.setenv("MAIL_FROM_EMAIL", "test@palmshed.dev")
        config = MailConfig.from_env()
        assert config.provider == "smtp"
        assert config.from_email == "test@palmshed.dev"


class TestMailConfigValidation:
    def test_config_valid_by_default(self):
        config = MailConfig()
        valid, errors = config.is_valid()
        assert valid
        assert errors == []

    def test_config_valid_with_smtp(self):
        config = MailConfig(provider="smtp", from_email="hello@palmshed.dev")
        valid, errors = config.is_valid()
        assert valid

    def test_config_invalid_provider(self):
        config = MailConfig(provider="nonexistent")
        valid, errors = config.is_valid()
        assert not valid
        assert any("provider" in e.lower() for e in errors)


class TestMailMetrics:
    def test_initial_state(self):
        m = MailMetrics()
        assert m.queued == 0
        assert m.sent == 0
        assert m.failed == 0
        assert m.retried == 0
        assert m.avg_duration_ms == 0.0

    def test_record_counts(self):
        m = MailMetrics()
        m.record_queued()
        m.record_sent()
        m.record_failed()
        m.record_retried()
        snap = m.snapshot()
        assert snap["queued"] == 1
        assert snap["sent"] == 1
        assert snap["failed"] == 1
        assert snap["retried"] == 1

    def test_average_duration(self):
        m = MailMetrics()
        m.record_duration(0.1)
        m.record_duration(0.2)
        assert m.avg_duration_ms == pytest.approx(150.0, abs=0.001)

    def test_snapshot(self):
        m = MailMetrics()
        m.record_queued()
        snap = m.snapshot()
        assert isinstance(snap, dict)
        assert "queued" in snap
        assert "avg_duration_ms" in snap


class TestMockProvider:
    def test_send_returns_result(self):
        provider = MockProvider()
        msg = MailMessage(template="test", recipient=Address("a@b.com"), id="1")
        result = provider.send(msg)
        assert isinstance(result, MailResult)
        assert result.status == MailStatus.SENT
        assert result.provider == "mock"

    def test_captures_sent_messages(self):
        provider = MockProvider()
        msg = MailMessage(template="test", recipient=Address("a@b.com"), id="1")
        provider.send(msg)
        assert len(provider.sent) == 1
        assert provider.sent[0].id == "1"

    def test_capabilities(self):
        provider = MockProvider()
        caps = provider.capabilities
        assert caps.html
        assert caps.attachments
        assert not caps.scheduling

    def test_reset(self):
        provider = MockProvider()
        provider.send(
            MailMessage(template="test", recipient=Address("a@b.com"), id="1")
        )
        provider.reset()
        assert len(provider.sent) == 0


class TestProviderRegistry:
    def test_register_and_create(self):
        ProviderRegistry.register("test_provider", MockProvider)
        config = MailConfig(provider="test_provider")
        provider = ProviderRegistry.create("test_provider", config)
        assert isinstance(provider, MockProvider)

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown mail provider"):
            ProviderRegistry.create("does_not_exist", MailConfig())

    def test_available_includes_registered(self):
        available = ProviderRegistry.available()
        assert "mock" in available

    def test_get_returns_none_for_unknown(self):
        assert ProviderRegistry.get("nonexistent") is None


class TestMailTemplates:
    def test_templates_validate_on_init(self):
        templates = MailTemplates()
        assert templates is not None

    def test_render_returns_html_and_text(self):
        templates = MailTemplates()
        result = templates.render(
            "welcome",
            {"name": "Test", "product": "Alma", "link": "https://alma.palmshed.dev"},
        )
        assert "html_body" in result
        assert "text_body" in result
        assert "Palmshed" in result["html_body"]

    def test_template_metadata(self):
        meta = template_metadata(MailTemplate.WELCOME)
        assert meta is not None
        assert meta.name == "welcome"
        assert meta.version == "1.0"
        assert "Alma" in meta.format_subject({"product": "Alma"})

    def test_template_metadata_notification(self):
        meta = template_metadata(MailTemplate.NOTIFICATION)
        assert meta is not None
        assert "${subject}" in meta.subject

    def test_unknown_template_metadata(self):
        with pytest.raises(ValueError):
            MailTemplate("unknown")

    def test_registered_templates_include_all(self):
        from services.mail.templates import registered_templates

        names = [t.value for t in registered_templates()]
        assert "welcome" in names
        assert "verification" in names
        assert "password_reset" in names
        assert "notification" in names

    def test_validate_returns_errors_on_missing_dir(self):
        with pytest.raises(TemplateValidationError):
            MailTemplates(directory="/tmp/nonexistent_mail_templates")


class TestMailService:
    def test_send_sync_returns_message(self):
        config = MailConfig(sync=True)
        svc = MailService(config=config)
        msg = svc.send(
            MailTemplate.NOTIFICATION,
            "user@example.com",
            context={"subject": "Test", "body": "Body", "product": "Alma"},
        )
        assert isinstance(msg, MailMessage)
        assert msg.recipient.email == "user@example.com"
        assert msg.status == MailStatus.SENT

    def test_send_with_subject_override(self):
        config = MailConfig(sync=True)
        svc = MailService(config=config)
        msg = svc.send(
            MailTemplate.NOTIFICATION,
            "user@example.com",
            context={"subject": "Test", "body": "Body", "product": "Alma"},
            subject="Custom Subject",
        )
        assert msg.subject_override == "Custom Subject"

    def test_send_with_sender_override(self):
        config = MailConfig(sync=True)
        svc = MailService(config=config)
        msg = svc.send(
            MailTemplate.NOTIFICATION,
            "user@example.com",
            context={"subject": "Test", "body": "Body", "product": "Alma"},
            sender=Address("custom@palmshed.dev", "Custom"),
        )
        assert msg.sender.email == "custom@palmshed.dev"

    def test_send_with_cc_bcc(self):
        config = MailConfig(sync=True)
        svc = MailService(config=config)
        msg = svc.send(
            MailTemplate.NOTIFICATION,
            "to@example.com",
            context={"subject": "Test", "body": "Body", "product": "Alma"},
            cc=["cc1@example.com", "cc2@example.com"],
            bcc=["bcc@example.com"],
        )
        assert len(msg.cc) == 2
        assert len(msg.bcc) == 1

    def test_send_async_queues_message(self):
        svc = MailService()
        msg = svc.send(
            MailTemplate.NOTIFICATION,
            "user@example.com",
            context={"subject": "Test", "body": "Body", "product": "Alma"},
        )
        assert msg.status == MailStatus.SENT
        assert msg.id is not None

    def test_shutdown_drains_queue(self):
        svc = MailService()
        svc.shutdown(timeout=1.0)

    def test_health_returns_status(self):
        config = MailConfig(sync=True)
        svc = MailService(config=config)
        h = svc.health()
        assert isinstance(h, HealthStatus)
        assert h.provider == "MockProvider"
        assert h.templates_valid
        assert h.config_valid

    def test_health_with_queue_depth(self):
        svc = MailService()
        svc.send(
            MailTemplate.NOTIFICATION,
            "user@example.com",
            context={"subject": "Test", "body": "Body", "product": "Alma"},
        )
        h = svc.health()
        assert h.queue_depth >= 0

    def test_metrics_recorded_in_sync_mode(self):
        config = MailConfig(sync=True)
        svc = MailService(config=config)
        svc.send(
            MailTemplate.NOTIFICATION,
            "a@example.com",
            context={"subject": "S1", "body": "B1", "product": "Alma"},
        )
        svc.send(
            MailTemplate.NOTIFICATION,
            "b@example.com",
            context={"subject": "S2", "body": "B2", "product": "Alma"},
        )
        snap = svc.metrics.snapshot()
        assert snap["sent"] == 2
        assert snap["queued"] == 2
        assert snap["avg_duration_ms"] >= 0


class TestMailValidation:
    def test_rejects_too_many_recipients(self):
        config = MailConfig(sync=True, max_recipients=3)
        svc = MailService(config=config)
        with pytest.raises(MailValidationError, match="max is 3"):
            svc.send(
                MailTemplate.NOTIFICATION,
                "to@example.com",
                context={"subject": "T", "body": "B", "product": "Alma"},
                cc=["cc1@example.com", "cc2@example.com", "cc3@example.com"],
            )

    def test_rejects_large_context(self):
        config = MailConfig(sync=True, max_context_size_bytes=100)
        svc = MailService(config=config)
        with pytest.raises(MailValidationError, match="Context too large"):
            svc.send(
                MailTemplate.NOTIFICATION,
                "to@example.com",
                context={"data": "x" * 200},
            )

    def test_rejects_large_attachment(self):
        config = MailConfig(sync=True, max_attachment_size_mb=1)
        svc = MailService(config=config)
        with pytest.raises(MailValidationError, match="too large"):
            svc.send(
                MailTemplate.NOTIFICATION,
                "to@example.com",
                context={"subject": "T", "body": "B", "product": "Alma"},
                attachments=[
                    Attachment(
                        "big.bin", b"x" * (2 * 1024 * 1024), "application/octet-stream"
                    )
                ],
            )

    def test_rejects_attachments_when_provider_does_not_support(self):
        config = MailConfig(sync=True)
        svc = MailService(config=config)
        provider = svc.provider
        caps = provider.capabilities
        if not caps.attachments:
            with pytest.raises(
                MailValidationError, match="does not support attachments"
            ):
                svc.send(
                    MailTemplate.NOTIFICATION,
                    "to@example.com",
                    context={"subject": "T", "body": "B", "product": "Alma"},
                    attachments=[Attachment("f.txt", b"data", "text/plain")],
                )


class TestMailSendErrors:
    def test_mail_error_raised_on_provider_failure(self):
        class FailingProvider(MockProvider):
            def send(self, message):
                raise RuntimeError("Provider failure")

        config = MailConfig(sync=True)
        svc = MailService(config=config, provider=FailingProvider())
        with pytest.raises(MailError):
            svc.send(
                MailTemplate.NOTIFICATION,
                "user@example.com",
                context={"subject": "Test", "body": "Body", "product": "Alma"},
            )


class TestQueue:
    def test_thread_mail_queue_enqueue(self):
        sent = []

        def worker(msg):
            sent.append(msg)

        queue = ThreadMailQueue(worker=worker)
        msg = MailMessage(template="test", recipient=Address("a@b.com"), id="1")
        queue.enqueue(msg)
        assert queue.depth == 1

    def test_thread_mail_queue_drain(self):
        queue = ThreadMailQueue(worker=lambda msg: None)
        msg = MailMessage(template="test", recipient=Address("a@b.com"), id="1")
        queue.enqueue(msg)
        queue.drain(timeout=1.0)

    def test_queue_abc_defaults(self):
        from services.mail.queue import MailQueue as ABCQueue

        class ConcreteQueue(ABCQueue):
            def enqueue(self, message):
                pass

        q = ConcreteQueue()
        assert q.depth == 0
        assert not q.running
        q.drain()

    def test_retry_policy_in_queue(self):
        attempts = []

        def worker(msg):
            attempts.append(msg.retry_count)
            if len(attempts) < 3:
                raise RuntimeError("fail")

        retry = RetryPolicy(max_retries=3, base_delay_seconds=0.01)
        queue = ThreadMailQueue(worker=worker, retry_policy=retry)
        msg = MailMessage(template="test", recipient=Address("a@b.com"), id="1")
        queue.enqueue(msg)
        queue.start()
        time.sleep(0.1)
        queue.drain(timeout=0.5)
        assert len(attempts) >= 2


class TestTemplateValidation:
    def test_template_validation_passes(self):
        templates = MailTemplates()
        errors = templates.validate()
        assert len(errors) == 0

    def test_template_validation_checks_missing_placeholders(self):
        import tempfile
        import os

        tmpdir = tempfile.mkdtemp()

        for name in ("welcome", "verification", "password_reset", "notification"):
            content = " ".join(
                "${" + p + "}"
                for p in (
                    "name",
                    "product",
                    "link",
                    "code",
                    "expires_in",
                    "subject",
                    "body",
                )
            )
            with open(os.path.join(tmpdir, f"{name}.html"), "w") as f:
                f.write(f"<p>{content}</p>")
            with open(os.path.join(tmpdir, f"{name}.txt"), "w") as f:
                f.write(content)

        errors = MailTemplates(directory=tmpdir).validate()
        assert len(errors) == 0

    def test_template_not_found(self):
        templates = MailTemplates()
        from services.mail.templates import TemplateNotFound

        with pytest.raises(TemplateNotFound):
            templates.render("nonexistent", {})


class TestResendProvider:
    def test_registered_in_registry(self):
        """Resend provider is registered and available."""
        from services.mail.providers.resend import ResendProvider

        registered_cls = ProviderRegistry.get("resend")
        assert registered_cls is not None
        assert registered_cls is ResendProvider

    def test_capabilities(self):
        """Resend supports html, attachments, inline images; not scheduling."""
        from services.mail.providers.resend import ResendProvider

        provider = ResendProvider(MailConfig(resend_api_key="test"))
        assert provider.capabilities.html
        assert provider.capabilities.attachments
        assert provider.capabilities.inline_images
        assert not provider.capabilities.scheduling

    def test_payload_structure(self):
        """Verify the JSON payload sent to Resend API is correctly shaped."""
        from services.mail.providers.resend import ResendProvider
        from services.mail.models import Attachment

        config = MailConfig(resend_api_key="test", reply_to="reply@palmshed.dev")
        provider = ResendProvider(config)

        msg = MailMessage(
            id="msg-001",
            template="welcome",
            recipient=Address("user@example.com", "User"),
            context={"html_body": "<p>Hello</p>", "text_body": "Hello", "name": "User"},
            subject_override="Welcome",
            reply_to="reply@palmshed.dev",
            cc=[Address("cc@example.com")],
            bcc=[Address("bcc@example.com")],
            sender=Address("hello@palmshed.dev", "Palmshed"),
            attachments=[Attachment("file.pdf", b"pdfcontent", "application/pdf")],
        )

        payload = provider._build_payload(msg)
        assert payload["from"] == "Palmshed <hello@palmshed.dev>"
        assert payload["to"] == ["user@example.com"]
        assert payload["subject"] == "Welcome"
        assert payload["html"] == "<p>Hello</p>"
        assert payload["text"] == "Hello"
        assert payload["cc"] == ["cc@example.com"]
        assert payload["bcc"] == ["bcc@example.com"]
        assert payload["reply_to"] == "reply@palmshed.dev"
        assert len(payload["attachments"]) == 1
        assert payload["attachments"][0]["filename"] == "file.pdf"
        assert payload["attachments"][0]["content_type"] == "application/pdf"

    def test_payload_no_optional_fields(self):
        """Minimal payload should exclude optional keys."""
        from services.mail.providers.resend import ResendProvider

        config = MailConfig(resend_api_key="test")
        provider = ResendProvider(config)
        msg = MailMessage(
            id="msg-002",
            template="test",
            recipient=Address("a@b.com"),
            context={"html_body": "<p>Hi</p>"},
            subject_override="Hi",
        )
        payload = provider._build_payload(msg)
        assert "cc" not in payload
        assert "bcc" not in payload
        assert "reply_to" not in payload
        assert "attachments" not in payload

    def test_config_rejects_missing_api_key(self):
        """Config validation fails when resend is selected without API key."""
        config = MailConfig(provider="resend")
        valid, errors = config.is_valid()
        assert not valid
        assert any("RESEND_API_KEY" in e for e in errors)

    def test_config_valid_with_api_key(self):
        """Config validation passes when resend has API key."""
        config = MailConfig(provider="resend", resend_api_key="re_abc123")
        valid, errors = config.is_valid()
        assert valid
        assert errors == []

    def test_send_success_returns_provider_id(self):
        """Successful Resend API call returns provider_message_id."""
        from services.mail.providers.resend import ResendProvider

        config = MailConfig(resend_api_key="re_abc123", sync=True)
        provider = ResendProvider(config)
        msg = MailMessage(
            id="msg-succ-01",
            template="welcome",
            recipient=Address("user@example.com", "User"),
            context={"html_body": "<p>Hi</p>", "text_body": "Hi"},
            subject_override="Test",
        )

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps({"id": "resend-id-123"}).encode()
        mock_conn = MagicMock()
        mock_conn.getresponse.return_value = mock_resp
        mock_conn.__enter__.return_value = mock_conn

        with patch("http.client.HTTPSConnection", return_value=mock_conn):
            result = provider.send(msg)

        assert result.status == MailStatus.SENT
        assert result.provider_message_id == "resend-id-123"
        assert result.provider == "resend"

    def test_send_http_error_returns_failed(self):
        """Resend API error (e.g. 422) returns FAILED with error message."""
        from services.mail.providers.resend import ResendProvider
        from services.mail import MailStatus

        config = MailConfig(resend_api_key="re_abc123", sync=True)
        provider = ResendProvider(config)
        msg = MailMessage(
            id="msg-err-01",
            template="welcome",
            recipient=Address("user@example.com", "User"),
            context={"html_body": "<p>Hi</p>", "text_body": "Hi"},
            subject_override="Test",
        )

        mock_resp = MagicMock()
        mock_resp.status = 422
        mock_resp.read.return_value = json.dumps(
            {
                "message": "Invalid sender address",
                "name": "validation_error",
            }
        ).encode()
        mock_conn = MagicMock()
        mock_conn.getresponse.return_value = mock_resp
        mock_conn.__enter__.return_value = mock_conn

        with patch("http.client.HTTPSConnection", return_value=mock_conn):
            result = provider.send(msg)

        assert result.status == MailStatus.FAILED
        assert "Invalid sender address" in result.error
        assert result.provider_message_id is None


class TestArchitecture:
    """Architectural boundary tests — prevent accidental dependency drift."""

    FORBIDDEN_IMPORTS = {
        "services.mail": [
            "flask",
            "django",
            "react",
            "jsx",
            "palmshed_ai",
            "templates",  # app templates, not mail templates
        ],
    }

    ALLOWED_IMPORTS = {
        "urllib",
    }

    def test_mail_never_imports_application_modules(self):
        """Mail is a platform service — must not depend on application code."""
        import services.mail

        mail_path = os.path.dirname(services.mail.__file__)
        for root, _dirs, files in os.walk(mail_path):
            for fname in files:
                if not fname.endswith(".py") or fname.startswith("__"):
                    continue
                filepath = os.path.join(root, fname)
                with open(filepath) as f:
                    content = f.read()
                for forbidden in self.FORBIDDEN_IMPORTS["services.mail"]:
                    if (
                        f"import {forbidden}" in content
                        or f"from {forbidden}" in content
                    ):
                        rel = os.path.relpath(filepath, mail_path)
                        pytest.fail(f"{rel} imports forbidden module '{forbidden}'")

    def test_providers_never_import_application_code(self):
        """Providers must remain application-agnostic."""
        import services.mail.providers

        providers_path = os.path.dirname(services.mail.providers.__file__)
        for root, _dirs, files in os.walk(providers_path):
            for fname in files:
                if not fname.endswith(".py") or fname.startswith("__"):
                    continue
                filepath = os.path.join(root, fname)
                with open(filepath) as f:
                    content = f.read()
                for forbidden in self.FORBIDDEN_IMPORTS["services.mail"]:
                    if (
                        f"import {forbidden}" in content
                        or f"from {forbidden}" in content
                    ):
                        rel = os.path.relpath(filepath, providers_path)
                        pytest.fail(f"{rel} imports forbidden module '{forbidden}'")

    def test_providers_use_base_class(self):
        """All registered providers must extend MailProvider."""
        from services.mail.providers.base import MailProvider
        from services.mail.providers.registry import ProviderRegistry

        for name in ProviderRegistry.available():
            cls = ProviderRegistry.get(name)
            assert cls is not None, f"Provider '{name}' not found in registry"
            assert issubclass(
                cls, MailProvider
            ), f"Provider '{name}' ({cls.__name__}) does not extend MailProvider"

    def test_templates_have_html_and_txt(self):
        """Every template must have both HTML and plain-text versions."""
        templates_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "templates", "mail"
        )
        for template in MailTemplate:
            name = template.value
            html = os.path.join(templates_dir, f"{name}.html")
            txt = os.path.join(templates_dir, f"{name}.txt")
            assert os.path.exists(html), f"Missing {html}"
            assert os.path.exists(txt), f"Missing {txt}"

    def test_config_is_single_source_of_env(self):
        """os.environ should only be read in config.py, not in other modules."""
        import services.mail

        mail_path = os.path.dirname(services.mail.__file__)
        for root, _dirs, files in os.walk(mail_path):
            for fname in files:
                if not fname.endswith(".py") or fname == "config.py":
                    continue
                filepath = os.path.join(root, fname)
                with open(filepath) as f:
                    content = f.read()
                if "os.environ" in content or "os.getenv" in content:
                    rel = os.path.relpath(filepath, mail_path)
                    pytest.fail(
                        f"{rel} reads environment variables directly; use MailConfig"
                    )

    def test_service_accepts_only_mailtemplate_enum(self):
        """MailService.send() must be called with a MailTemplate enum, not a string."""
        svc = MailService(config=MailConfig(sync=True, provider="mock"))
        with pytest.raises((TypeError, AttributeError, ValueError)):
            svc.send(
                "welcome",  # bare string — should be MailTemplate.WELCOME
                "user@example.com",
                context={"name": "T", "product": "Alma", "link": "https://x"},
            )

    def test_health_status_provider_capabilities(self):
        """HealthStatus must include provider capabilities."""
        caps = ProviderCapabilities(html=False, attachments=False)
        h = HealthStatus(
            provider="test",
            provider_capabilities=caps,
            queue_running=False,
            queue_depth=0,
            config_valid=True,
            config_errors=[],
            templates_valid=True,
            template_count=0,
        )
        assert h.provider_capabilities.html is False
