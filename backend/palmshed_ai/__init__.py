# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
#
# This module initializes the Flask application with CORS support,
# configures the Gemini API, and registers the API blueprint.

__version__ = "0.2.0"

from flask import Flask, send_file, request, abort
from .sdk import GeminiAI
from flask_cors import CORS
from flask_limiter import Limiter
from werkzeug.middleware.proxy_fix import ProxyFix

__all__ = ["create_app", "GeminiAI", "main"]
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def create_app():
    app = Flask(
        __name__,
        static_folder=os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../deploy/static/web/static")
        ),
        template_folder=os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../deploy/static/web")
        ),
    )
    CORS(app)  # Enable CORS for all routes

    # Conditionally apply ProxyFix if PROXY_COUNT is set and > 0
    proxy_count = int(os.environ.get("PROXY_COUNT", "0"))
    if proxy_count > 0:
        app.wsgi_app = ProxyFix(
            app.wsgi_app, x_for=proxy_count, x_proto=proxy_count, x_host=proxy_count
        )

    # Initialize rate limiter
    storage_uri = os.environ.get("REDIS_URL") or "memory://"
    limiter = Limiter(
        storage_uri=storage_uri,
        key_func=lambda: (
            request.remote_addr if hasattr(request, "remote_addr") else "unknown"
        ),
    )
    limiter.init_app(app)

    # App-wide anonymous identity via HttpOnly cookie
    from .identity import ensure_client_id, set_client_cookie

    app.before_request(ensure_client_id)
    app.after_request(set_client_cookie)

    # Register blueprints
    from .routes.api import api_bp
    from .routes.attachments import attachments_bp
    from .routes.conversations import conversations_bp

    app.register_blueprint(api_bp)
    app.register_blueprint(attachments_bp)
    app.register_blueprint(conversations_bp)

    # Apply rate limiting to API routes
    limiter.limit("100/hour")(api_bp)

    PAGES_DIR = os.path.join(app.template_folder, "pages")

    PAGE_ROUTES = {
        "/terms": "terms.html",
        "/privacy": "privacy.html",
        "/contact": "contact.html",
        "/help": "help.html",
    }

    def _serve_page(filepath):
        def handler():
            if os.path.isfile(filepath):
                return send_file(filepath)
            abort(404)

        return handler

    for route, filename in PAGE_ROUTES.items():
        page_path = os.path.join(PAGES_DIR, filename)
        app.add_url_rule(route, endpoint=filename, view_func=_serve_page(page_path))

    # Serve React build for root route
    @app.route("/")
    def index():
        return send_file(os.path.join(app.template_folder, "index.html"))

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response

    return app


def main():
    """Entry point for the CLI application."""
    app = create_app()
    app.run()
