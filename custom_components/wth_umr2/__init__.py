"""The WTH UMR2 Regulator integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from aiohttp import ClientError
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]
SCAN_INTERVAL = timedelta(seconds=30)
REQUEST_TIMEOUT = 10
STATUS_SECTIONS = (
    "version",
    "main",
    "inputs",
    "process",
    "outputs",
    "communications",
)

type WTHConfigEntry = ConfigEntry[WTHCoordinator]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the WTH UMR2 component."""
    # HA 2026.3+ handles brand logos automatically via /api/brands/integration/
    # No need for custom logo serving
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
    
    # Register device in device registry
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


async def async_reload_entry(hass: HomeAssistant, entry: WTHConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


class WTHCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching WTH UMR2 data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        self.host: str = entry.data["host"]
        self._session = async_get_clientsession(hass)
        self._entry = entry
        
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=SCAN_INTERVAL,
            always_update=False,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch each status section separately and combine the responses."""
        status: dict[str, Any] = {}

        for section in STATUS_SECTIONS:
            status[section] = await self._async_fetch_status_section(section)

        return status

    async def _async_fetch_status_section(self, section: str) -> dict[str, Any]:
        """Fetch and validate one status section from the device."""
        url = f"http://{self.host}/get.json?f=$.status.{section}.*"

        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                async with self._session.get(url) as response:
                    if response.status != 200:
                        raise UpdateFailed(
                            f"Error fetching {section} from {self.host}: "
                            f"HTTP {response.status}"
                        )

                    data = await response.json()

            if not isinstance(data, dict):
                raise UpdateFailed(
                    f"Invalid {section} response from {self.host}: expected object"
                )

            warning = data.get("warning")
            if warning:
                _LOGGER.warning(
                    "WTH UMR2 at %s returned a warning for %s: %s",
                    self.host,
                    section,
                    warning,
                )

            response_status = data.get("status")
            if not isinstance(response_status, dict):
                raise UpdateFailed(
                    f"Invalid {section} response from {self.host}: "
                    "missing status object"
                )

            section_data = response_status.get(section)
            if not isinstance(section_data, dict) or not section_data:
                raise UpdateFailed(
                    f"Invalid {section} response from {self.host}: "
                    f"missing or empty status.{section} object"
                )

            return section_data

        except TimeoutError as err:
            raise UpdateFailed(
                f"Timeout fetching {section} from {self.host}"
            ) from err
        except ClientError as err:
            raise UpdateFailed(
                f"Error communicating with {self.host} while fetching {section}: {err}"
            ) from err
        except ValueError as err:
            raise UpdateFailed(
                f"Invalid JSON while fetching {section} from {self.host}"
            ) from err
    
    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        await super().async_shutdown()


