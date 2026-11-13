"""The WTH UMR2 Regulator integration."""
from __future__ import annotations

from typing import Any

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
from .coordinator import STATUS_PATHS as STATUS_PATHS
from .coordinator import WTHConfigEntry, WTHCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the WTH UMR2 component."""
    # HA 2026.3+ handles brand logos automatically via /api/brands/integration/
    # No need for custom logo serving.
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
        configuration_url=f"http://{coordinator.host}",
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: WTHConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
