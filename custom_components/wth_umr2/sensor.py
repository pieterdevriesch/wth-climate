"""Sensor platform for WTH UMR2 Regulator."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
    EntityCategory,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .communication import (
    get_communication,
    get_communication_devices,
    get_process_communication,
)
from . import WTHCoordinator
from .const import DOMAIN


def _get_indexed_item(items: Any, index: int) -> dict[str, Any] | None:
    """Return an item by its controller-provided index."""
    if not isinstance(items, list):
        return None

    for item in items:
        if isinstance(item, dict) and item.get("index") == index:
            return item

    return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WTH UMR2 sensor based on a config entry."""
    coordinator: WTHCoordinator = entry.runtime_data
    
    entities: list[SensorEntity] = []
    
    # Main status sensors
    entities.extend([
        WTHMainStateSensor(coordinator, entry),
        WTHModeSensor(coordinator, entry),
        WTHDisplaySensor(coordinator, entry),
        WTHLEDSensor(coordinator, entry),
        WTHHeatFactorSensor(coordinator, entry),
        WTHCoolFactorSensor(coordinator, entry),
        WTHPWMFactorSensor(coordinator, entry),
    ])
    
    # Output sensors
    entities.extend([
        WTHHeaterSensor(coordinator, entry),
        WTHCoolerSensor(coordinator, entry),
        WTHPumpSpeedSensor(coordinator, entry),
    ])
    
    # Thermostat input sensors (8 inputs)
    for i in range(8):
        entities.extend([
            WTHThermostatSensor(coordinator, entry, i),
            WTHThermostatTemperatureSensor(coordinator, entry, i),
        ])

    # Thermostat process demand (10 controller channels)
    for i in range(10):
        entities.append(WTHThermostatDemandSensor(coordinator, entry, i))

    # Valve sensors (10 valves)
    for i in range(10):
        entities.append(WTHValveSensor(coordinator, entry, i))
    
    # Input sensors
    entities.extend([
        WTHMaxInputSensor(coordinator, entry),
        WTHReturnInputSensor(coordinator, entry),
        WTHCondensInputSensor(coordinator, entry),
        WTHPowerStealingSensor(coordinator, entry),
    ])
    
    # Temperature sensors (10 sensors)
    for i in range(10):
        entities.append(WTHTemperatureSensor(coordinator, entry, i))
    
    # Communication status sensors (diagnostic)
    entities.extend([
        WTHFanlinkStatusSensor(coordinator, entry),
        WTHRFStatusSensor(coordinator, entry),
        WTHModbusStatusSensor(coordinator, entry),
        WTHBluetoothStatusSensor(coordinator, entry),
        WTHEthernetStatusSensor(coordinator, entry),
        WTHJSONStatusSensor(coordinator, entry),
        WTHUSBStatusSensor(coordinator, entry),
        WTHFirmwareBuildSensor(coordinator, entry),
        WTHAPIVersionSensor(coordinator, entry),
    ])

    # Communication devices (diagnostic)
    for i in range(10):
        entities.append(WTHFanlinkDeviceSensor(coordinator, entry, i))
        entities.append(WTHCommunicationDeviceSensor(coordinator, entry, "rf", i))
        entities.append(WTHCommunicationDeviceSensor(coordinator, entry, "modbus", i))
        entities.append(WTHCommunicationDeviceSensor(coordinator, entry, "bluetooth", i))

    # PID diagnostics
    entities.extend([
        WTHPIDSensor(coordinator, entry, "pValue", "PID P Value"),
        WTHPIDSensor(coordinator, entry, "iValue", "PID I Value"),
        WTHPIDSensor(coordinator, entry, "dValue", "PID D Value"),
        WTHPIDSensor(
            coordinator,
            entry,
            "pumpFactor",
            "PID Pump Factor",
            percentage=True,
        ),
        WTHPIDSensor(
            coordinator,
            entry,
            "valveFactor",
            "PID Valve Factor",
            percentage=True,
        ),
    ])
    
    async_add_entities(entities)


