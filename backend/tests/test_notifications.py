# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT

import os

import pytest

from services.notifications import (
    NotificationConfig,
    NotificationService,
    Notification,
    NotificationResult,
    NotificationStatus,
    NotificationPriority,
    NotificationMetrics,
    NotificationHealth,
    ChannelCapabilities,
    ChannelRegistry,
)
from services.notifications.channels import (
    MockChannel,
    EmailChannel,
    WebhookChannel,
    get_channel,
)


class TestNotificationModels:
    def test_notification_defaults(self):
        n = Notification(
            id="1",
            channel="email",
            recipient="a@b.com",
            subject="Hi",
            body="Hello",
        )
        assert n.priority == NotificationPriority.NORMAL
        assert n.status == NotificationStatus.PENDING
        assert n.metadata == {}

    def test_notification_with_all_fields(self):
        n = Notification(
            id="1",
            channel="webhook",
            recipient="a@b.com",
            subject="Hi",
            body="Hello",
            body_html="<p>Hello</p>",
            priority=NotificationPriority.HIGH,
            metadata={"key": "val"},
        )
        assert n.body_html == "<p>Hello</p>"
        assert n.priority == NotificationPriority.HIGH

    def test_notification_result_creation(self):
        result = NotificationResult(
            notification_id="abc",
            channel="email",
            status=NotificationStatus.SENT,
        )
        assert result.notification_id == "abc"
        assert result.status == NotificationStatus.SENT

    def test_notification_health(self):
        h = NotificationHealth(channels={"mock": "ok", "email": "ok"})
        assert h.channels["mock"] == "ok"
        assert h.enabled

    def test_notification_health_disabled(self):
        h = NotificationHealth(enabled=False)
        assert not h.enabled


class TestNotificationConfig:
    def test_default_config(self):
        config = NotificationConfig()
        assert config.enabled
        assert config.default_channel == "mock"
        assert config.webhook_timeout == 10

    def test_config_validation_valid(self):
        config = NotificationConfig()
        valid, errors = config.is_valid()
        assert valid

    def test_config_validation_invalid_channel(self):
        config = NotificationConfig(default_channel="nonexistent")
        valid, errors = config.is_valid()
        assert not valid

    def test_config_validation_webhook_no_url(self):
        config = NotificationConfig(default_channel="webhook")
        valid, errors = config.is_valid()
        assert not valid

    def test_config_validation_webhook_with_url(self):
        config = NotificationConfig(
            default_channel="webhook", webhook_url="https://hooks.example.com"
        )
        valid, errors = config.is_valid()
        assert valid

    def test_from_env_defaults(self, monkeypatch):
        monkeypatch.delenv("NOTIFICATIONS_ENABLED", raising=False)
        config = NotificationConfig.from_env()
        assert config.enabled

    def test_from_env_override(self, monkeypatch):
        monkeypatch.setenv("NOTIFICATIONS_DEFAULT_CHANNEL", "webhook")
        monkeypatch.setenv("NOTIFICATIONS_WEBHOOK_URL", "https://hooks.example.com")
        config = NotificationConfig.from_env()
        assert config.default_channel == "webhook"


class TestNotificationMetrics:
    def test_initial_state(self):
        m = NotificationMetrics()
        assert m.sent == 0
        assert m.failed == 0
        assert m.bounced == 0

    def test_record_counts(self):
        m = NotificationMetrics()
        m.record_sent()
        m.record_failed()
        m.record_bounced()
        snap = m.snapshot()
        assert snap["sent"] == 1
        assert snap["failed"] == 1
        assert snap["bounced"] == 1

    def test_average_duration(self):
        m = NotificationMetrics()
        m.record_duration(0.1)
        m.record_duration(0.2)
        assert m.avg_duration_ms == pytest.approx(150.0, abs=0.001)


