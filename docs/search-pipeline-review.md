# Search Pipeline Verification Review

**Date:** 2026-07-23
**Verification Environment:** Mock (default keys, no live API calls)
**Review Scope:** `verify_search.py` harness and search pipeline implementation

---

## 1. Latency Measurements

### What the Verification Measures

The verification script (`verify_search.py:551-605`) measures pipeline execution time:

```python
t0 = time.time()
self.service.execute_search_pipeline(query, mode=mode)
latencies.append((time.time() - t0) * 1000)
```

### Reported Values

| Metric | Reported | What It Captures |
|--------|----------|------------------|
| Chat | <0.01 ms | Intent routing only |
| Search | 0.01 ms (p50) | Provider call + extraction |
| Code | 0.01 ms (p50) | Pipeline routing only |

### Why These Values Are Low

The verification sets mock API keys by default (`verify_search.py:35`):

```python
os.environ["GEMINI_API_KEY"] = os.environ.get("GEMINI_API_KEY", "mock_key_for_verification")
```

The `_is_mock_key()` method (`sdk.py:75-79`) returns synthetic responses without making API calls:

```python
return f"Synthesized answer for '{prompt[:60]}': Grounded response based on provided context..."
```

The search providers are also initialized with mock keys (`verify_search.py:179-188`):

```python
providers: Dict[str, SearchProvider] = {
    "Tavily": TavilySearchProvider(api_key="mock_key"),
    "Brave": BraveSearchProvider(api_key="mock_key"),
    ...
}
```

These providers return empty lists when no valid API key is present.

### Verification Status

| Metric | Status |
|--------|--------|
| Pipeline execution time | Verified with mocks |
| Network latency | Not measured |
| Gemini generation time | Not measured |
| End-to-end latency | Not measured |

---

## 2. Search Providers

### Provider Implementation

Six providers are implemented (`search.py:74-361`):

| Provider | API Endpoint | Key Environment Variable |
|----------|--------------|--------------------------|
| Tavily | `api.tavily.com` | `TAVILY_API_KEY` |
| Brave | `api.search.brave.com` | `BRAVE_API_KEY` |
| Exa | `api.exa.ai` | `EXA_API_KEY` |
| SerpAPI | `serpapi.com` | `SERPAPI_API_KEY` |
| SearXNG | Local instance | `SEARXNG_URL` |
| Fallback | DuckDuckGo HTML | None required |

### Provider Behavior Without Keys

Each provider returns an empty list when its API key is missing:

```python
# TavilySearchProvider.search() line 83-84
if not self.api_key:
    return []
```

### Fallback Provider

The fallback provider (`search.py:286-361`) queries DuckDuckGo's HTML endpoint and generates structured fallback cards when scraping fails. This is the only provider that makes real network requests without API keys.

### Verification Status

| Provider | Verified with Live API | Verified with Mocks | Inferred |
|----------|----------------------|--------------------| ---------|
| Tavily | Not verified | Initialization only | - |
| Brave | Not verified | Initialization only | - |
| Exa | Not verified | Initialization only | - |
| SerpAPI | Not verified | Initialization only | - |
| SearXNG | Not verified | Initialization only | - |
| Fallback | Not verified | Execution tested | - |

---

## 3. Streaming

### Backend Implementation

The `/api/search/stream` endpoint (`api.py:107-123`):

```python
def generate_sse():
    try:
        for s in steps:
            yield f"data: {json.dumps({'type': 'step', 'step': s})}\n\n"
        if sources:
            yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
        words = full_response.split(" ")
        for i, w in enumerate(words):
            chunk = w + (" " if i < len(words) - 1 else "")
            yield f"data: {json.dumps({'type': 'chunk', 'delta': chunk})}\n\n"
```

The response is generated completely first, then split into words and yielded sequentially.

### Frontend Implementation

The frontend (`api.ts:85`) uses standard fetch:

```typescript
return request<import('../types').ApiSearchResult>('/api/search', {
```

This calls `res.json()` after the full response is received (`api.ts:35`).

### Verification Test

The streaming verification (`verify_api.py:420-432`) checks for SSE format:

```python
if resp_stream.status_code == 200 and "data: " in stream_body and '"type": "chunk"' in stream_body:
```

This confirms the response body contains SSE-formatted events but does not measure progressive delivery.

### Verification Status

| Aspect | Status |
|--------|--------|
| Backend SSE format | Verified with mocks |
| Progressive token delivery | Not verified |
| Frontend SSE consumption | Not verified (frontend uses fetch) |
| Time to first token | Not measured |

---

## 4. Browser Verification

### Current Implementation

`verify_frontend()` (`verify_search.py:487-524`) performs structural checks:

```python
has_progress_states = os.path.exists(search_progress_path) and (
    "Searching the web" in open(search_progress_path, "r", encoding="utf-8").read()
)
```

### Checks Performed

