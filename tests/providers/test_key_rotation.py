import asyncio

import pytest

from free_claude_code.providers.key_rotation import KeyRotator


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
