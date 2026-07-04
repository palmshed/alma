# Advanced API Examples

## Raw Gemini API Usage

For advanced users, you can access the raw Google Gemini API directly:

```python
import google.generativeai as genai
from google import genai as google_genai
import os

# Configure API (use environment variables for security)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Text generation
model = genai.GenerativeModel("gemini-2.5-flash")
response = model.generate_content("Hello world")
print(response.text)

# Thinking mode
client = google_genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Explain photosynthesis",
    config={"thinking_config": {"include_thoughts": True}}
)
```

> **Security Note:** Never hardcode API keys in your code. Always use environment variables or secure credential management systems.

## URL Context Integration

```python
from google.genai import types

url_context_tool = types.Tool(url_context=types.UrlContext())
response = client.models.generate_content(
    model="gemini-2.5-flash-preview-05-20",
    contents="Search for latest AI news",
    config={"tools": [url_context_tool]}
)
```

## Image Generation

```python
from google.genai import types

contents = [
    types.Content(
        role="user",
        parts=[
            types.Part.from_text(text="Generate an image of a cat"),
        ],
    ),
]

generate_content_config = types.GenerateContentConfig(
    response_modalities=["image", "text"],
    response_mime_type="text/plain",
)

response = client.models.generate_content(
    model="gemini-2.0-flash-exp-image-generation",
    contents=contents,
    config=generate_content_config,
)
```

## Deep Research (Multi-step Research Tasks)

Use the Interactions API for autonomous research:

```python
from google import genai
import time

client = genai.Client(api_key="your-key")

# Start research task
interaction = client.interactions.create(
    agent="deep-research-pro-preview-12-2025",
    input="Research the history of Google TPUs.",
    background=True
)

# Poll for results
while True:
    status = client.interactions.get(interaction.name)
    if status.state.name == "COMPLETED":
        print("Report:", status.output)
        print("Citations:", getattr(status, 'citations', []))
        break
    elif status.state.name == "FAILED":
        print("Failed:", getattr(status, 'error', 'Unknown error'))
        break
    time.sleep(5)
```

### API Endpoint

POST `/api/research`

**Request:**
```bash
curl -X POST http://localhost:8000/api/research \
  -H "Content-Type: application/json" \
  -d '{"topic": "History of artificial intelligence"}'
```

**Response:**
```json
{
  "report": "Detailed research report...",
  "citations": ["Source 1", "Source 2"]
}
```

**Error (quota/access):**
```json
{
  "error": "Internal server error"
}
```
