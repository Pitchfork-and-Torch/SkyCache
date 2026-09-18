"""Admin API helpers (PIN-gated)."""

from __future__ import annotations

from fastapi import Header, HTTPException


def require_admin_pin(pin: str, x_admin_pin: str | None = Header(default=None)) -> None:
    if not x_admin_pin or x_admin_pin != pin:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Admin-Pin header")