| Check | Method | What It Verifies |
|-------|--------|------------------|
| Search mode selector | File existence | Component file exists |
| Search progress states | String match | "Searching the web" in source |
| Source cards | String match | "source-card" in source |
| Target blank | String match | `target="_blank"` in source |
| Modal | File existence | Component file exists |

### Checks Not Performed

| Check | Status |
|-------|--------|
| DOM rendering | Not verified |
| Progressive text appearance | Not verified |
| Link navigation | Not verified |
| AbortController cancellation | Not verified |
| Layout shifts | Not verified |

### Verification Status

| Aspect | Status |
|--------|--------|
| Component file existence | Verified |
| Component string patterns | Verified |
| Runtime behavior | Not verified |
| User interaction | Not verified |

---

## 5. Cache

### SearchCache Implementation

In-memory TTL cache (`search.py:364-380`):

```python
class SearchCache:
    def __init__(self, ttl_seconds: int = 600):
        self.ttl = ttl_seconds
        self._cache: Dict[str, Tuple[float, List[SearchResult]]] = {}
```

### General Cache

Supports Redis or in-memory (`extensions/cache.py:15-62`):

```python
class Cache:
    def __init__(self, redis_url: Optional[str] = None):
        self.redis = redis.from_url(redis_url) if redis_url else None
        self.memory_cache = {}
```

Defaults to in-memory when `redis_url` is not provided.

### Verification Test

Cache verification (`verify_search.py:335-387`) uses unique queries:

```python
query = "Unique cache test query " + str(time.time())
```

First request is a cache miss, second request is a cache hit. TTL expiration is tested with a 1-second cache.

### Verification Status

| Aspect | Status |
|--------|--------|
| Cache miss | Verified |
| Cache hit | Verified |
| TTL expiration | Verified |
| Redis persistence | Not verified |
| Cache eviction under load | Not verified |

---

## 6. Failure Injection

### What's Tested

| Failure Type | Method | Verified |
|--------------|--------|----------|
| Provider timeout | Mock exception | Yes (mocked) |
| 429 rate limit | Mock exception | Yes (mocked) |
| All providers fail | Mock all providers | Yes (mocked) |
| Invalid JSON request | Malformed body | Yes |
| Empty queries | Whitespace only | Yes |

### What's Not Tested

| Failure Type | Status |
|--------------|--------|
| DNS failure | Not implemented |
| SSL certificate error | Not implemented |
| Gemini unavailable | Not implemented |
| Malformed provider response | Not implemented |
| Network timeout (real) | Not implemented |

---

## 7. Resource Usage

### Current Testing

No resource usage monitoring exists in the verification suite.

### What's Tested

| Scenario | Status |
|----------|--------|
| 10 concurrent requests | Verified (chat mode only) |
| 50 concurrent requests | Not tested |
| 100 concurrent requests | Not tested |

### What's Not Measured

| Metric | Status |
|--------|--------|
| Peak memory | Not measured |
| CPU usage | Not measured |
| File descriptor count | Not measured |
| Thread count | Not measured |

---

## 8. Long-Running Sessions

### Current Testing

No long-running session tests exist.

### What's Not Tested

| Check | Status |
|-------|--------|
| Memory growth over time | Not tested |
| Connection leaks | Not tested |
| Cache behavior over time | Not tested |
| Provider health over time | Not tested |

---

## Summary

| Area | Verified with Live Services | Verified with Mocks | Inferred | Not Implemented |
|------|---------------------------|--------------------|----------|--------------------|
| Latency (pipeline) | - | Yes | - | - |
| Latency (end-to-end) | - | - | - | Yes |
| Search providers (execution) | - | Fallback only | Others inferred | - |
| Streaming (SSE format) | - | Yes | - | - |
| Streaming (progressive) | - | - | - | Yes |
| Frontend streaming | - | - | - | Yes |
| Browser behavior | - | - | - | Yes |
| Cache (hit/miss/TTL) | - | Yes | - | - |
| Cache (Redis) | - | - | - | Yes |
| Failure injection (mocked) | - | Yes | - | - |
| Failure injection (real) | - | - | - | Yes |
| Resource usage | - | - | - | Yes |
| Long-running sessions | - | - | - | Yes |

---

## Recommendations

These are ordered by priority. Implementation should wait for a second verification run with live services.

1. **Establish a trustworthy baseline** by running verification with real API keys
2. **Measure end-to-end latency** from the browser, including network calls
3. **Verify streaming delivery** by measuring time to first token and progressive chunk arrival
4. **Test frontend SSE consumption** to determine if EventSource or fetch is used
5. **Add browser-based behavioral tests** for search progress, source rendering, and cancellation
6. **Test failure modes with real network conditions** (DNS, SSL, provider unavailability)
7. **Monitor resource usage** under concurrent load
8. **Run long-running session tests** to detect memory leaks and connection issues
