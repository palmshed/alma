# Alma

Alma is an AI assistant for chat, web search, step-by-step reasoning, code, images, voice, and multilingual conversation, all persisted and restorable within a single interface.

> Alma decides how to answer a request rather than asking the user to choose a model. A provider preference (Auto, Gemini, or OpenRouter) is available in the settings menu; the system still handles model selection and fallback internally.

The frontend expresses the user's intent. Alma maps that intent to a capability. The capability is served through a provider abstraction, and the provider selects the appropriate model. Model selection is intentionally an implementation detail; the user describes the task and the system handles the routing.

```
User
    ↓
  Alma
    ↓
Capability
    ↓
Provider Abstraction
    ├── Gemini
    └── OpenRouter → openrouter/auto
```

The product interface exposes a provider preference (Auto, Gemini, or OpenRouter) in the header settings menu. This is a preference, not a model choice: the router still selects the concrete model per capability and falls back across providers as needed.

## What Alma Provides

- **Chat**, Direct conversation with context maintained across turns.
- **Search**, Real-time grounded answers with verified sources and citations via an intent-routed search pipeline.
- **Thinking**, Detailed step-by-step reasoning for complex problems, showing deep reasoning separate from the final answer.
- **Code**, Write, debug, and optimize scripts; code-related requests are routed through a dedicated search-and-generate execution path.
- **Images**, Processing and generation of visual assets.
- **Voice**, Read responses aloud for accessible screen-free interaction.
- **Languages**, Multilingual support in the user's primary language or via automatic detection.
- **Conversations**, Auto-saved history with options to rename, delete, restore, and toggle between past sessions.

## System Architecture

Alma uses a layered architecture to keep presentation, business logic, and AI integrations strictly separated.

