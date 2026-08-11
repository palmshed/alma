# SPDX-FileCopyrightText: Copyright (c) 2026 Palmshed
# SPDX-License-Identifier: MIT

import json
from typing import Any, Dict, List, Optional
from unittest.mock import PropertyMock, patch

import pytest

from palmshed_ai.providers.base import AIProviderError
from palmshed_ai.providers.gemini import GeminiAI
from palmshed_ai.providers.openrouter import OpenRouterProvider
from palmshed_ai.router import AIRouter

REAL_GEMINI_KEY = "real-test-key-gemini"
REAL_OR_KEY = "real-test-key-openrouter"

SYNTHETIC_ANSWER_PREFIX = "Synthesized answer for"
SYNTHETIC_CHAT_PREFIX = "Grounded response for conversation turn"


# ── Fake HTTP session for OpenRouter tests ────────────────────────────


class FakeResponse:
    def __init__(
        self,
        status_code: int = 200,
        payload: Optional[Dict[str, Any]] = None,
        lines: Optional[List[str]] = None,
        text: str = "",
    ):
        self.status_code = status_code
        self._payload = payload
        self._lines = lines
        self.text = text

    def json(self) -> Dict[str, Any]:
        if self._payload is not None:
            return self._payload
        return json.loads(self.text)

    def iter_lines(self, decode_unicode: bool = False):
        for line in self._lines or []:
            yield line


class FakeSession:
    def __init__(self, response: FakeResponse):
        self.response = response
        self.calls: List[Dict[str, Any]] = []

    def post(self, url, headers=None, json=None, timeout=None, stream=False):
        self.calls.append(
            {"url": url, "json": json, "headers": headers, "stream": stream}
        )
        return self.response


def completion_payload(content: str, reasoning: Optional[str] = None) -> Dict[str, Any]:
    message: Dict[str, Any] = {"role": "assistant", "content": content}
    if reasoning:
        message["reasoning"] = reasoning
    return {"choices": [{"message": message, "finish_reason": "stop"}]}


def stream_payload(delta: str) -> Dict[str, Any]:
    return {"choices": [{"delta": {"content": delta}}]}


