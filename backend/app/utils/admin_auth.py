from __future__ import annotations

from typing import Optional
import secrets

from fastapi import Request

from app.config.settings import settings


def is_force_refresh_allowed(request: Optional[Request]) -> bool:
    if request is None:
        return True

    admin_key = settings.ADMIN_API_KEY
    if not admin_key:
        return False

    header_key = request.headers.get("x-admin-key", "")
    if not header_key:
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            header_key = auth_header[7:]

    return bool(header_key) and secrets.compare_digest(header_key, admin_key)