class WTHBaseSensor(CoordinatorEntity[WTHCoordinator], SensorEntity):
    """Base class for WTH UMR2 sensors."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: WTHCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="WTH UMR2 Regulator",
            manufacturer="WTH",
            model="UMR2",
            sw_version=coordinator.data.get("version", {}).get("fw", "Unknown"),
            hw_version=coordinator.data.get("version", {}).get("hw", "Unknown"),
            configuration_url=f"http://{coordinator.host}",
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data is not None



class WTHMainStateSensor(WTHBaseSensor):
    """Sensor for main state."""

    _attr_name = "Main State"
    _attr_icon = "mdi:state-machine"

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self._entry.entry_id}_main_state"

    @property
    def native_value(self) -> str | None:
        """Return the state."""
        return self.coordinator.data.get("main", {}).get("state")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        main = self.coordinator.data.get("main", {})
        return {
            "message": main.get("message"),
            "kick": main.get("kick"),
            "button": main.get("button"),
            "night_lower_active": main.get("nightLowerActive"),
            "master_state": main.get("masterState"),
            "global_heat_factor": main.get("globalHeatFactor"),
            "global_cool_factor": main.get("globalCoolFactor"),
            "global_pwm_factor": main.get("globalPwmFactor"),
        }


class WTHModeSensor(WTHBaseSensor):
    """Sensor for operating mode."""

    _attr_name = "Operating Mode"
    _attr_icon = "mdi:thermostat"

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self._entry.entry_id}_mode"

    @property
    def native_value(self) -> str | None:
        """Return the mode."""
        return self.coordinator.data.get("main", {}).get("mode")


class WTHDisplaySensor(WTHBaseSensor):
    """Sensor for display value."""

    _attr_name = "Display"
    _attr_icon = "mdi:monitor"

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self._entry.entry_id}_display"

    @property
    def native_value(self) -> str | None:
        """Return the display value."""
        return self.coordinator.data.get("main", {}).get("display")


class WTHLEDSensor(WTHBaseSensor):
    """Sensor for LED status."""

    _attr_name = "LED Status"
    _attr_icon = "mdi:led-on"

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self._entry.entry_id}_led"

    @property
    def native_value(self) -> str | None:
        """Return the LED status."""
        return self.coordinator.data.get("main", {}).get("led")


class WTHHeatFactorSensor(WTHBaseSensor):
    """Sensor for heat factor."""

    _attr_name = "Heat Factor"
    _attr_icon = "mdi:fire"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self._entry.entry_id}_heat_factor"

    @property
    def native_value(self) -> int | None:
        """Return the heat factor."""
        return self.coordinator.data.get("main", {}).get("heatFactor")


class WTHCoolFactorSensor(WTHBaseSensor):
    """Sensor for cool factor."""

    _attr_name = "Cool Factor"
    _attr_icon = "mdi:snowflake"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self._entry.entry_id}_cool_factor"

    @property
    def native_value(self) -> int | None:
        """Return the cool factor."""
        return self.coordinator.data.get("main", {}).get("coolFactor")


class WTHPWMFactorSensor(WTHBaseSensor):
    """Sensor for PWM factor."""

    _attr_name = "PWM Factor"
    _attr_icon = "mdi:sine-wave"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self._entry.entry_id}_pwm_factor"

    @property
    def native_value(self) -> int | None:
        """Return the PWM factor."""
        return self.coordinator.data.get("main", {}).get("pwmFactor")


class WTHHeaterSensor(WTHBaseSensor):
    """Sensor for heater output."""

    _attr_name = "Heater Output"
    _attr_icon = "mdi:radiator"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self._entry.entry_id}_heater_output"

    @property
    def native_value(self) -> int | None:
        """Return the heater factor."""
        return self.coordinator.data.get("outputs", {}).get("heater", {}).get("factor")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        heater = self.coordinator.data.get("outputs", {}).get("heater", {})
        return {
            "state": heater.get("state"),
        }


class WTHCoolerSensor(WTHBaseSensor):
    """Sensor for cooler output."""

    _attr_name = "Cooler Output"
    _attr_icon = "mdi:air-conditioner"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self._entry.entry_id}_cooler_output"

    @property
    def native_value(self) -> int | None:
        """Return the cooler factor."""
        return self.coordinator.data.get("outputs", {}).get("cooler", {}).get("factor")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        cooler = self.coordinator.data.get("outputs", {}).get("cooler", {})
        return {
            "state": cooler.get("state"),
        }


class WTHPumpSpeedSensor(WTHBaseSensor):
    """Sensor for pump speed."""

    _attr_name = "Pump Speed"
    _attr_icon = "mdi:pump"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self._entry.entry_id}_pump_speed"

    @property
    def native_value(self) -> int | None:
        """Return the pump speed."""
        return self.coordinator.data.get("outputs", {}).get("pump", {}).get("speed")


class WTHThermostatSensor(WTHBaseSensor):
    """Sensor for thermostat status."""

    def __init__(self, coordinator: WTHCoordinator, entry: ConfigEntry, index: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._index = index
        self._attr_name = f"Thermostat {index + 1}"
        self._attr_icon = "mdi:thermostat"

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self._entry.entry_id}_thermostat_{self._index}"

    @property
    def native_value(self) -> str | None:
        """Return the thermostat state."""
        thermostats = self.coordinator.data.get("inputs", {}).get("thermostats", [])
        thermostat = _get_indexed_item(thermostats, self._index)
        return "on" if thermostat and thermostat.get("isOn") else "off" if thermostat else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        # Get both input and process thermostat data
        input_thermostats = self.coordinator.data.get("inputs", {}).get("thermostats", [])
        process_thermostats = self.coordinator.data.get("process", {}).get("thermostats", [])
        
        attrs = {}
        input_thermostat = _get_indexed_item(input_thermostats, self._index)
        process_thermostat = _get_indexed_item(process_thermostats, self._index)

        if input_thermostat:
            attrs["input_state"] = input_thermostat.get("isOn")
        
        if process_thermostat:
            attrs["temperature"] = process_thermostat.get("temperature")
            attrs["setpoint"] = process_thermostat.get("setpoint")
        
        return attrs


class WTHThermostatDemandSensor(WTHBaseSensor):
    """Sensor for thermostat demand factor."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:thermostat"

    def __init__(self, coordinator: WTHCoordinator, entry: ConfigEntry, index: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._index = index
        self._attr_name = f"Thermostat {index + 1} Demand"

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self._entry.entry_id}_thermostat_{self._index}_demand"

    @property
    def native_value(self) -> int | None:
        """Return the thermostat demand factor."""
        thermostats = self.coordinator.data.get("process", {}).get("thermostats", [])
        thermostat = _get_indexed_item(thermostats, self._index)
        return thermostat.get("factor") if thermostat else None