- **Frontend**, A React application paired with a lightweight static mirror. It captures user intent (mode, prompt, conversation history, language preference) and sends it to the backend API. It never holds provider credentials, names specific AI models, or handles routing logic.
- **Backend API**, Flask routes that accept incoming requests, run the real-time search pipeline when needed, and call the AI router. It handles validation and error mapping without containing provider-specific code.
- **Capability Layer**, The router maps requests to specialized capabilities (`chat`, `thinking`, `web`). Capabilities act as the contract between the API and providers, ensuring no upper layer depends on a specific model.
- **Provider Abstraction**, The `AIProvider` interface normalizes all backend integrations. The router talks exclusively to this interface. Each provider resolves its own underlying model per capability.
- **Gemini Provider**, Direct integration with the Google Gemini API. Manages generation along with specialized tasks like text-to-speech, visual processing, and deep research.
- **OpenRouter Provider**, An OpenAI-compatible client providing access to OpenRouter models as a peer to the Gemini provider behind the same standard interface.
- **Search Providers**, Multi-engine search via Tavily, Brave, Exa, SerpAPI, and SearXNG under a `SearchProvider` interface, featuring dynamic fallback ordering and DuckDuckGo support when no API keys are present.
- **Conversation Persistence**, A `ConversationStore` powered by a underlying Storage service, offering schema versioning and user isolation via anonymous client session cookies.
- **Verification Suite**, Backend unit tests, browser E2E verifiers, and the `alma verify` command to check system endpoints (see [Verification](#verification)).

### Architectural Boundaries

| Layer | Strict Rules |
| :--- | :--- |
| **Frontend** | Must never access provider credentials or dictate model choices. |
| **Capabilities** | Must remain completely decoupled from specific AI models. |
| **Backend** | Encapsulates provider selection and credential management. |
| **API Contract** | Excludes internal model names from client-facing responses. |

## Provider Model

Alma resolves requests through an abstract multi-provider chain:

$$\text{Capability} \longrightarrow \text{Provider} \longrightarrow \text{Model}$$

Provider selection is configured server-side via `AI_PROVIDER` (`auto`, `gemini`, or `openrouter`). In `auto` mode, the router evaluates healthy providers by preference and falls back automatically if an error occurs. If no credentials are available, a synthetic provider handles requests so verification and tests continue running seamlessly.

OpenRouter's `openrouter/auto` mechanism acts as an internal routing strategy, not a user-facing toggle.

## Configuration

Environment variables in `.env` manage local runtime configuration. Secrets must remain server-side and should never be committed to source control.

### 1. Required Credentials (Set At Least One)

| Variable | Description |
| :--- | :--- |
| `GEMINI_API_KEY` | API credentials for the Google Gemini provider |
| `OPENROUTER_API_KEY` | API credentials for the OpenRouter provider |

### 2. Provider Settings

| Variable | Description |
| :--- | :--- |
| `AI_PROVIDER` | Provider selection strategy: `auto` (default), `gemini`, or `openrouter` |
| `OPENROUTER_MODEL` | Default chat model for OpenRouter (default: `openrouter/auto`) |
| `OPENROUTER_THINKING_MODEL` | Deep reasoning model for OpenRouter (default: `openrouter/auto`) |
| `OPENROUTER_URL_CONTEXT_MODEL` | URL/web context parsing model for OpenRouter (default: `openrouter/auto`) |

### 3. Search Credentials (Optional)

*If omitted, the platform defaults to a free DuckDuckGo search fallback.*

| Variable | Description |
| :--- | :--- |
| `TAVILY_API_KEY` | Tavily search pipeline key |
| `BRAVE_API_KEY` | Brave Search API key |
| `EXA_API_KEY` | Exa neural search API key |
| `SERPAPI_API_KEY` | SerpAPI engine credentials |
| `SEARXNG_URL` | Self-hosted SearXNG instance endpoint |

### 4. Advanced & Infrastructure Overrides

| Variable | Description |
| :--- | :--- |
| `GEMINI_MODEL` | Override for standard Gemini chat model |
| `GEMINI_THINKING_MODEL` | Override for Gemini deep-reasoning model |
| `GEMINI_URL_CONTEXT_MODEL` | Override for Gemini context extraction model |
| `REDIS_URL` | Optional Redis instance URL for response caching |
| `GO_SERVICE_URL` | Optional Go text-processing microservice endpoint |

### 5. Synthetic Fallback Provider

When running without active provider keys, Alma uses a mock synthetic provider (`synthetic/mock`) that yields deterministic data for local testing and CI pipeline validation without external network calls, ensuring tests run reliably.

## Verification & Testing

Alma includes end-to-end testing tools to ensure system stability across application boundaries.

- **Code Style:** `make lint` checks code clean state with `ruff`.
- **Backend Test Suite:** `make test` executes `pytest` across API routes, providers, routing, search components, and storage services.
- **Frontend Compilation:** `make build` compiles the React client using Vite.
- **End-to-End Verification:** `make verify-e2e` drives headless browser tests across desktop, tablet, and mobile layouts to evaluate UI interaction, saving traces to `src/backend/verify-output/e2e/`.
- **System Health Diagnostics:** `alma verify` validates real endpoints (`/api/generate`, `/api/generate-with-thinking`, `/api/health`) to distinguish quota issues from systemic errors.

## Security & Trust Boundaries

1. **Credential Isolation:** Provider credentials never reach the browser client.
2. **Backend Proxying:** External search and AI calls are strictly proxied through backend controllers.
3. **Isolated Environments:** Sensitive values reside solely in server `.env` files.
4. **Isolated User Context:** Conversations use isolated anonymous client tokens for privacy.

> **Note:** Alma does not natively provide storage encryption at rest or built-in user identity management beyond anonymous session identifiers.

## Getting Started

### Prerequisites

- **Python 3.9+** with [uv](https://docs.astral.sh/uv/) installed
- **Node.js** (v18+) and **npm**

### Setup Environment

```bash
# Sync backend dependencies
uv sync

# Install frontend dependencies
cd src/frontend && npm install && cd ../..
```

Create a `.env` file in the project root containing your preferred credentials as described in the [Configuration](#configuration) section.

### Launch Local Development Server

```bash
make dev
```

- **Frontend Interface:** `http://localhost:3000`
- **Backend API:** `http://localhost:8000`

*Optional auxiliary services:*
- Static Web Mirror: `./scripts/dev.sh static` (Port `5001`)
- Go Text Processor: `./scripts/dev.sh go` (Port `8080`)

## Repository Structure

```
src/
├── backend/         # Flask API, router logic, AI providers, search pipelines, and tests
├── frontend/        # React application source code
├── static/          # Static Web UI (mirroring the main client)
├── api/             # Serverless entry points (e.g., Vercel)
├── go/              # High-performance Go text-processing service
└── swift/           # Native macOS client wrapper
docs/                # System documentation and architecture decisions
scripts/             # Setup and CLI helper scripts
```

## Development Commands

Keep the main workflows in one place. Each command answers a specific question:

```bash
make lint          # Is the code clean?
make test          # Do backend tests pass?
make build         # Does the frontend build?
make verify-e2e    # Does the product work through a real browser?
```

## Troubleshooting

### Internal Server Error (HTTP 500)

An HTTP 500 indicates an unhandled server-side exception. The frontend will show a generic failure state while details are logged on the server.

1. Inspect the backend terminal console for python tracebacks.
2. Confirm your `.env` configuration file is present and properly formatted.
3. Verify that your API keys are active and have available quota.
4. Restart the backend service following any `.env` modification.
5. When opening an issue, provide the target route, server traceback logs, and non-sensitive environment settings.