class TestChannelCapabilities:
    def test_default_capabilities(self):
        caps = ChannelCapabilities()
        assert not caps.html
        assert not caps.attachments
        assert not caps.batch

    def test_custom_capabilities(self):
        caps = ChannelCapabilities(html=True, attachments=True)
        assert caps.html
        assert caps.attachments


class TestMockChannel:
    @pytest.fixture
    def channel(self):
        return MockChannel()

    def test_send_returns_result(self, channel):
        n = Notification(
            id="1", channel="mock", recipient="a@b.com", subject="Hi", body="Hello"
        )
        result = channel.send(n)
        assert result.status == NotificationStatus.SENT

    def test_captures_sent(self, channel):
        n = Notification(
            id="1", channel="mock", recipient="a@b.com", subject="Hi", body="Hello"
        )
        channel.send(n)
        assert len(channel.sent) == 1

    def test_health(self, channel):
        assert channel.health()

    def test_reset(self, channel):
        n = Notification(
            id="1", channel="mock", recipient="a@b.com", subject="Hi", body="Hello"
        )
        channel.send(n)
        channel.reset()
        assert len(channel.sent) == 0

    def test_capabilities(self, channel):
        caps = channel.capabilities
        assert caps.html
        assert caps.attachments


class TestEmailChannel:
    @pytest.fixture
    def channel(self):
        return EmailChannel()

    def test_send_returns_result(self, channel):
        n = Notification(
            id="1",
            channel="email",
            recipient="a@b.com",
            subject="Test",
            body="Body",
        )
        result = channel.send(n)
        assert result.status in (NotificationStatus.SENT, NotificationStatus.FAILED)

    def test_capabilities(self, channel):
        caps = channel.capabilities
        assert caps.html
        assert caps.attachments

    def test_health(self, channel):
        assert isinstance(channel.health(), bool)


class TestWebhookChannel:
    @pytest.fixture
    def channel(self):
        config = NotificationConfig(webhook_url="")
        return WebhookChannel(config=config)

    def test_send_fails_without_url(self, channel):
        n = Notification(
            id="1",
            channel="webhook",
            recipient="a@b.com",
            subject="Test",
            body="Body",
        )
        result = channel.send(n)
        assert result.status == NotificationStatus.FAILED
        assert "not configured" in result.error

    def test_health_no_url(self, channel):
        assert not channel.health()

    def test_health_with_url(self):
        config = NotificationConfig(webhook_url="https://hooks.example.com")
        channel = WebhookChannel(config=config)
        assert channel.health()

    def test_capabilities(self, channel):
        caps = channel.capabilities
        assert not caps.html
        assert not caps.attachments


class TestChannelRegistry:
    def test_register_and_create(self):
        ChannelRegistry.register("test_channel", MockChannel)
        channel = ChannelRegistry.create("test_channel")
        assert isinstance(channel, MockChannel)

    def test_unknown_channel_raises(self):
        with pytest.raises(ValueError, match="Unknown notification channel"):
            ChannelRegistry.create("does_not_exist")

    def test_available_includes_registered(self):
        available = ChannelRegistry.available()
        assert "mock" in available
        assert "email" in available
        assert "webhook" in available

    def test_get_returns_none_for_unknown(self):
        assert ChannelRegistry.get("nonexistent") is None


class TestGetChannel:
    def test_get_mock_channel(self):
        channel = get_channel("mock")
        assert isinstance(channel, MockChannel)

    def test_get_email_channel(self):
        channel = get_channel("email")
        assert isinstance(channel, EmailChannel)

    def test_get_webhook_channel(self):
        config = NotificationConfig(webhook_url="https://hooks.example.com")
        channel = get_channel("webhook", config=config)
        assert isinstance(channel, WebhookChannel)


