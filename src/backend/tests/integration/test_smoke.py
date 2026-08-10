# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
import pytest
import os

os.environ["GEMINI_API_KEY"] = "dummy"


def test_smoke():
    import os

    os.environ["GEMINI_API_KEY"] = "dummy"
    from palmshed_ai import create_app

    app = create_app()
    client = app.test_client()
    if not os.path.exists(os.path.join(app.template_folder, "index.html")):
        pytest.skip("Frontend build not found")
    response = client.get("/")
    assert response.status_code == 200
    print("Integration test passed: Root endpoint responds")
