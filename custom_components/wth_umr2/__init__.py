"""The WTH UMR2 Regulator integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.const import ATTR_DEVICE_ID, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr

from .config_flow import host_url_value
from .const import DOMAIN
from .coordinator import STATUS_PATHS as STATUS_PATHS
from .coordinator import VALVE_MODES, WTHConfigEntry, WTHCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
SERVICE_SET_VALVE_MODE = "set_valve_mode"


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the WTH UMR2 component."""
    # HA 2026.3+ handles brand logos automatically via /api/brands/integration/
    # No need for custom logo serving.
    async def handle_set_valve_mode(call: ServiceCall) -> None:
        """Set a valve mode for the selected WTH UMR2 device."""
        device_id = call.data.get(ATTR_DEVICE_ID)
        if not device_id:
            raise HomeAssistantError("A WTH UMR2 device must be selected")

        device = dr.async_get(hass).async_get(device_id)
        if device is None:
            raise HomeAssistantError("WTH UMR2 device was not found")

        entries = [
            hass.config_entries.async_get_entry(entry_id)
            for entry_id in device.config_entries
        ]
        entries = [
            entry for entry in entries if entry is not None and entry.domain == DOMAIN
        ]
        if len(entries) != 1:
            raise HomeAssistantError("WTH UMR2 device configuration is ambiguous")

        await entries[0].runtime_data.async_set_valve_mode(
            call.data["valve_index"],
            call.data["mode"],
        )

    if not hass.services.has_service(DOMAIN, SERVICE_SET_VALVE_MODE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_VALVE_MODE,
            handle_set_valve_mode,
            schema=vol.Schema(
                {
                    vol.Required("valve_index"): vol.All(
                        vol.Coerce(int), vol.Range(min=0, max=9)
                    ),
                    vol.Required("mode"): vol.In(sorted(VALVE_MODES)),
                }
            ),
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: WTHConfigEntry) -> bool:
    """Set up WTH UMR2 from a config entry."""
    coordinator = WTHCoordinator(hass, entry)

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        await coordinator.async_shutdown()
        raise

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        manufacturer="WTH",
        model="UMR2",
        name="WTH UMR2 Regulator",
        sw_version=coordinator.data.get("version", {}).get("fw", "Unknown"),
        hw_version=coordinator.data.get("version", {}).get("hw", "Unknown"),
        configuration_url=f"http://{host_url_value(coordinator.host)}",
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: WTHConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_shutdown()
    return unload_ok