class WTHThermostatTemperatureSensor(WTHBaseSensor):
    """Sensor for thermostat temperature."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: WTHCoordinator, entry: ConfigEntry, index: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._index = index
        self._attr_name = f"Thermostat {index + 1} Temperature"
        thermostats = coordinator.data.get("process", {}).get("thermostats", [])
        thermostat = _get_indexed_item(thermostats, index)
        temperature = thermostat.get("temperature") if thermostat else None
        self._attr_entity_registry_enabled_default = (
            isinstance(temperature, (int, float)) and temperature > 0
        )

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self._entry.entry_id}_thermostat_{self._index}_temp"

    @property
    def native_value(self) -> float | None:
        """Return the temperature."""
        thermostats = self.coordinator.data.get("process", {}).get("thermostats", [])
        thermostat = _get_indexed_item(thermostats, self._index)
        if thermostat:
            temp = thermostat.get("temperature", 0.0)
            return temp if temp > 0 else None
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        thermostats = self.coordinator.data.get("process", {}).get("thermostats", [])
        thermostat = _get_indexed_item(thermostats, self._index)
        if thermostat:
            return {
                "setpoint": thermostat.get("setpoint"),
            }
        return {}


class WTHValveSensor(WTHBaseSensor):
    """Sensor for valve state."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:valve"

    def __init__(self, coordinator: WTHCoordinator, entry: ConfigEntry, index: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._index = index
        self._attr_name = f"Valve {index + 1}"

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self._entry.entry_id}_valve_{self._index}"

    @property
    def native_value(self) -> int | None:
        """Return the valve state."""
        valves = self.coordinator.data.get("outputs", {}).get("valves", [])
        valve = _get_indexed_item(valves, self._index)
        return valve.get("state") if valve else None


