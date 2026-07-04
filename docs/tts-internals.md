# TTS Internals

## Text-to-Speech Implementation

Alma uses Google Text-to-Speech (gTTS) for converting text to audio:

```python
from gtts import gTTS
import tempfile
import uuid

def text_to_speech(text: str) -> str:
    """Convert text to speech and return file path."""
    if not text or len(text) > 1000:
        raise ValueError("Invalid text")

    filename = f"{uuid.uuid4()}.mp3"
    filepath = os.path.join(tempfile.gettempdir(), "gemini_tts", filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    tts = gTTS(text=text, lang="en", slow=False)
    tts.save(filepath)
    return filepath
```

## Audio File Management

- Files are stored in system temp directory
- Unique UUID-based filenames prevent conflicts
- MP3 format for broad compatibility
- Automatic cleanup handled by OS temp management

## Limitations

- Max 1000 characters per request
- English language only (gTTS default)
- Synchronous processing (no streaming)
- Temporary file storage (not persistent)

## Future Enhancements

- Multiple language support
- Streaming audio generation
- Persistent storage options
- Voice customization
