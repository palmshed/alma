# Testing Guide

## Test Structure

Tests are located in the `backend/tests/` directory:

```
backend/tests/
└── test_app.py    # Basic Flask app tests
```

## Running Tests

```bash
# Run all tests
make test

# With coverage
PYTHONPATH=backend uv run pytest --cov=palmshed_ai --cov-report=html

# Specific test file
PYTHONPATH=backend uv run pytest backend/tests/test_app.py
```

## Current Test Coverage

### App Creation
```python
def test_app_creation():
    app = create_app()
    assert app is not None
    assert app.name == "palmshed_ai"
```

### Index Route
```python
def test_index_route():
    app = create_app()
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
```

### API Validation
```python
def test_generate_api_missing_prompt():
    app = create_app()
    client = app.test_client()
    response = client.post("/api/generate", json={})
    assert response.status_code == 400
```

## Missing Test Areas

- API endpoint functionality (text generation, TTS, image gen)
- Error handling scenarios
- File upload/download operations
- Authentication and security
- Integration tests with Gemini API
- Frontend JavaScript tests
- Performance and load tests

## Test Environment Setup

```bash
# Set dummy API key for testing
export GEMINI_API_KEY="dummy"

# Run tests
uv run pytest
```

## CI/CD Testing

Tests run automatically on:
- Push to main branch
- Pull requests to main
- Manual workflow dispatch

See `.github/workflows/ci.yml` for details.

## Adding New Tests

1. Create test functions in `tests/test_*.py`
2. Use pytest fixtures for setup
3. Mock external API calls
4. Test both success and error cases
5. Run `make test` to verify

---

## End-to-End (E2E) Browser Verification

E2E tests use Playwright to drive a real browser through Alma's user flows. They validate that the React UI, Flask backend, and browser environment work together correctly from the user's perspective.

### Prerequisites

```bash
# Install all dependencies (includes playwright)
uv sync

# Install the Chromium browser binary
uv run playwright install chromium
```

On CI, `--with-deps` installs system-level libraries (Xvfb, etc.) that Chromium needs on Linux:

```bash
uv run playwright install chromium --with-deps
```

### Running E2E

```bash
# Full E2E (all flows, all viewports) — the default
alma verify e2e

# Specific flows only
alma verify e2e --flow chat search themes

# Specific viewport only
alma verify e2e --viewport desktop

# JSON + HTML output
alma verify e2e --json --output backend/verify-output

# Just infrastructure check (no browser)
alma verify e2e --flow infra
```

Available flows: `infra`, `chat`, `search`, `thinking`, `voice`, `keyboard`, `themes`.

Available viewports: `desktop` (1280×800), `tablet` (768×1024), `mobile` (375×667).

### How It Works

1. **Infrastructure check** — hits `/api/health` and loads the frontend URL to confirm both servers are up.
2. **Disclaimer dismissal** — the first-visit disclaimer dialog is dismissed via JavaScript evaluate so it doesn't block interactions.
3. **Flow execution** — each flow opens a fresh browser context, navigates to the app, and performs a series of actions (type, click, assert).
4. **Error collection** — browser console errors are captured. Race-condition 404s and Gemini quota errors are filtered out.
5. **Quota detection** — if the Gemini API returns 429 RESOURCE_EXHAUSTED, subsequent API-dependent flows are skipped with `infra_fail` status instead of false failures.
6. **Report generation** — results are written to `report.json` and `report.html` in the output directory.

### Reading the Report

**Human-readable** (printed to terminal):

```
E2E VERIFICATION RESULTS — 2026-07-23 18:43:28 UTC

PASSED 42 | FAILED 0 | SKIPPED 23 | 65 TOTAL

DESKTOP (1420ms)    14/14 passed
  chat              pass (320ms) — 2 messages exchanged
  search            pass (210ms) — 6 source cards, 1 search bar
  thinking          pass (180ms) — thinking toggle present
  voice             pass (150ms) — TTS container, button, audio found
  keyboard          pass (120ms) — Enter submits, Escape closes sidebar
  themes            pass (140ms) — dark: present, light: present, toggle: present
  infra             pass (100ms) — ...

TABLET (890ms)      14/14 passed
  ...
```

**Machine-readable** (`--json`):

```json
{
  "timestamp": "2026-07-23T18:43:28.111379Z",
  "flows": {
    "desktop": {
      "chat": {"status": "pass", "duration_ms": 320, "detail": "2 messages exchanged"},
      "search": {"status": "pass", "duration_ms": 210}
    }
  },
  "summary": {"passed": 14, "failed": 0, "skipped": 23, "total": 37}
}
```

Status values: `pass`, `fail`, `infra_fail` (infrastructure issue, not a product bug), `skip` (quota exhausted or flow not requested).

### CI Integration

E2E runs in GitHub Actions on every push to `main` and daily at 06:00 UTC. See `.github/workflows/e2e.yml`.

On failure, the workflow uploads:
- Screenshots (`.png`)
- HTML report (`report.html`)
- JSON report (`report.json`)
- Playwright traces (`trace.zip`) for debugging failed flows
