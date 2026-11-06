"""Tests for WTH UMR2 sensors."""
from __future__ import annotations

import asyncio
from typing import Any

from homeassistant.config_entries import ConfigEntry

from custom_components.wth_umr2 import WTHCoordinator
from custom_components.wth_umr2.const import DOMAIN
from custom_components.wth_umr2.sensor import (
    WTHCommunicationDeviceSensor,
    WTHMainStateSensor,
    WTHRFStatusSensor,
    WTHTemperatureSensor,
    WTHThermostatTemperatureSensor,
    async_setup_entry,
)


def make_coordinator(data: dict[str, Any]) -> WTHCoordinator:
    """Create a coordinator without starting Home Assistant."""
    coordinator = object.__new__(WTHCoordinator)
    coordinator.host = "192.0.2.10"
    coordinator.data = data
    coordinator.last_update_success = True
    return coordinator


def make_entry() -> ConfigEntry:
    """Create a config entry for sensor tests."""
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
        unique_id=None,
    )


def test_main_sensor_reads_state_and_attributes() -> None:
    """The main sensor should expose state and relevant status attributes."""
    coordinator = make_coordinator(
        {
            "version": {"fw": "1.2.3", "hw": "A"},
            "main": {
                "state": "heating",
                "message": "Running",
                "nightLowerActive": True,
            },
        }
    )
    sensor = WTHMainStateSensor(coordinator, make_entry())

    assert sensor.unique_id == "test-entry_main_state"
    assert sensor.native_value == "heating"
    assert sensor.extra_state_attributes == {
        "message": "Running",
        "kick": None,
        "button": None,
        "night_lower_active": True,
        "master_state": None,
        "global_heat_factor": None,
        "global_cool_factor": None,
        "global_pwm_factor": None,
    }


def test_indexed_temperature_sensors_use_controller_indexes() -> None:
    """Indexed sensors should find matching indexes rather than list positions."""
    coordinator = make_coordinator(
        {
            "inputs": {
                "tSensors": [
                    {"index": 4, "temperature": 18.5, "serialNumber": "abc"}
                ]
            },
            "process": {
                "thermostats": [
                    {"index": 2, "temperature": 21.0, "setpoint": 20.0}
                ]
            },
        }
    )
    entry = make_entry()

    temperature = WTHTemperatureSensor(coordinator, entry, 4)
    thermostat_temperature = WTHThermostatTemperatureSensor(coordinator, entry, 2)

    assert temperature.native_value == 18.5
    assert temperature.extra_state_attributes == {"serial_number": "abc"}
    assert thermostat_temperature.native_value == 21.0
    assert thermostat_temperature.extra_state_attributes == {"setpoint": 20.0}


def test_temperature_sensors_hide_non_positive_values() -> None:
    """Non-positive controller temperatures should not become HA states."""
    coordinator = make_coordinator(
        {
            "inputs": {"tSensors": [{"index": 0, "temperature": 0}]},
            "process": {"thermostats": [{"index": 0, "temperature": -1}]},
        }
    )
    entry = make_entry()

    temperature = WTHTemperatureSensor(coordinator, entry, 0)
    thermostat_temperature = WTHThermostatTemperatureSensor(coordinator, entry, 0)

    assert temperature.native_value is None
    assert thermostat_temperature.native_value is None
    assert temperature.entity_registry_enabled_default is False
    assert thermostat_temperature.entity_registry_enabled_default is False


def test_diagnostic_sensors_expose_status_and_device_type() -> None:
    """Diagnostic entities should expose communication data safely."""
    coordinator = make_coordinator(
        {
            "communications": {
                "rf": {"state": "Connected"},
                "bluetooth": {
                    "devices": [{"index": 3, "type": "Thermostat"}]
                },
            }
        }
    )
    entry = make_entry()

    status = WTHRFStatusSensor(coordinator, entry)
    device = WTHCommunicationDeviceSensor(coordinator, entry, "bluetooth", 3)

    assert status.native_value == "Connected"
    assert device.native_value == "Thermostat"
    assert device.unique_id == "test-entry_bluetooth_device_3"


def test_sensor_setup_creates_documented_entity_count() -> None:
    """Setup should create the complete documented set of sensor entities."""
    coordinator = make_coordinator({"version": {}})
    entry = make_entry()
    entry.runtime_data = coordinator
    entities: list[Any] = []

    def add_entities(new_entities: list[Any]) -> None:
        entities.extend(new_entities)

    asyncio.run(async_setup_entry(object(), entry, add_entities))  # type: ignore[arg-type]

    assert len(entities) == 114
    assert len({entity.unique_id for entity in entities}) == 114
