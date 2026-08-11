# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT

from palmshed_ai.search import (
    SearchResult,
    SearchService,
    SearchCache,
    FallbackSearchProvider,
)


def test_search_result_domain_extraction():
    sr = SearchResult(
        title="OpenAI",
        url="https://www.openai.com/research/gpt-4",
        snippet="GPT-4 research notes",
    )
    assert sr.domain == "openai.com"
    d = sr.to_dict()
    assert d["domain"] == "openai.com"
    assert d["title"] == "OpenAI"

    restored = SearchResult.from_dict(d)
    assert restored.url == "https://www.openai.com/research/gpt-4"
    assert restored.domain == "openai.com"


def test_search_cache_ttl():
    cache = SearchCache(ttl_seconds=1)
    results = [SearchResult(title="Test", url="https://example.com", snippet="snippet")]
    cache.set("key1", results)

    cached = cache.get("key1")
    assert cached is not None
    assert cached[0].title == "Test"


def test_intent_router():
    service = SearchService()
    assert (
        service.route_intent("Write a Python function to sort array", mode="auto")
        == "code"
    )
    assert service.route_intent("What is the weather today?", mode="auto") == "search"
    assert service.route_intent("tell me a story", mode="chat") == "chat"
    assert service.route_intent("anything", mode="search") == "search"


def test_intent_router_chat_triggers():
    service = SearchService()
    assert service.route_intent("Hello there", mode="auto") == "chat"
    assert service.route_intent("2 + 2", mode="auto") == "chat"
    assert service.route_intent("What is 15% of 200?", mode="auto") == "chat"
    assert service.route_intent("Rewrite this paragraph", mode="auto") == "chat"
    assert service.route_intent("Translate this to Spanish", mode="auto") == "chat"
    assert service.route_intent("Summarize this article", mode="auto") == "chat"
    assert service.route_intent("Explain this code snippet", mode="auto") == "chat"
    assert service.route_intent("Write a poem about stars", mode="auto") == "chat"


def test_intent_router_search_triggers():
    service = SearchService()
    assert (
        service.route_intent("What is the latest Rust release?", mode="auto")
        == "search"
    )
    assert service.route_intent("What happened today in tech?", mode="auto") == "search"
    assert service.route_intent("Compare PostgreSQL and MySQL", mode="auto") == "search"
    assert (
        service.route_intent("What is the capital of France?", mode="auto") == "search"
    )
    assert service.route_intent("What is Rust 1.90?", mode="auto") == "search"
    assert service.route_intent("Latest Node.js release", mode="auto") == "search"
    assert service.route_intent("Who won the 2026 election?", mode="auto") == "search"


def test_followup_reuse_skips_time_sensitive_queries():
    service = SearchService()
    messages = [
        {"role": "user", "content": "Search for Python release dates"},
        {
            "role": "assistant",
            "content": "Python 3.12 was released in 2023.",
            "sources": [
                {
                    "title": "Python Docs",
                    "url": "https://python.org",
                    "snippet": "Python release schedules",
                    "domain": "python.org",
                }
            ],
        },
    ]

    # Short, non-time-sensitive follow-up reuses sources.
    res = service.execute_search_pipeline(
        query="What changed from the previous version?",
        messages=messages,
        mode="auto",
    )
    assert res.get("reused") is True
    assert res["sources"][0]["domain"] == "python.org"

    # Time-sensitive follow-up forces a fresh search.
    res = service.execute_search_pipeline(
        query="What is the latest Rust release?",
        messages=messages,
        mode="auto",
    )
    assert res.get("reused") is False
    assert res["search_steps"][0] == "Searching the web..."


def test_query_rewriter():
    service = SearchService()
    assert (
        service.rewrite_query("Please search for Alma AI architecture")
        == "Alma AI architecture"
    )
    assert service.rewrite_query("find me latest news on AI") == "latest news on AI"


def test_grounded_context_prefers_raw_content():
    service = SearchService()
    results = [
        SearchResult(
            title="OpenAI",
            url="https://www.openai.com/research/gpt-4",
            snippet="Short snippet only.",
            raw_content="A substantial passage of real page content that is long enough to pass the minimum length threshold and be preferred over the truncated search snippet.",
            published_date="2024-03-14",
        )
    ]
    ctx = service.format_grounded_context(results)
    assert "Source [1]" in ctx
    assert "Title: OpenAI" in ctx
    assert "URL: https://www.openai.com/research/gpt-4" in ctx
    assert "Domain: openai.com" in ctx
    assert "Published: 2024-03-14" in ctx
    assert "substantial passage" in ctx
    assert "Short snippet only." not in ctx


def test_grounded_context_falls_back_to_snippet():
    service = SearchService()
    results = [
        SearchResult(
            title="Example",
            url="https://example.com",
            snippet="A fallback snippet when no full page content was fetched.",
        )
    ]
    ctx = service.format_grounded_context(results)
    assert "fallback snippet" in ctx
    assert "Source [1]" in ctx


def test_grounded_context_truncates_long_content():
    service = SearchService()
    long_content = "word " * 3000
    results = [
        SearchResult(
            title="Long",
            url="https://example.com/long",
            snippet="tiny",
            raw_content=long_content,
        )
    ]
    ctx = service.format_grounded_context(results)
    assert len(ctx) < 3000
    assert ctx.rstrip().endswith("...")


def test_fallback_search_provider():
    provider = FallbackSearchProvider()
    results = provider.search("python programming", max_results=3)
    assert len(results) > 0
    assert results[0].url.startswith("http")
    assert results[0].title != ""


def test_search_pipeline_execution():
    service = SearchService()
    res = service.execute_search_pipeline(
        query="latest news on quantum computing",
        mode="search",
        max_results=3,
    )
    assert res["intent"] == "search"
    assert len(res["sources"]) > 0
    assert len(res["search_steps"]) == 3
    assert "Searching the web..." in res["search_steps"]
    assert "Reading sources..." in res["search_steps"]
    assert "Generating answer..." in res["search_steps"]
    assert "Source [1]" in res["grounded_context"]


def test_followup_sources_reuse():
    service = SearchService()
    messages = [
        {"role": "user", "content": "Search for Python release dates"},
        {
            "role": "assistant",
            "content": "Python 3.12 was released in 2023.",
            "sources": [
                {
                    "title": "Python Docs",
                    "url": "https://python.org",
                    "snippet": "Python release schedules",
                    "domain": "python.org",
                }
            ],
        },
    ]

    res = service.execute_search_pipeline(
        query="tell me more",
        messages=messages,
        mode="auto",
    )
    assert res.get("reused") is True
    assert len(res["sources"]) == 1
    assert res["sources"][0]["domain"] == "python.org"
