"""Tests for the WTH UMR2 config flow validation."""
from __future__ import annotations

import asyncio
from typing import Any, Self

import pytest
from aiohttp import ClientError

from custom_components.wth_umr2 import config_flow
from custom_components.wth_umr2.const import DOMAIN


class FakeResponse:
    """Minimal async HTTP response used by config flow tests."""

    def __init__(self, data: Any, status: int = 200) -> None:
        """Initialize the response."""
        self.status = status
        self.data = data

    async def __aenter__(self) -> Self:
        """Enter the response context."""
        return self

    async def __aexit__(self, *args: object) -> None:
        """Exit the response context."""

    async def json(self) -> Any:
        """Return the configured JSON payload."""
        if isinstance(self.data, BaseException):
            raise self.data
        return self.data


class FakeSession:
    """Minimal async HTTP session used by config flow tests."""

    def __init__(self, response: FakeResponse) -> None:
        """Initialize the session."""
        self.response = response
        self.url: str | None = None

    def get(self, url: str) -> FakeResponse:
        """Return the configured response."""
        self.url = url
        return self.response


def run_async(coroutine: Any) -> Any:
    """Run a config flow coroutine."""
    return asyncio.run(coroutine)


def test_validate_input_accepts_valid_device(monkeypatch: pytest.MonkeyPatch) -> None:
    """A response with a non-empty version object should be accepted."""
    session = FakeSession(
        FakeResponse({"status": {"version": {"fw": "1.2.3"}}})
    )
    monkeypatch.setattr(config_flow, "async_get_clientsession", lambda hass: session)

    result = run_async(
        config_flow.validate_input(
            object(),  # type: ignore[arg-type]
            {"host": "192.0.2.10"},
        )
    )

    assert result == {"title": "WTH UMR2 (192.0.2.10)"}
    assert session.url == "http://192.0.2.10/get.json?f=$.status.version.*"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"status": {}},
        {"status": {"version": {}}},
        {"status": {"version": "1.2.3"}},
    ],
)
def test_validate_input_rejects_invalid_response(
    monkeypatch: pytest.MonkeyPatch, payload: dict[str, Any]
) -> None:
    """Malformed device responses should be reported as invalid."""
    session = FakeSession(FakeResponse(payload))
    monkeypatch.setattr(config_flow, "async_get_clientsession", lambda hass: session)

    with pytest.raises(ValueError, match="Invalid response"):
        run_async(config_flow.validate_input(object(), {"host": "device"}))  # type: ignore[arg-type]


def test_validate_input_maps_http_and_client_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Transport failures should be exposed as connection errors."""
    session = FakeSession(FakeResponse({}, status=503))
    monkeypatch.setattr(config_flow, "async_get_clientsession", lambda hass: session)

    with pytest.raises(ConnectionError, match="HTTP 503"):
        run_async(config_flow.validate_input(object(), {"host": "device"}))  # type: ignore[arg-type]

    session.response = FakeResponse(ClientError("connection refused"))
    with pytest.raises(ConnectionError, match="connection refused"):
        run_async(config_flow.validate_input(object(), {"host": "device"}))  # type: ignore[arg-type]


def test_config_flow_declares_domain_and_version() -> None:
    """The config flow must be registered for the integration domain."""
    assert config_flow.DOMAIN == DOMAIN
    assert config_flow.ConfigFlow.VERSION == 1
