"""Access control for the FCC admin UI."""

import base64
import binascii
import ipaddress
import os
import secrets
from urllib.parse import urlsplit

from fastapi import HTTPException, Request

from free_claude_code.config.loader import get_settings

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


def _is_loopback(host: str | None) -> bool:
    if not host:
        return False
    normalized = host.strip().strip("[]").lower()
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def _origin_host(origin: str | None) -> str | None:
    if not origin:
        return None
    return urlsplit(origin).hostname


def _remote_enabled() -> bool:
    return os.getenv("FCC_ADMIN_REMOTE_ENABLED", "").strip().lower() in _TRUE_VALUES


def _remote_host() -> str:
    return os.getenv("FCC_ADMIN_REMOTE_HOST", "").strip().rstrip(".").lower()


def _basic_password(request: Request) -> str | None:
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "basic" or not token:
        return None
    try:
        decoded = base64.b64decode(token, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return None
    username, separator, password = decoded.partition(":")
    if not separator or username != "admin":
        return None
    return password


def require_admin_access(request: Request) -> None:
    """Allow local admin access or an explicitly enabled HTTPS admin hostname.

    Remote access uses HTTP Basic authentication. The username is ``admin`` and
    the password is the retained ``ANTHROPIC_AUTH_TOKEN``. Keep that token private
    and distribute ``PUBLIC_API_KEYS`` to normal API clients instead.
    """

    client_host = request.client.host if request.client else None
    request_host = request.url.hostname
    origin_host = _origin_host(request.headers.get("origin"))
    settings = get_settings()

    trusted_client = _is_loopback(client_host) or (
        client_host in settings.admin_trusted_client_ips
    )
    local_origin = origin_host is None or _is_loopback(origin_host)
    if trusted_client and local_origin and (
        _is_loopback(client_host) or _is_loopback(request_host)
    ):
        return

    if not _remote_enabled():
        raise HTTPException(status_code=403, detail="Admin UI is local-only")

    expected_host = _remote_host()
    normalized_host = (request_host or "").rstrip(".").lower()
    normalized_origin = (origin_host or "").rstrip(".").lower()
    if not expected_host or normalized_host != expected_host:
        raise HTTPException(status_code=403, detail="Admin host is not allowed")
    if origin_host and normalized_origin != expected_host:
        raise HTTPException(status_code=403, detail="Admin origin is not allowed")

    password = _basic_password(request)
    if password is None or not secrets.compare_digest(
        password.encode("utf-8"), settings.proxy_auth_token.encode("utf-8")
    ):
        raise HTTPException(
            status_code=401,
            detail="Admin authentication required",
            headers={"WWW-Authenticate": 'Basic realm="FCC Admin"'},
        )
