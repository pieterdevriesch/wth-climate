"""Base entity for the WTH UMR2 integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WTHCoordinator


class WTHBaseEntity(CoordinatorEntity[WTHCoordinator]):
    """Base entity shared by WTH UMR2 platforms."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: WTHCoordinator, entry: ConfigEntry) -> None:
        """Initialize the entity."""
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
