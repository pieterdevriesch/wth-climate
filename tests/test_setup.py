"""Tests for WTH UMR2 config-entry setup."""
from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryNotReady

import custom_components.wth_umr2 as integration
from custom_components.wth_umr2.const import DOMAIN


class FakeConfigEntries:
    """Minimal config-entry manager used by setup tests."""

    def __init__(self) -> None:
        """Initialize the manager."""
        self.async_forward_entry_setups = AsyncMock()


class FakeHass:
    """Minimal Home Assistant object used by setup tests."""

    def __init__(self) -> None:
        """Initialize Home Assistant state."""
        self.config_entries = FakeConfigEntries()


def make_entry() -> ConfigEntry:
    """Create a config entry for setup tests."""
    return ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="WTH UMR2 (192.0.2.10)",
        data={"host": "192.0.2.10"},
        source="user",
        entry_id="test-entry",
        discovery_keys={},
        options={},
        unique_id="192.0.2.10",
    )


def run_async(coroutine: Any) -> Any:
    """Run a setup coroutine."""
    return asyncio.run(coroutine)


def test_setup_entry_refreshes_forwards_platform_and_registers_device(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Successful setup should refresh data before forwarding the sensor platform."""
    hass = FakeHass()
    entry = make_entry()
    coordinator = Mock(
        host="192.0.2.10",
        data={"version": {"fw": "1.2.3", "hw": "A"}},
        async_config_entry_first_refresh=AsyncMock(),
        async_shutdown=AsyncMock(),
    )
    device_registry = Mock()
    device_registry.async_get_or_create = Mock()
    monkeypatch.setattr(integration, "WTHCoordinator", Mock(return_value=coordinator))
    monkeypatch.setattr(integration.dr, "async_get", Mock(return_value=device_registry))

    result = run_async(integration.async_setup_entry(hass, entry))

    assert result is True
    assert entry.runtime_data is coordinator
    coordinator.async_config_entry_first_refresh.assert_awaited_once_with()
    hass.config_entries.async_forward_entry_setups.assert_awaited_once_with(
        entry, integration.PLATFORMS
    )
    device_registry.async_get_or_create.assert_called_once_with(
        config_entry_id="test-entry",
        identifiers={(DOMAIN, "test-entry")},
        manufacturer="WTH",
        model="UMR2",
        name="WTH UMR2 Regulator",
        sw_version="1.2.3",
        hw_version="A",
        configuration_url="http://192.0.2.10",
    )


def test_setup_entry_shuts_down_and_propagates_unavailable_device(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unavailable device should prevent platform setup and be retried by HA."""
    hass = FakeHass()
    entry = make_entry()
    coordinator = Mock(
        host="192.0.2.10",
        data={},
        async_config_entry_first_refresh=AsyncMock(
            side_effect=ConfigEntryNotReady
        ),
        async_shutdown=AsyncMock(),
    )
    monkeypatch.setattr(integration, "WTHCoordinator", Mock(return_value=coordinator))

    with pytest.raises(ConfigEntryNotReady):
        run_async(integration.async_setup_entry(hass, entry))

    coordinator.async_config_entry_first_refresh.assert_awaited_once_with()
    coordinator.async_shutdown.assert_awaited_once_with()
    hass.config_entries.async_forward_entry_setups.assert_not_awaited()
