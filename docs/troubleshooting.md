# Troubleshooting Guide

This guide helps diagnose common issues with the Alma application endpoints.

## API Endpoint Diagnostics

### General Debugging Steps

1. **Check server logs**: Run the app with debug mode to see the full error traceback:
   ```bash
   uv run python static_app.py
   ```
   Look for the exception details in the console output.

2. **Verify API key**: Ensure `GEMINI_API_KEY` is set in your `.env` file and the key is valid.

3. **Common causes**:
   - Invalid or missing Gemini API key
   - Network connectivity issues
   - Changes in Gemini API response format
   - Model-specific parameters may not be supported (e.g., `thinking_config` for older models)
   - API quota exhaustion (especially for image generation)

4. **Test the endpoint**: Try a simple request to isolate the issue:
   ```bash
   curl -X POST http://localhost:5001/api/generate-with-thinking \
    -H "Content-Type: application/json" \
    -d '{"prompt": "Hello"}'
   ```
   Check the server console for the specific exception message to identify the root cause.

### Endpoint-Specific Issues

#### `/api/generate-with-thinking` (500 errors)

- **Model not found**: Update model names in `backend/palmshed_ai/models.py` to current Gemini API models
- **Thinking config issues**: Ensure using Gemini 2.5 series models that support thinking mode
- **Response parsing errors**: Check if API response structure has changed

#### `/api/generate-image` (429/404 errors)

- **Quota exhausted**: Free tier has limited image generation requests
- **Model unavailable**: Image generation models may have restricted access
- **Wait for quota reset**: Quotas typically reset every few minutes

#### `/api/text-to-speech` (500 errors)

- **gTTS library issues**: Check if gtts package is installed and network access available
- **File system permissions**: Ensure temp directory is writable

### Environment Setup

Ensure your `.env` file contains:
```
GEMINI_API_KEY=your_valid_api_key_here
```

For Imagen models, also set:
```
GOOGLE_CLOUD_PROJECT=your_project_id
GOOGLE_CLOUD_LOCATION=us-central1
```

### Model Configuration

Current working models (as of July 2026):
- **Text generation**: `gemini-2.5-flash`
- **Thinking mode**: `gemini-2.5-flash` (switched from `gemini-2.5-pro` due to free tier quota)
- **URL context**: `gemini-2.5-flash`
- **Image generation**: `gemini-2.5-flash-image` (switched from `imagen-4.0-generate-001` which requires Vertex AI)

### Vertex AI / Imagen Issues

1. **"Vertex AI not available"**: Install optional Vertex AI dependency:
   ```bash
   uv add --group vertex-ai google-cloud-aiplatform
   ```

2. **"GOOGLE_CLOUD_PROJECT required"**: Add to your `.env` file:
   ```
   GOOGLE_CLOUD_PROJECT=your_project_id
   GOOGLE_CLOUD_LOCATION=us-central1
   ```

3. **Authentication errors**: Run `gcloud auth application-default login`

4. **Billing required**: Enable billing on your Google Cloud project for Imagen models

### Getting Help

If issues persist:
1. Check the [Gemini API documentation](https://ai.google.dev/gemini-api/docs)
2. Check the [Vertex AI documentation](https://cloud.google.com/vertex-ai/docs) for Imagen
3. Monitor API usage at [Google AI Studio](https://ai.dev/usage)
4. Review server logs for detailed error messages
5. Test with different prompts/models to isolate the issue
