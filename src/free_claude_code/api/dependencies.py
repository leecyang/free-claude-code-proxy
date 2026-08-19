"""FastAPI dependencies for the explicit runtime service boundary."""

import secrets

from fastapi import Depends, HTTPException, Request
from loguru import logger

from free_claude_code.application.errors import UnknownProviderError
from free_claude_code.application.ports import ProviderPort, RequestRuntimeLease
from free_claude_code.config.provider_catalog import PROVIDER_CATALOG
from free_claude_code.config.settings import Settings

from .ports import ApiServices


def get_services(request: Request) -> ApiServices:
    """Return the complete services supplied when the app was constructed."""
    return request.app.state.services


def get_settings(services: ApiServices = Depends(get_services)) -> Settings:
    """Return the current request-runtime settings snapshot."""
    return services.requests.current_settings()


def resolve_provider(
    provider_type: str,
    *,
    lease: RequestRuntimeLease,
) -> ProviderPort:
    """Resolve a provider through one retained generation."""
    should_log_init = not lease.is_provider_cached(provider_type)
    try:
        provider = lease.resolve_provider(provider_type)
    except UnknownProviderError:
        logger.error(
            "Unknown provider_type: '{}'. Supported: {}",
            provider_type,
            ", ".join(f"'{key}'" for key in PROVIDER_CATALOG),
        )
        raise
    if should_log_init:
        logger.info("Provider initialized: {}", provider_type)
    return provider


def _accepted_tokens(settings: Settings) -> tuple[str, ...]:
    """Return every token that authenticates a proxy request."""
    return (settings.proxy_auth_token, *settings.public_api_keys)


def require_proxy_auth(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> None:
    """Require the configured proxy token as HTTP bearer authorization.

    Any one of the retained ``proxy_auth_token`` or the configured
    ``public_api_keys`` authenticates a request.
    """
    if not settings.proxy_auth_enabled:
        return

    authorization = request.headers.get("authorization")
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing proxy authentication token",
        )

    parts = authorization.strip().split(maxsplit=1)
    if len(parts) != 2 or parts[0].casefold() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid proxy authentication token",
        )
    token = parts[1].strip()

    token_bytes = token.encode("utf-8")
    if not token or not any(
        secrets.compare_digest(token_bytes, accepted.encode("utf-8"))
        for accepted in _accepted_tokens(settings)
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid proxy authentication token",
        )
