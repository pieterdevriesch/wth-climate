"""Tests for the WTH UMR2 config flow validation."""
from __future__ import annotations

import asyncio
from typing import Any, Self
from unittest.mock import AsyncMock, Mock

import pytest
from aiohttp import ClientError
from homeassistant.data_entry_flow import AbortFlow, FlowResult

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


def test_config_flow_shows_initial_form() -> None:
    """The user step should initially show the host form without errors."""
    result = run_async(config_flow.ConfigFlow().async_step_user())

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {}


def test_config_flow_creates_entry_after_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A valid device should produce a config entry."""
    flow = config_flow.ConfigFlow()
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = Mock()
    flow.async_create_entry = Mock(
        return_value={"type": "create_entry", "title": "WTH UMR2 (device)"}
    )
    validate = AsyncMock(return_value={"title": "WTH UMR2 (device)"})
    monkeypatch.setattr(config_flow, "validate_input", validate)

    result: FlowResult = run_async(
        flow.async_step_user({"host": "device"})
    )

    validate.assert_awaited_once_with(flow.hass, {"host": "device"})
    flow.async_set_unique_id.assert_awaited_once_with("device")
    flow._abort_if_unique_id_configured.assert_called_once_with()
    flow.async_create_entry.assert_called_once_with(
        title="WTH UMR2 (device)",
        data={"host": "device"},
    )
    assert result["type"] == "create_entry"


def test_config_flow_aborts_duplicate_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A host that is already configured should not create another entry."""
    flow = config_flow.ConfigFlow()
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = Mock(
        side_effect=AbortFlow("already_configured")
    )
    flow.async_create_entry = Mock()
    monkeypatch.setattr(
        config_flow,
        "validate_input",
        AsyncMock(return_value={"title": "WTH UMR2 (device)"}),
    )

    with pytest.raises(AbortFlow, match="already_configured"):
        run_async(flow.async_step_user({"host": "device"}))

    flow.async_set_unique_id.assert_awaited_once_with("device")
    flow._abort_if_unique_id_configured.assert_called_once_with()
    flow.async_create_entry.assert_not_called()


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (ConnectionError("Timeout"), "timeout"),
        (ConnectionError("connection refused"), "cannot_connect"),
        (ValueError("Invalid response"), "invalid_response"),
        (RuntimeError("unexpected"), "unknown"),
    ],
)
def test_config_flow_recovers_from_validation_errors(
    monkeypatch: pytest.MonkeyPatch,
    exception: Exception,
    error: str,
) -> None:
    """Validation errors should return the form with a translated error key."""
    flow = config_flow.ConfigFlow()
    validate = AsyncMock(side_effect=exception)
    monkeypatch.setattr(config_flow, "validate_input", validate)

    result: FlowResult = run_async(
        flow.async_step_user({"host": "device"})
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": error}