class WTHMaxInputSensor(WTHBaseSensor):
    """Sensor for max input."""

    _attr_name = "Max Input"
    _attr_icon = "mdi:thermometer-alert"

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self._entry.entry_id}_max_input"

    @property
    def native_value(self) -> str | None:
        """Return the state."""
        return self.coordinator.data.get("inputs", {}).get("max", {}).get("state")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        max_input = self.coordinator.data.get("inputs", {}).get("max", {})
        return {
            "message": max_input.get("message"),
            "temperature": max_input.get("temperature"),
        }


class WTHReturnInputSensor(WTHBaseSensor):
    """Sensor for return input."""

    _attr_name = "Return Input"
    _attr_icon = "mdi:thermometer"

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self._entry.entry_id}_return_input"

    @property
    def native_value(self) -> str | None:
        """Return the state."""
        return self.coordinator.data.get("inputs", {}).get("return", {}).get("state")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return_input = self.coordinator.data.get("inputs", {}).get("return", {})
        return {
            "message": return_input.get("message"),
            "temperature": return_input.get("temperature"),
        }


class WTHCondensInputSensor(WTHBaseSensor):
    """Sensor for condens input."""

    _attr_name = "Condens Input"
    _attr_icon = "mdi:water"

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self._entry.entry_id}_condens_input"

    @property
    def native_value(self) -> str | None:
        """Return the state."""
        return self.coordinator.data.get("inputs", {}).get("condens", {}).get("state")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        condens = self.coordinator.data.get("inputs", {}).get("condens", {})
        return {
            "message": condens.get("message"),
            "value": condens.get("value"),
            "temperature": condens.get("temperature"),
        }


class WTHPowerStealingSensor(WTHBaseSensor):
    """Sensor for power-stealing thermostat status."""

    _attr_name = "Power Stealing"
    _attr_icon = "mdi:flash"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self._entry.entry_id}_power_stealing"

    @property
    def native_value(self) -> str | None:
        """Return the power-stealing status."""
        return self.coordinator.data.get("inputs", {}).get("powerstealing", {}).get(
            "state"
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        powerstealing = self.coordinator.data.get("inputs", {}).get(
            "powerstealing", {}
        )
        return {"message": powerstealing.get("message")}


class WTHTemperatureSensor(WTHBaseSensor):
    """Sensor for temperature sensors."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: WTHCoordinator, entry: ConfigEntry, index: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._index = index
        self._attr_name = f"Temperature Sensor {index + 1}"
        sensors = coordinator.data.get("inputs", {}).get("tSensors", [])
        temperature = (
            sensors[index].get("temperature") if index < len(sensors) else None
        )
        self._attr_entity_registry_enabled_default = (
            isinstance(temperature, (int, float)) and temperature > 0
        )

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self._entry.entry_id}_temp_sensor_{self._index}"

    @property
    def native_value(self) -> float | None:
        """Return the temperature."""
        sensors = self.coordinator.data.get("inputs", {}).get("tSensors", [])
        sensor = _get_indexed_item(sensors, self._index)
        if sensor:
            temp = sensor.get("temperature", 0.0)
            return temp if temp > 0 else None
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        sensors = self.coordinator.data.get("inputs", {}).get("tSensors", [])
        sensor = _get_indexed_item(sensors, self._index)
        if sensor:
            return {
                "serial_number": sensor.get("serialNumber"),
            }
        return {}


class WTHFanlinkStatusSensor(WTHBaseSensor):
    """Sensor for Fanlink communication status."""

    _attr_name = "Fanlink Status"
    _attr_icon = "mdi:lan-connect"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self._entry.entry_id}_fanlink_status"

    @property
    def native_value(self) -> str | None:
        """Return the status."""
        return self.coordinator.data.get("communications", {}).get("fanlink", {}).get("state")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        fanlink = get_communication(self.coordinator.data, "fanlink")
        raw_data = get_process_communication(self.coordinator.data, "fanlink")
        return {
            "message": fanlink.get("message"),
            "raw_data": raw_data.get("rawData"),
        }


class WTHCommunicationStatusSensor(WTHBaseSensor):
    """Sensor for a communication interface status."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: WTHCoordinator,
        entry: ConfigEntry,
        communication: str,
        name: str,
        icon: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._communication = communication
        self._attr_name = name
        self._attr_icon = icon

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self._entry.entry_id}_{self._communication}_status"

    @property
    def native_value(self) -> str | None:
        """Return the communication status."""
        communication = get_communication(self.coordinator.data, self._communication)
        return communication.get("state")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        communication = get_communication(self.coordinator.data, self._communication)
        return {"message": communication.get("message")}


