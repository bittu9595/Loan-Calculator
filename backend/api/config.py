"""Runtime configuration sourced from environment variables."""

from __future__ import annotations

import os

# Comma-separated list of origins allowed to call this API. Defaults to the
# local frontend dev servers only - never default to "*" in production, since
# an unrestricted CORS policy is an OWASP-flagged security misconfiguration.
_DEFAULT_ALLOWED_ORIGINS = "http://localhost:5173,http://localhost:3000"


def get_allowed_origins() -> list[str]:
    raw = os.environ.get("ALLOWED_ORIGINS", _DEFAULT_ALLOWED_ORIGINS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]
