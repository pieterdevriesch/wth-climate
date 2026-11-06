"""Tests for communication data helpers."""
from __future__ import annotations

from custom_components.wth_umr2.communication import (
    COMMUNICATION_NAMES,
    COMMUNICATION_PATHS,
    get_communication,
    get_communication_devices,
    get_process_communication,
)


def test_communication_paths_cover_all_interfaces() -> None:
    """Communication requests should cover every controller interface."""
    assert COMMUNICATION_PATHS == tuple(
        ("communications", name) for name in COMMUNICATION_NAMES
    )
    assert set(COMMUNICATION_NAMES) == {
        "fanlink",
        "rf",
        "modbus",
        "bluetooth",
        "ethernet",
        "json",
        "usb",
    }


def test_communication_helpers_return_expected_sections() -> None:
    """Communication helpers should safely access coordinator data."""
    data = {
        "communications": {
            "rf": {"state": "Connected", "devices": [{"index": 2}]},
        },
        "process": {
            "communications": {
                "rf": {"rawData": "01 02"},
            },
        },
    }

    assert get_communication(data, "rf")["state"] == "Connected"
    assert get_process_communication(data, "rf")["rawData"] == "01 02"
    assert get_communication_devices(data, "rf") == [{"index": 2}]


def test_communication_helpers_handle_missing_or_invalid_sections() -> None:
    """Communication helpers should return empty values for malformed data."""
    data = {
        "communications": {
            "rf": {"devices": "not a list"},
            "json": "not an object",
        },
        "process": {"communications": {"rf": None}},
    }

    assert get_communication(data, "missing") == {}
    assert get_communication(data, "json") == {}
    assert get_process_communication(data, "rf") == {}
    assert get_communication_devices(data, "rf") == []
