## Dependencies

### Backend

| Package | Version | Purpose |
|---|---|---|
| Flask | 2.3.3 | Web framework |
| flask-cors | 6.0.0 | CORS support |
| flask-limiter | 3.5.1 | Rate limiting |
| google-generativeai | ≥0.3.1 | Gemini API (text, thinking, web) |
| google-genai | ≥0.1.0 | Gemini API (images) |
| gTTS | 2.5.4 | Text-to-speech |
| python-dotenv | 1.2.1 | Environment variables |
| redis | latest | Optional caching |

### Frontend

| Package | Version | Purpose |
|---|---|---|
| React | 18.3.1 | UI framework |
| react-dom | 18.3.1 | DOM rendering |
| react-markdown | 9.0.1 | Markdown rendering |
| remark-gfm | 4.0.1 | GitHub Flavored Markdown |
| lucide-react | 1.23.0 | Icons |
| Tailwind CSS | 4.1.17 | Styling |
| Vite | 8.0.14 | Build tool |
| TypeScript | 4.9.5 | Type safety |

---

## Troubleshooting

### Internal Server Error (HTTP 500)

An HTTP 500 response means the backend encountered an unexpected exception while processing the request. The browser only reports that the request failed. The underlying cause is available in the backend logs.

Common causes include:

- Missing or invalid environment variables
- AI provider or model configuration errors
- Missing API credentials
- Backend startup or dependency issues
- Unexpected runtime exceptions

To diagnose the issue:

1. Check the backend console or server logs for the traceback.
2. Verify that your environment variables are correctly configured.
3. Confirm the AI provider credentials and model configuration are valid.
4. Restart the backend after changing configuration.

When reporting a bug, include:

- The endpoint or action that failed
- The backend traceback
- Relevant environment details (excluding secrets)

The traceback is the authoritative source for diagnosing HTTP 500 errors.
