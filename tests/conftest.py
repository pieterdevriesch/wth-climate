"""Pytest configuration for the integration tests."""
from __future__ import annotations

import asyncio

import pytest
import pytest_socket


@pytest.fixture
def event_loop() -> asyncio.AbstractEventLoop:
    """Provide a Windows event loop after the HA socket guard is installed."""
    pytest_socket.enable_socket()
    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        loop.close()
