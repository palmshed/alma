# Summary

Vortai is an AI platform that integrates web search, URL analysis, text generation, text-to-speech, image creation, and multimodal reasoning using Google Gemini models. It provides a React interface, a static web interface, and a REST API.

## Stack

Runs on thread. Calls mlapi for inference. Exposed via hautofix.

# Details

Vortai offers multiple components:

* Web search and URL context extraction
* High-quality text generation with optional reasoning traces
* AI-generated images and TTS output
* Redis-based caching and optional Rust/Cython acceleration
* React and static HTML interfaces
* REST API endpoints for all major AI operations

The project includes secure file handling, rate limiting (100 req/hour/IP), origin control, path traversal protection, and temporary file cleanup.
All services can be run together or independently using `run-dev.sh`.

**Development workflow**

* Python backend (Flask)
* React (TypeScript) frontend on port 8000
* Static HTML interface on port 5001
* Optional Go processor on port 8080
* Rust/Cython modules for performance

**Key directories**

```
vortai/            – Python core SDK + API
frontend/          – React interface
deploy/            – Vercel and static deployments
scripts/           – Setup + service manager
go/                – Optional Go microservice
tests/             – Full test suite
docs/              – API examples + security notes
```

# PoC (Usage Examples)

**Basic text generation**

```python
from vortai import GeminiAI
ai = GeminiAI()
response = await ai.generate_text("Explain quantum computing")
print(response)
```

**Reasoning mode**

```python
result = ai.generate_text_with_thinking("Solve: 2x + 3 = 7")
print(result["response"])
print(result["thinking_summary"])
```

**Web search context**

```python
response = ai.generate_text_with_url_context(
    "Summarize latest AI research from https://example.com"
)
```

**Text-to-Speech**

```python
file = ai.text_to_speech("Hello world")
```

**Image generation**

```python
file = ai.generate_image("A serene mountain landscape at sunset")
```

**REST endpoints**

| Method | Path                             | Purpose                       |
| ------ | -------------------------------- | ----------------------------- |
| POST   | `/api/generate`                  | Text generation               |
| POST   | `/api/generate-with-thinking`    | Reasoning mode                |
| POST   | `/api/generate-with-url-context` | Web-search contextual         |
| POST   | `/api/text-to-speech`            | TTS                           |
| POST   | `/api/generate-image`            | Image generation              |
| POST   | `/api/process-text-go`           | Go-powered text normalization |

# Impact

Vortai provides full-stack AI capabilities suitable for production use, local development, and rapid prototyping. Users can:

* Generate text with or without reasoning
* Pull real-time web data into AI responses
* Produce images and TTS audio
* Use both React and static web interfaces
* Deploy to Vercel or run locally
* Integrate via Python SDK or REST API

With strong security defaults (rate limiting, sanitization, file safety), Vortai is suitable for environments where user inputs, web requests, and file generation are sensitive.
