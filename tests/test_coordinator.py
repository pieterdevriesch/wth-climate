"""Tests for the WTH UMR2 coordinator."""
from __future__ import annotations

import asyncio
from typing import Any, Self

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.wth_umr2 import STATUS_PATHS, WTHCoordinator


class FakeResponse:
    """Minimal async HTTP response used by coordinator tests."""

    def __init__(self, data: dict[str, Any], status: int = 200) -> None:
        """Initialize the response."""
        self.status = status
        self._data = data

    async def __aenter__(self) -> Self:
        """Enter the response context."""
        return self

    async def __aexit__(self, *args: object) -> None:
        """Exit the response context."""

    async def json(self) -> dict[str, Any]:
        """Return the response JSON."""
        return self._data


class FakeSession:
    """Minimal async HTTP session used by coordinator tests."""

    def __init__(self, response: FakeResponse) -> None:
        """Initialize the session."""
        self.response = response
        self.url: str | None = None

    def get(self, url: str) -> FakeResponse:
        """Return the configured response."""
        self.url = url
        return self.response


def make_coordinator(session: FakeSession) -> WTHCoordinator:
    """Create a coordinator without starting Home Assistant."""
    coordinator = object.__new__(WTHCoordinator)
    coordinator.host = "192.0.2.10"
    coordinator._session = session
    return coordinator


def run_async(coroutine: Any) -> Any:
    """Run a coroutine without the Windows HA event-loop fixture."""
    return asyncio.run(coroutine)


def test_update_data_splits_and_merges_status_paths() -> None:
    """Each API path should be requested and restored under its original keys."""
    coordinator = make_coordinator(FakeSession(FakeResponse({})))
    requested: list[tuple[str, ...]] = []

    async def fetch(path: tuple[str, ...]) -> dict[str, Any]:
        requested.append(path)
        return {"state": ".".join(path)}

    coordinator._async_fetch_status_path = fetch

    result = run_async(coordinator._async_update_data())

    assert requested == list(STATUS_PATHS)
    assert result["version"]["state"] == "version"
    assert result["communications"]["rf"]["state"] == "communications.rf"
    assert result["communications"]["usb"]["state"] == "communications.usb"


def test_fetch_status_path_returns_requested_section() -> None:
    """A valid response should return the requested nested section."""
    response = FakeResponse(
        {
            "status": {
                "communications": {
                    "rf": {"state": "Connected"},
                },
            },
        }
    )
    session = FakeSession(response)
    coordinator = make_coordinator(session)

    result = run_async(
        coordinator._async_fetch_status_path(("communications", "rf"))
    )

    assert result == {"state": "Connected"}
    assert session.url == (
        "http://192.0.2.10/get.json?f=$.status.communications.rf.*"
    )


def test_fetch_status_path_rejects_missing_section() -> None:
    """A response without the requested section should fail the update."""
    response = FakeResponse({"status": {"communications": {}}})
    coordinator = make_coordinator(FakeSession(response))

    with pytest.raises(UpdateFailed, match="missing or empty"):
        run_async(coordinator._async_fetch_status_path(("communications", "rf")))
