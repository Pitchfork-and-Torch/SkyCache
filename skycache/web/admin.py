"""Admin API helpers (PIN-gated)."""

from __future__ import annotations

import threading

from fastapi import HTTPException

_LOCK = threading.Lock()
_FAILS: dict[str, int] = {}
_LOCKOUT_AFTER = 5


def client_ip(request) -> str:
    client = getattr(request, "client", None) if request is not None else None
    host = getattr(client, "host", None) if client is not None else None
    return str(host or "unknown")


def require_admin_pin(pin: str, x_admin_pin: str | None = None, client_key: str | None = None) -> None:
    """Reject a missing or wrong PIN. Lock an IP out after a few failures."""
    ip = client_key or "unknown"
    with _LOCK:
        if _FAILS.get(ip, 0) >= _LOCKOUT_AFTER:
            raise HTTPException(status_code=429, detail="Too many PIN attempts")
    supplied = x_admin_pin or ""
    if supplied != pin:
        with _LOCK:
            _FAILS[ip] = _FAILS.get(ip, 0) + 1
            locked = _FAILS[ip] >= _LOCKOUT_AFTER
        if locked:
            raise HTTPException(status_code=429, detail="Too many PIN attempts")
        raise HTTPException(status_code=401, detail="Invalid or missing X-Admin-Pin header")
    with _LOCK:
        _FAILS[ip] = 0
