# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT

import os
import tempfile
import pytest
from unittest.mock import patch
from palmshed_ai import create_app

# Set dummy API key for testing
os.environ["GEMINI_API_KEY"] = "dummy"


@pytest.fixture
def app():
    """Create and configure a test app instance."""
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


def test_app_creation():
    """Test that the Flask app creates successfully."""
    app = create_app()
    assert app is not None
    assert app.name == "palmshed_ai"


@patch("palmshed_ai.routes.api.ai.generate_text")
def test_generate_api_success(mock_generate, client):
    """Test the generate API with valid prompt."""
    mock_generate.return_value = "Mocked response"

    response = client.post("/api/generate", json={"prompt": "Test prompt"})
    assert response.status_code == 200
    data = response.get_json()
    assert "response" in data
    assert data["response"] == "Mocked response"
    mock_generate.assert_called_once()


def test_generate_api_missing_prompt(client):
    """Test the generate API with missing prompt."""
    response = client.post("/api/generate", json={})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "No prompt provided" in data["error"]


def test_generate_api_empty_prompt(client):
    """Test the generate API with empty prompt."""
    response = client.post("/api/generate", json={"prompt": ""})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "No prompt provided" in data["error"]


def test_generate_api_prompt_too_long(client):
    """Test the generate API with prompt exceeding max length."""
    long_prompt = "a" * 5001  # Max is 5000
    response = client.post("/api/generate", json={"prompt": long_prompt})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "Prompt too long" in data["error"]


@patch("palmshed_ai.routes.api.ai.generate_text_with_thinking")
def test_generate_with_thinking_success(mock_thinking, client):
    """Test the thinking mode API with valid prompt."""
    mock_response = {
        "response": "Mocked thinking response",
        "thinking_summary": ["Step 1", "Step 2"],
    }
    mock_thinking.return_value = mock_response

    response = client.post(
        "/api/generate-with-thinking", json={"prompt": "Test prompt"}
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data == mock_response
    mock_thinking.assert_called_once()


def test_generate_with_thinking_missing_prompt(client):
    """Test the thinking mode API with missing prompt."""
    response = client.post("/api/generate-with-thinking", json={})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "No prompt provided" in data["error"]


@patch("palmshed_ai.routes.api.ai.generate_text_with_url_context")
def test_generate_with_url_context_success(mock_url_context, client):
    """Test the URL context API with valid prompt."""
    mock_url_context.return_value = "Mocked URL context response"

    response = client.post(
        "/api/generate-with-url-context", json={"prompt": "Test prompt"}
    )
    assert response.status_code == 200
    data = response.get_json()
    assert "response" in data
    assert data["response"] == "Mocked URL context response"
    mock_url_context.assert_called_once()


def test_generate_with_url_context_missing_prompt(client):
    """Test the URL context API with missing prompt."""
    response = client.post("/api/generate-with-url-context", json={})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "No prompt provided" in data["error"]


@patch("palmshed_ai.routes.api.ai.text_to_speech")
def test_text_to_speech_success(mock_tts, client):
    """Test the TTS API with valid text."""
    # Use a path within the expected temp directory
    temp_audio_path = os.path.join(
        tempfile.gettempdir(), "gemini_tts", "test_audio.mp3"
    )
    # Create the file so send_file works
    os.makedirs(os.path.dirname(temp_audio_path), exist_ok=True)
    with open(temp_audio_path, "wb") as f:
        f.write(b"fake audio data")
    mock_tts.return_value = temp_audio_path

    try:
        response = client.post("/api/text-to-speech", json={"text": "Hello world"})
        assert response.status_code == 200
        # Should return a file download
        assert response.headers["Content-Type"] == "audio/mp3"
        mock_tts.assert_called_once_with("Hello world")
    finally:
        # Clean up
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)


def test_text_to_speech_missing_text(client):
    """Test the TTS API with missing text."""
    response = client.post("/api/text-to-speech", json={})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "No text provided" in data["error"]


def test_text_to_speech_empty_text(client):
    """Test the TTS API with empty text."""
    response = client.post("/api/text-to-speech", json={"text": ""})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "No text provided" in data["error"]


def test_text_to_speech_text_too_long(client):
    """Test the TTS API with text exceeding max length."""
    long_text = "a" * 1001  # Max is 1000
    response = client.post("/api/text-to-speech", json={"text": long_text})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "Text too long" in data["error"]


