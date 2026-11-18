"""Diagnostics support for the WTH UMR2 integration."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .coordinator import WTHCoordinator


def _list_count(section: Any) -> int:
    """Return the length of a list section without exposing its contents."""
    return len(section) if isinstance(section, list) else 0


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry[WTHCoordinator]
) -> dict[str, Any]:
    """Return safe diagnostics for a WTH UMR2 config entry."""
    del hass
    coordinator = entry.runtime_data
    data = coordinator.data
    communications = data.get("communications", {})

    return {
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "sections": sorted(data),
        },
        "version": {
            key: data.get("version", {}).get(key)
            for key in ("fw", "hw", "fwBuild", "json")
            if key in data.get("version", {})
        },
        "main": {
            key: data.get("main", {}).get(key)
            for key in ("state", "mode", "led")
            if key in data.get("main", {})
        },
        "counts": {
            "thermostats": _list_count(data.get("inputs", {}).get("thermostats")),
            "temperature_sensors": _list_count(
                data.get("inputs", {}).get("tSensors")
            ),
            "valves": _list_count(data.get("outputs", {}).get("valves")),
        },
        "communications": {
            name: {
                "state": section.get("state"),
                "device_count": _list_count(section.get("devices")),
            }
            for name, section in communications.items()
            if isinstance(section, dict)
        },
    }