@pytest.fixture(autouse=True)
def clear_provider_env(monkeypatch):
    """Keep tests deterministic regardless of developer environment keys."""
    for key in (
        "AI_PROVIDER",
        "GEMINI_API_KEY",
        "OPENROUTER_API_KEY",
        "OPENROUTER_BASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)
    yield


# ── Gemini provider ───────────────────────────────────────────────────


def test_gemini_synthetic_with_mock_key():
    provider = GeminiAI(api_key="dummy")
    assert not provider.has_credentials
    assert provider.synthetic
    text = provider.generate_text("hello")
    assert text.startswith(SYNTHETIC_ANSWER_PREFIX)


def test_gemini_model_for(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "model-a")
    monkeypatch.setenv("GEMINI_THINKING_MODEL", "model-b")
    monkeypatch.setenv("GEMINI_URL_CONTEXT_MODEL", "model-c")
    provider = GeminiAI(api_key="dummy")
    assert provider.model_for("chat") == "model-a"
    assert provider.model_for("thinking") == "model-b"
    assert provider.model_for("web") == "model-c"
    assert provider.model_for("code") == "model-a"


# ── OpenRouter provider ───────────────────────────────────────────────


def test_openrouter_synthetic_with_mock_key():
    provider = OpenRouterProvider(api_key="mock_key")
    assert not provider.has_credentials
    assert provider.synthetic
    assert provider.generate_text("hello").startswith(SYNTHETIC_ANSWER_PREFIX)
    assert provider.generate_chat([{"role": "user", "content": "hi"}]).startswith(
        SYNTHETIC_CHAT_PREFIX
    )


def test_openrouter_synthetic_thinking_shape():
    provider = OpenRouterProvider(api_key="dummy")
    result = provider.generate_text_with_thinking("hi")
    assert set(result.keys()) == {"response", "thinking_summary"}
    assert result["thinking_summary"]


def test_openrouter_model_for(monkeypatch):
    monkeypatch.setenv("OPENROUTER_MODEL", "or/a")
    monkeypatch.setenv("OPENROUTER_THINKING_MODEL", "or/b")
    monkeypatch.setenv("OPENROUTER_URL_CONTEXT_MODEL", "or/c")
    provider = OpenRouterProvider(api_key=REAL_OR_KEY)
    assert provider.model_for("chat") == "or/a"
    assert provider.model_for("thinking") == "or/b"
    assert provider.model_for("web") == "or/c"
    assert provider.model_for("code") == "or/a"


def test_openrouter_generate_text_parses_response():
    session = FakeSession(
        FakeResponse(payload=completion_payload("Hello from OpenRouter"))
    )
    provider = OpenRouterProvider(api_key=REAL_OR_KEY, base_url="https://or.test/v1")
    provider.session = session
    assert provider.generate_text("hello") == "Hello from OpenRouter"
    sent = session.calls[0]["json"]
    assert sent["model"] == "openrouter/auto"
    assert sent["messages"] == [{"role": "user", "content": "hello"}]
    assert sent["stream"] is False


def test_openrouter_generate_chat_maps_model_role():
    session = FakeSession(
        FakeResponse(payload=completion_payload("conversation answer"))
    )
    provider = OpenRouterProvider(api_key=REAL_OR_KEY, base_url="https://or.test/v1")
    provider.session = session
    messages = [
        {"role": "user", "content": "What is my name?"},
        {"role": "model", "content": "Alice"},
    ]
    assert provider.generate_chat(messages) == "conversation answer"
    sent = session.calls[0]["json"]["messages"]
    assert sent[1]["role"] == "assistant"


def test_openrouter_thinking_extracts_reasoning():
    session = FakeSession(
        FakeResponse(
            payload=completion_payload(
                "final answer",
                reasoning="First reason about the problem.",
            )
        )
    )
    provider = OpenRouterProvider(api_key=REAL_OR_KEY, base_url="https://or.test/v1")
    provider.session = session
    result = provider.generate_text_with_thinking("think")
    assert result["response"] == "final answer"
    assert result["thinking_summary"] == ["First reason about the problem."]


def test_openrouter_quota_error_classified():
    session = FakeSession(FakeResponse(status_code=429, text="rate limited"))
    provider = OpenRouterProvider(api_key=REAL_OR_KEY, base_url="https://or.test/v1")
    provider.session = session
    with pytest.raises(AIProviderError) as excinfo:
        provider.generate_text("hello")
    assert excinfo.value.category == "quota"
    assert excinfo.value.http_error_status() == 429
    assert excinfo.value.provider == "OpenRouter"


def test_openrouter_streams_deltas():
    payloads = [
        stream_payload("Hel"),
        stream_payload("lo"),
        stream_payload(" world"),
    ]
    lines: List[str] = []
    for p in payloads:
        lines.append(f"data: {json.dumps(p)}")
    lines.append("data: [DONE]")
    session = FakeSession(FakeResponse(lines=lines))
    provider = OpenRouterProvider(api_key=REAL_OR_KEY, base_url="https://or.test/v1")
    provider.session = session
    assert (
        "".join(provider.stream_chat([{"role": "user", "content": "hi"}]))
        == "Hello world"
    )
    assert session.calls[0]["json"]["stream"] is True


def test_openrouter_missing_key_is_synthetic():
    provider = OpenRouterProvider(api_key=None, base_url="https://or.test/v1")
    assert not provider.has_credentials
    assert provider.generate_text("hello").startswith(SYNTHETIC_ANSWER_PREFIX)


# ── Router: provider selection ────────────────────────────────────────


def test_router_auto_prefers_gemini(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", REAL_GEMINI_KEY)
    monkeypatch.setenv("OPENROUTER_API_KEY", REAL_OR_KEY)
    router = AIRouter()
    assert [p.name for p in router._candidates()] == ["gemini", "openrouter"]


def test_router_openrouter_preferred(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openrouter")
    monkeypatch.setenv("GEMINI_API_KEY", REAL_GEMINI_KEY)
    monkeypatch.setenv("OPENROUTER_API_KEY", REAL_OR_KEY)
    router = AIRouter()
    assert [p.name for p in router._candidates()] == ["openrouter", "gemini"]


def test_router_single_configured_provider(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", REAL_OR_KEY)
    router = AIRouter()
    assert [p.name for p in router._candidates()] == ["openrouter"]


def test_router_no_keys_uses_synthetic(monkeypatch):
    router = AIRouter()
    assert [p.name for p in router._candidates()] == ["synthetic"]
    status = router.status()
    assert status["provider"] == "synthetic/mock"
    assert status["available"] == []


def test_router_auto_with_dummy_key_uses_synthetic(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy")
    router = AIRouter()
    assert [p.name for p in router._candidates()] == ["synthetic"]


def test_router_synthetic_generation_reports_info(monkeypatch):
    router = AIRouter()
    info: Dict[str, Any] = {}
    response = router.generate_chat([{"role": "user", "content": "hello"}], info=info)
    assert response.startswith(SYNTHETIC_CHAT_PREFIX)
    assert info["provider"] == "synthetic/mock"
    assert info["provider_key"] == "synthetic"
    assert info["model"] == "synthetic"
    assert info["fallback_used"] is False


# ── Router: fallback between providers ────────────────────────────────


def _router_with_real_credentials(monkeypatch) -> AIRouter:
    monkeypatch.setenv("GEMINI_API_KEY", REAL_GEMINI_KEY)
    monkeypatch.setenv("OPENROUTER_API_KEY", REAL_OR_KEY)
    return AIRouter()


def test_router_falls_back_on_quota(monkeypatch):
    router = _router_with_real_credentials(monkeypatch)
    with patch.object(
        GeminiAI, "has_credentials", new_callable=PropertyMock, return_value=True
    ):
        with patch.object(
            OpenRouterProvider,
            "has_credentials",
            new_callable=PropertyMock,
            return_value=True,
        ):
            with patch.object(
                router.providers["gemini"],
                "generate_chat",
                side_effect=AIProviderError(
                    "quota exceeded",
                    category="quota",
                    http_status=429,
                    provider="Gemini",
                    model="m",
                ),
            ):
                with patch.object(
                    router.providers["openrouter"],
                    "generate_chat",
                    return_value="OpenRouter answer",
                ):
                    info: Dict[str, Any] = {}
                    response = router.generate_chat(
                        [{"role": "user", "content": "hi"}], info=info
                    )
    assert response == "OpenRouter answer"
    assert info["provider"] == "OpenRouter"
    assert info["fallback_used"] is True


def test_router_per_request_provider_override(monkeypatch):
    router = _router_with_real_credentials(monkeypatch)
    with patch.object(
        GeminiAI, "has_credentials", new_callable=PropertyMock, return_value=True
    ):
        with patch.object(
            OpenRouterProvider,
            "has_credentials",
            new_callable=PropertyMock,
            return_value=True,
        ):
            with patch.object(
                router.providers["openrouter"],
                "generate_chat",
                return_value="OpenRouter answer",
            ) as or_mock:
                with patch.object(
                    router.providers["gemini"],
                    "generate_chat",
                    return_value="Gemini answer",
                ) as gem_mock:
                    response = router.generate_chat(
                        [{"role": "user", "content": "hi"}], provider="openrouter"
                    )
    assert response == "OpenRouter answer"
    assert or_mock.called
    assert not gem_mock.called


def test_router_invalid_provider_override_falls_back_to_auto(monkeypatch):
    router = _router_with_real_credentials(monkeypatch)
    with patch.object(
        GeminiAI, "has_credentials", new_callable=PropertyMock, return_value=True
    ):
        with patch.object(
            OpenRouterProvider,
            "has_credentials",
            new_callable=PropertyMock,
            return_value=True,
        ):
            with patch.object(
                router.providers["gemini"],
                "generate_chat",
                return_value="Gemini answer",
            ):
                response = router.generate_chat(
                    [{"role": "user", "content": "hi"}], provider="nonsense"
                )
    assert response == "Gemini answer"


def test_router_raises_when_all_providers_fail(monkeypatch):
    router = _router_with_real_credentials(monkeypatch)
    with patch.object(
        GeminiAI, "has_credentials", new_callable=PropertyMock, return_value=True
    ):
        with patch.object(
            OpenRouterProvider,
            "has_credentials",
            new_callable=PropertyMock,
            return_value=True,
        ):
            with patch.object(
                router.providers["gemini"],
                "generate_chat",
                side_effect=AIProviderError(
                    "boom", category="server", provider="Gemini"
                ),
            ):
                with patch.object(
                    router.providers["openrouter"],
                    "generate_chat",
                    side_effect=AIProviderError(
                        "also boom", category="server", provider="OpenRouter"
                    ),
                ):
                    with pytest.raises(AIProviderError) as excinfo:
                        router.generate_chat([{"role": "user", "content": "hi"}])
    assert excinfo.value.provider == "OpenRouter"


def test_router_does_not_fallback_to_synthetic_on_real_failure(monkeypatch):
    router = _router_with_real_credentials(monkeypatch)
    with patch.object(
        GeminiAI, "has_credentials", new_callable=PropertyMock, return_value=True
    ):
        with patch.object(
            router.providers["gemini"],
            "generate_chat",
            side_effect=AIProviderError(
                "boom", category="unavailable", provider="Gemini"
            ),
        ):
            with patch.object(
                OpenRouterProvider,
                "has_credentials",
                new_callable=PropertyMock,
                return_value=False,
            ):
                with pytest.raises(AIProviderError) as excinfo:
                    router.generate_chat([{"role": "user", "content": "hi"}])
    assert excinfo.value.category == "unavailable"


# ── Router: streaming ─────────────────────────────────────────────────


def test_router_stream_synthetic(monkeypatch):
    router = AIRouter()
    chunks = list(router.stream_chat([{"role": "user", "content": "hello"}]))
    assert "".join(chunks).startswith(SYNTHETIC_CHAT_PREFIX)


def test_router_stream_falls_back(monkeypatch):
    router = _router_with_real_credentials(monkeypatch)

    class ExplodingStream:
        def __iter__(self):
            raise AIProviderError("stream failed", category="server")

    with patch.object(
        GeminiAI, "has_credentials", new_callable=PropertyMock, return_value=True
    ):
        with patch.object(
            OpenRouterProvider,
            "has_credentials",
            new_callable=PropertyMock,
            return_value=True,
        ):
            with patch.object(
                router.providers["gemini"],
                "stream_chat",
                return_value=ExplodingStream(),
            ):
                with patch.object(
                    router.providers["openrouter"],
                    "stream_chat",
                    return_value=iter(["a", "b", "c"]),
                ):
                    info: Dict[str, Any] = {}
                    chunks = list(
                        router.stream_chat(
                            [{"role": "user", "content": "hi"}], info=info
                        )
                    )
    assert chunks == ["a", "b", "c"]
    assert info["provider"] == "OpenRouter"
    assert info["fallback_used"] is True


def test_router_thinking_shape_synthetic(monkeypatch):
    router = AIRouter()
    result = router.generate_chat_with_thinking([{"role": "user", "content": "hi"}])
    assert set(result.keys()) == {"response", "thinking_summary"}


# ── Language flows to the provider regardless of provider ─────────────


def _test_client():
    from palmshed_ai import create_app

    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


@patch("palmshed_ai.routes.api.ai.generate_chat")
def test_language_instruction_prepended(mock_chat):
    mock_chat.return_value = "answer"
    test_client = _test_client()

    test_client.post(
        "/api/generate",
        json={
            "messages": [{"role": "user", "content": "hello"}],
            "language": "hi",
        },
    )
    messages = mock_chat.call_args.args[0]
    assert messages[0]["role"] == "user"
    assert "Hindi" in messages[0]["content"]
    assert messages[-1]["content"] == "hello"


@patch("palmshed_ai.routes.api.ai.generate_chat")
def test_language_instruction_prepended_search(mock_chat):
    mock_chat.return_value = "answer"
    test_client = _test_client()

    test_client.post(
        "/api/search",
        json={
            "messages": [{"role": "user", "content": "hello"}],
            "mode": "auto",
            "language": "ta",
        },
    )
    messages = mock_chat.call_args.args[0]
    assert "Tamil" in messages[0]["content"]
