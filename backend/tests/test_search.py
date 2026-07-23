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
    assert service.route_intent("Write a Python function to sort array", mode="auto") == "code"
    assert service.route_intent("What is the weather today?", mode="auto") == "search"
    assert service.route_intent("tell me a story", mode="chat") == "chat"
    assert service.route_intent("anything", mode="search") == "search"


def test_query_rewriter():
    service = SearchService()
    assert service.rewrite_query("Please search for Alma AI architecture") == "Alma AI architecture"
    assert service.rewrite_query("find me latest news on AI") == "latest news on AI"


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
