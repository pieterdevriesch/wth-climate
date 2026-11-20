"""Tests for WTH UMR2 diagnostics."""
from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import Mock

from custom_components.wth_umr2.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.wth_umr2.const import DOMAIN
from homeassistant.config_entries import ConfigEntry
from pytest_homeassistant_custom_component.common import MockConfigEntry


def make_entry(data: dict[str, Any]) -> ConfigEntry:
    """Create a config entry containing a fake coordinator."""
    entry = MockConfigEntry(
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
    entry.runtime_data = Mock(data=data, last_update_success=True)
    return entry


def run_async(coroutine: Any) -> Any:
    """Run a diagnostics coroutine."""
    return asyncio.get_event_loop().run_until_complete(coroutine)


def test_diagnostics_include_safe_health_summary() -> None:
    """Diagnostics should include health data without raw device details."""
    entry = make_entry(
        {
            "version": {"fw": "1.2.3", "hw": "A", "fwBuild": 42, "json": "1.0"},
            "main": {"state": "OK", "mode": "heating", "led": "Green On"},
            "inputs": {
                "thermostats": [{"index": 0}],
                "tSensors": [{"index": 0}],
            },
            "outputs": {"valves": [{"index": 0}]},
            "communications": {
                "bluetooth": {
                    "state": "Connected",
                    "devices": [{"index": 0, "serialNumber": "secret"}],
                }
            },
        }
    )

    result = run_async(async_get_config_entry_diagnostics(object(), entry))

    assert result["coordinator"]["last_update_success"] is True
    assert result["version"] == {
        "fw": "1.2.3",
        "hw": "A",
        "fwBuild": 42,
        "json": "1.0",
    }
    assert result["counts"] == {
        "thermostats": 1,
        "temperature_sensors": 1,
        "valves": 1,
    }
    assert result["communications"] == {
        "bluetooth": {"state": "Connected", "device_count": 1}
    }
    assert "secret" not in str(result)
    assert "192.0.2.10" not in str(result)
