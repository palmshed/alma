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
