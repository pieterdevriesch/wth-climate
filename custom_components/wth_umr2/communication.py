"""Communication data helpers for the WTH UMR2 regulator."""
from __future__ import annotations

from typing import Any

COMMUNICATION_NAMES = (
    "fanlink",
    "rf",
    "modbus",
    "bluetooth",
    "ethernet",
    "json",
    "usb",
)

COMMUNICATION_PATHS: tuple[tuple[str, ...], ...] = tuple(
    ("communications", name) for name in COMMUNICATION_NAMES
)


def get_communication(data: dict[str, Any], name: str) -> dict[str, Any]:
    """Return one communication section from coordinator data."""
    section = data.get("communications", {}).get(name, {})
    return section if isinstance(section, dict) else {}


def get_process_communication(data: dict[str, Any], name: str) -> dict[str, Any]:
    """Return process-level data for one communication interface."""
    section = data.get("process", {}).get("communications", {}).get(name, {})
    return section if isinstance(section, dict) else {}


def get_communication_devices(
    data: dict[str, Any], name: str
) -> list[dict[str, Any]]:
    """Return devices reported for one communication interface."""
    devices = get_communication(data, name).get("devices", [])
    return devices if isinstance(devices, list) else []