class TestNotificationService:
    def test_send_with_mock(self):
        svc = NotificationService()
        result = svc.send(
            recipient="a@b.com",
            subject="Test",
            body="Hello",
        )
        assert result.status == NotificationStatus.SENT
        assert result.notification_id != ""

    def test_send_with_channel_override(self):
        svc = NotificationService()
        result = svc.send(
            recipient="a@b.com",
            subject="Test",
            body="Hello",
            channel="mock",
        )
        assert result.status == NotificationStatus.SENT
        assert result.channel == "mock"

    def test_send_with_high_priority(self):
        svc = NotificationService()
        result = svc.send(
            recipient="a@b.com",
            subject="Test",
            body="Hello",
            priority=NotificationPriority.HIGH,
        )
        assert result.status == NotificationStatus.SENT

    def test_send_with_metadata(self):
        svc = NotificationService()
        result = svc.send(
            recipient="a@b.com",
            subject="Test",
            body="Hello",
            metadata={"source": "test"},
        )
        assert result.status == NotificationStatus.SENT

    def test_send_disabled(self):
        config = NotificationConfig(enabled=False)
        svc = NotificationService(config=config)
        result = svc.send(
            recipient="a@b.com",
            subject="Test",
            body="Hello",
        )
        assert result.status == NotificationStatus.FAILED
        assert "disabled" in result.error

    def test_send_with_html_body(self):
        svc = NotificationService()
        result = svc.send(
            recipient="a@b.com",
            subject="Test",
            body="Plain text",
            body_html="<p>HTML</p>",
        )
        assert result.status == NotificationStatus.SENT

    def test_health_returns_channels(self):
        svc = NotificationService()
        h = svc.health()
        assert isinstance(h, NotificationHealth)
        assert "mock" in h.channels
        assert "email" in h.channels
        assert "webhook" in h.channels

    def test_health_reflects_disabled(self):
        config = NotificationConfig(enabled=False)
        svc = NotificationService(config=config)
        h = svc.health()
        assert not h.enabled

    def test_metrics_recorded(self):
        svc = NotificationService()
        svc.send(recipient="a@b.com", subject="Test", body="Hello")
        svc.send(recipient="b@c.com", subject="Test2", body="World")
        snap = svc.metrics.snapshot()
        assert snap["sent"] == 2

    def test_metrics_recorded_on_failure(self):
        config = NotificationConfig(enabled=False)
        svc = NotificationService(config=config)
        svc.send(recipient="a@b.com", subject="Test", body="Hello")
        snap = svc.metrics.snapshot()
        assert snap["failed"] == 1


class TestNotificationValidation:
    def test_send_with_default_channel(self):
        config = NotificationConfig(default_channel="mock")
        svc = NotificationService(config=config)
        result = svc.send(recipient="a@b.com", subject="Hi", body="Hello")
        assert result.channel == "mock"


class TestNotificationArchitectureBoundaries:
    def test_no_application_imports(self):
        import services.notifications

        n_dir = os.path.dirname(services.notifications.__file__)
        for root, _dirs, files in os.walk(n_dir):
            for f in files:
                if f.endswith(".py") and f != "__init__.py":
                    filepath = os.path.join(root, f)
                    with open(filepath) as fh:
                        content = fh.read()
                    assert (
                        "palmshed_ai" not in content
                    ), f"Application import found in {filepath}"

    def test_config_is_single_env_source(self):
        config = NotificationConfig.from_env()
        assert hasattr(config, "from_env")
        assert hasattr(config, "is_valid")

    def test_mock_channel_extends_base(self):
        from services.notifications.channels import NotificationChannel as NC

        assert issubclass(MockChannel, NC)

    def test_email_channel_extends_base(self):
        from services.notifications.channels import NotificationChannel as NC

        assert issubclass(EmailChannel, NC)

    def test_webhook_channel_extends_base(self):
        from services.notifications.channels import NotificationChannel as NC

        assert issubclass(WebhookChannel, NC)

    def test_channel_capabilities_defined(self):
        caps = ChannelCapabilities()
        assert hasattr(caps, "html")
        assert hasattr(caps, "attachments")
        assert hasattr(caps, "batch")
        assert hasattr(caps, "scheduling")
