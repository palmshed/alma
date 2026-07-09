# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
#
# Static web interface Flask application for Alma.
# Serves the original HTML/CSS/JS interface on port 5000.

import os
from flask import Flask, render_template, send_file, abort
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def create_static_app():
    """Create Flask app for serving static web interface."""
    app = Flask(
        __name__,
        static_folder="deploy/static/web/static",
        template_folder="deploy/static/web/templates",
    )
    CORS(app)  # Enable CORS for API calls

    # App-wide anonymous identity via HttpOnly cookie
    from palmshed_ai.identity import ensure_client_id, set_client_cookie

    app.before_request(ensure_client_id)
    app.after_request(set_client_cookie)

    # Register API blueprints for backend functionality
    from palmshed_ai.routes.api import api_bp
    from palmshed_ai.routes.conversations import conversations_bp

    app.register_blueprint(api_bp)
    app.register_blueprint(conversations_bp)

    # Static pages (Terms, Privacy, Contact, Help)
    PAGES_DIR = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../deploy/static/web/pages")
    )

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

    # Override the index route to serve static interface
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response

    return app


if __name__ == "__main__":
    app = create_static_app()
    app.run(host="0.0.0.0", port=5001, debug=True)
