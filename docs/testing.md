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
