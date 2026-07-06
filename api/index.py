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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from backend.app import app  # noqa: F401 — WSGI handler for Vercel