class WTHJSONStatusSensor(WTHCommunicationStatusSensor):
    """Sensor for JSON communication status."""

    def __init__(self, coordinator: WTHCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "json", "JSON Status", "mdi:code-json")


class WTHUSBStatusSensor(WTHCommunicationStatusSensor):
    """Sensor for USB communication status."""

    def __init__(self, coordinator: WTHCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "usb", "USB Status", "mdi:usb")


class WTHPIDSensor(WTHBaseSensor):
    """Sensor for a PID diagnostic value."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: WTHCoordinator,
        entry: ConfigEntry,
        key: str,
        name: str,
        percentage: bool = False,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._key = key
        self._attr_name = name
        self._attr_icon = "mdi:tune-vertical"
        if percentage:
            self._attr_native_unit_of_measurement = PERCENTAGE

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self._entry.entry_id}_pid_{self._key}"

    @property
    def native_value(self) -> int | None:
        """Return the PID value."""
        pid = self.coordinator.data.get("process", {}).get("pid", {})
        return pid.get(self._key)


class WTHFirmwareBuildSensor(WTHBaseSensor):
    """Sensor for firmware build number."""

    _attr_name = "Firmware Build"
    _attr_icon = "mdi:counter"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self._entry.entry_id}_firmware_build"

    @property
    def native_value(self) -> int | None:
        """Return the firmware build number."""
        return self.coordinator.data.get("version", {}).get("fwBuild")


class WTHAPIVersionSensor(WTHBaseSensor):
    """Sensor for the controller API version."""

    _attr_name = "API Version"
    _attr_icon = "mdi:code-json"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self._entry.entry_id}_api_version"

    @property
    def native_value(self) -> str | None:
        """Return the controller API version."""
        return self.coordinator.data.get("version", {}).get("json")


class WTHRFStatusSensor(WTHBaseSensor):
    """Sensor for RF communication status."""

    _attr_name = "RF Status"
    _attr_icon = "mdi:wifi"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self._entry.entry_id}_rf_status"

    @property
    def native_value(self) -> str | None:
        """Return the status."""
        return self.coordinator.data.get("communications", {}).get("rf", {}).get("state")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        rf = get_communication(self.coordinator.data, "rf")
        raw_data = get_process_communication(self.coordinator.data, "rf")
        return {
            "message": rf.get("message"),
            "raw_data": raw_data.get("rawData"),
        }


class WTHModbusStatusSensor(WTHBaseSensor):
    """Sensor for Modbus communication status."""

    _attr_name = "Modbus Status"
    _attr_icon = "mdi:serial-port"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self._entry.entry_id}_modbus_status"

    @property
    def native_value(self) -> str | None:
        """Return the status."""
        return self.coordinator.data.get("communications", {}).get("modbus", {}).get("state")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        modbus = get_communication(self.coordinator.data, "modbus")
        process_modbus = get_process_communication(self.coordinator.data, "modbus")
        return {
            "message": modbus.get("message"),
            "command": process_modbus.get("command"),
            "raw_data": process_modbus.get("rawData"),
        }


class WTHBluetoothStatusSensor(WTHBaseSensor):
    """Sensor for Bluetooth communication status."""

    _attr_name = "Bluetooth Status"
    _attr_icon = "mdi:bluetooth"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self._entry.entry_id}_bluetooth_status"

    @property
    def native_value(self) -> str | None:
        """Return the status."""
        return self.coordinator.data.get("communications", {}).get("bluetooth", {}).get("state")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        bluetooth = self.coordinator.data.get("communications", {}).get("bluetooth", {})
        return {
            "message": bluetooth.get("message"),
        }


class WTHEthernetStatusSensor(WTHBaseSensor):
    """Sensor for Ethernet communication status."""

    _attr_name = "Ethernet Status"
    _attr_icon = "mdi:ethernet"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self._entry.entry_id}_ethernet_status"

    @property
    def native_value(self) -> str | None:
        """Return the status."""
        return self.coordinator.data.get("communications", {}).get("ethernet", {}).get("state")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        ethernet = self.coordinator.data.get("communications", {}).get("ethernet", {})
        return {
            "message": ethernet.get("message"),
            "mac_address": ethernet.get("macAddress"),
            "ip_address": ethernet.get("ipAddress"),
            "subnet_mask": ethernet.get("subnetMask"),
            "gateway_address": ethernet.get("gatewayAddress"),
            "dns_address": ethernet.get("dnsAddress"),
        }


class WTHFanlinkDeviceSensor(WTHBaseSensor):
    """Sensor for a Fanlink device."""

    def __init__(self, coordinator: WTHCoordinator, entry: ConfigEntry, index: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._communication = "fanlink"
        self._index = index
        self._attr_name = f"Fanlink Device {index + 1}"
        self._attr_icon = "mdi:devices"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self._entry.entry_id}_fanlink_device_{self._index}"

    @property
    def native_value(self) -> str | None:
        """Return the device type."""
        devices = get_communication_devices(
            self.coordinator.data, self._communication
        )
        device = _get_indexed_item(devices, self._index)
        if device is None:
            return None

        device_type = device.get("type", "")
        return device_type if device_type else "Not configured"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        devices = get_communication_devices(
            self.coordinator.data, self._communication
        )
        device = _get_indexed_item(devices, self._index)
        if device is None:
            return {}

        return {
            "serial_number": device.get("serialNumber"),
            "last_seen": device.get("lastSeen"),
            "last_learn": device.get("lastLearn"),
        }


class WTHCommunicationDeviceSensor(WTHBaseSensor):
    """Sensor for a device on a communication interface."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: WTHCoordinator,
        entry: ConfigEntry,
        communication: str,
        index: int,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._communication = communication
        self._index = index
        self._attr_name = f"{communication.title()} Device {index + 1}"
        self._attr_icon = "mdi:devices"

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self._entry.entry_id}_{self._communication}_device_{self._index}"

    @property
    def native_value(self) -> str | None:
        """Return the device type."""
        devices = get_communication_devices(
            self.coordinator.data, self._communication
        )
        device = _get_indexed_item(devices, self._index)
        if device is None:
            return None

        device_type = device.get("type", "")
        return device_type if device_type else "Not configured"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        devices = get_communication_devices(
            self.coordinator.data, self._communication
        )
        device = _get_indexed_item(devices, self._index)
        if device is None:
            return {}

        return {
            "serial_number": device.get("serialNumber"),
            "last_seen": device.get("lastSeen"),
            "last_learn": device.get("lastLearn"),
        }
