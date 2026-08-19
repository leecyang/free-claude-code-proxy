import asyncio

import httpx
import pytest
from openai import AsyncOpenAI

from free_claude_code.providers.key_rotation import KeyRotator
from tests.providers.support import (
    immediate_admission,
    make_provider_config,
    profiled_provider,
)


def test_key_rotator_cycles_through_keys_in_order() -> None:
    rotator = KeyRotator(["a", "b", "c"])

    keys = [asyncio.run(rotator.next_key()) for _ in range(5)]

    assert keys == ["a", "b", "c", "a", "b"]


def test_key_rotator_requires_at_least_one_key() -> None:
    with pytest.raises(ValueError):
        KeyRotator([])


def test_key_rotator_single_key_always_returns_it() -> None:
    rotator = KeyRotator(["only"])

    keys = [asyncio.run(rotator.next_key()) for _ in range(3)]

    assert keys == ["only", "only", "only"]


@pytest.mark.asyncio
async def test_retryable_429_uses_next_api_key() -> None:
    auth_headers: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        auth_headers.append(request.headers["authorization"])
        if len(auth_headers) == 1:
            return httpx.Response(
                429,
                json={"error": {"message": "rate limited", "type": "rate_limit"}},
            )
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            text="data: [DONE]\n\n",
        )

    provider = profiled_provider(
        "deepinfra",
        make_provider_config(
            api_key="key-a",
            api_keys=("key-a", "key-b"),
            base_url="https://provider.invalid/v1",
        ),
        admission=immediate_admission(provider_name="deepinfra", max_attempts=2),
    )
    await provider._client.close()
    key_rotator = provider._key_rotator
    assert key_rotator is not None
    provider._client = AsyncOpenAI(
        api_key=key_rotator.next_key,
        base_url="https://provider.invalid/v1",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        max_retries=0,
    )

    try:
        session = provider._admission.new_retry_session()
        stream, _body, attempt = await provider._create_stream(
            {"model": "test-model", "messages": []}, session
        )
        await attempt.succeeded()
        await stream.close()
        await attempt.aclose()
    finally:
        await provider.cleanup()

    assert auth_headers == ["Bearer key-a", "Bearer key-b"]
