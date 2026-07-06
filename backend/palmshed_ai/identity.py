# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
#
# App-wide anonymous identity via HttpOnly cookie.
# Every request gets g.client_id, scoped by the alma_client cookie.

import uuid

from flask import g, request


COOKIE_NAME = "alma_client"
COOKIE_MAX_AGE = 365 * 24 * 60 * 60  # 1 year


def ensure_client_id():
    """Before-request handler: ensure g.client_id is set.

    Reads the alma_client cookie from the incoming request.
    If absent, generates a new UUID and marks it for the
    after-request handler to persist.
    """
    client_id = request.cookies.get(COOKIE_NAME)
    if not client_id:
        client_id = str(uuid.uuid4())
        g._alma_client_new = True
    g.client_id = client_id


def set_client_cookie(response):
    """After-request handler: persist alma_client cookie if newly generated.

    Only sets the cookie when the identity was just created
    (i.e. the first request from a browser that didn't have one).
    """
    if getattr(g, "_alma_client_new", False):
        response.set_cookie(
            COOKIE_NAME,
            g.client_id,
            httponly=True,
            secure=request.is_secure,
            samesite="Lax",
            path="/",
            max_age=COOKIE_MAX_AGE,
        )
    return response
