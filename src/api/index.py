# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
#
# Vercel serverless entrypoint.
#
# This thin wrapper ensures the backend package is importable
# and re-exports the Flask WSGI application. Every request
# through Vercel executes the same `create_app()` code that
# development and CI use.
#
# The alternative — duplicating API logic in a separate
# BaseHTTPRequestHandler — was intentionally avoided to
# prevent drift between environments.

import sys
import os

_HERE = os.path.dirname(os.path.abspath(__file__))  # src/api
_ROOT = os.path.dirname(_HERE)  # src
_BACKEND = os.path.join(_ROOT, "backend")  # src/backend

for path in (_ROOT, _BACKEND):
    if path not in sys.path:
        sys.path.insert(0, path)

from backend.app import app  # noqa: E402, F401 — WSGI handler for Vercel