@patch("palmshed_ai.routes.api.ai.generate_image")
def test_generate_image_success(mock_image_gen, client):
    """Test the image generation API with valid prompt."""
    # Use a path within the expected temp directory
    temp_image_path = os.path.join(
        tempfile.gettempdir(), "generated_images", "test_image.png"
    )
    # Create the file so send_file works
    os.makedirs(os.path.dirname(temp_image_path), exist_ok=True)
    with open(temp_image_path, "wb") as f:
        f.write(b"fake image data")
    mock_image_gen.return_value = temp_image_path

    try:
        response = client.post(
            "/api/generate-image", json={"prompt": "A beautiful sunset"}
        )
        assert response.status_code == 200
        # Should return a file
        assert "image" in response.headers["Content-Type"].lower()
        mock_image_gen.assert_called_once_with("A beautiful sunset")
    finally:
        # Clean up
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)


def test_generate_image_missing_prompt(client):
    """Test the image generation API with missing prompt."""
    response = client.post("/api/generate-image", json={})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "No prompt provided" in data["error"]


def test_generate_image_empty_prompt(client):
    """Test the image generation API with empty prompt."""
    response = client.post("/api/generate-image", json={"prompt": ""})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "No prompt provided" in data["error"]


def test_generate_image_prompt_too_long(client):
    """Test the image generation API with prompt exceeding max length."""
    long_prompt = "a" * 5001  # Max is 5000
    response = client.post("/api/generate-image", json={"prompt": long_prompt})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "Prompt too long" in data["error"]


@patch("palmshed_ai.routes.api.ai.generate_text")
def test_generate_api_exception_handling(mock_generate, client):
    """Test exception handling in generate API."""
    mock_generate.side_effect = Exception("API Error")

    response = client.post("/api/generate", json={"prompt": "Test"})
    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data
    assert data["error"] == "API Error"


@patch("palmshed_ai.routes.api.ai.generate_text_with_thinking")
def test_thinking_api_exception_handling(mock_thinking, client):
    """Test exception handling in thinking API."""
    mock_thinking.side_effect = Exception("Thinking API Error")

    response = client.post("/api/generate-with-thinking", json={"prompt": "Test"})
    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data
    assert data["error"] == "Thinking API Error"


@patch("palmshed_ai.routes.api.ai.generate_text_with_url_context")
def test_url_context_api_exception_handling(mock_url_context, client):
    """Test exception handling in URL context API."""
    mock_url_context.side_effect = Exception("URL Context API Error")

    response = client.post("/api/generate-with-url-context", json={"prompt": "Test"})
    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data
    assert data["error"] == "URL Context API Error"


@patch("palmshed_ai.routes.api.ai.text_to_speech")
def test_tts_api_exception_handling(mock_tts, client):
    """Test exception handling in TTS API."""
    mock_tts.side_effect = Exception("TTS API Error")

    response = client.post("/api/text-to-speech", json={"text": "Test"})
    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data
    assert data["error"] == "TTS API Error"


@patch("palmshed_ai.routes.api.ai.generate_image")
def test_image_api_exception_handling(mock_image_gen, client):
    """Test exception handling in image generation API."""
    mock_image_gen.side_effect = Exception("Image API Error")

    response = client.post("/api/generate-image", json={"prompt": "Test"})
    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data
    assert data["error"] == "Image API Error"


@patch("palmshed_ai.routes.api.ai.research_topic")
def test_research_api_success(mock_research, client):
    """Test the research API with valid topic."""
    mock_response = {"report": "Mocked research report", "citations": []}
    mock_research.return_value = mock_response

    response = client.post("/api/research", json={"topic": "Test topic"})
    assert response.status_code == 200
    data = response.get_json()
    assert data == mock_response
    mock_research.assert_called_once_with("Test topic")


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"topic": ""},
    ],
)
def test_research_api_no_topic(client, payload):
    """Test the research API with missing or empty topic."""
    response = client.post("/api/research", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "No topic provided" in data["error"]


def test_research_api_topic_too_long(client):
    """Test the research API with topic exceeding max length."""
    long_topic = "a" * 5001  # Max is 5000
    response = client.post("/api/research", json={"topic": long_topic})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "Topic too long" in data["error"]


@patch("palmshed_ai.routes.api.ai.research_topic")
def test_research_api_exception_handling(mock_research, client):
    """Test exception handling in research API."""
    mock_research.side_effect = Exception("Research API Error")

    response = client.post("/api/research", json={"topic": "Test"})
    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data
    assert data["error"] == "Internal server error"
