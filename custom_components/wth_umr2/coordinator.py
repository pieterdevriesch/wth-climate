"""Data coordinator for the WTH UMR2 regulator."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from aiohttp import ClientError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .communication import COMMUNICATION_PATHS
from .config_flow import host_url_value
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)
REQUEST_TIMEOUT = 10
STATUS_PATHS: tuple[tuple[str, ...], ...] = (
    ("version",),
    ("main",),
    ("inputs",),
    ("process",),
    ("outputs",),
    *COMMUNICATION_PATHS,
)
OPTIONAL_STATUS_PATHS = frozenset(COMMUNICATION_PATHS)


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
        """Fetch each status path separately and combine the responses."""
        status: dict[str, Any] = {}

        for path in STATUS_PATHS:
            try:
                section_data = await self._async_fetch_status_path(path)
            except UpdateFailed as err:
                if path not in OPTIONAL_STATUS_PATHS:
                    raise

                _LOGGER.warning(
                    "Optional WTH UMR2 section %s is unavailable: %s",
                    ".".join(path),
                    err,
                )
                section_data = {}

            target = status
            for key in path[:-1]:
                target = target.setdefault(key, {})
            target[path[-1]] = section_data

        return status

    async def _async_fetch_status_path(self, path: tuple[str, ...]) -> dict[str, Any]:
        """Fetch and validate one status path from the device."""
        path_text = ".".join(path)
        url = (
            f"http://{host_url_value(self.host)}/get.json"
            f"?f=$.status.{path_text}.*"
        )

        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                async with self._session.get(url) as response:
                    if response.status != 200:
                        raise UpdateFailed(
                            f"Error fetching {path_text} from {self.host}: "
                            f"HTTP {response.status}"
                        )

                    data = await response.json()

            if not isinstance(data, dict):
                raise UpdateFailed(
                    f"Invalid {path_text} response from {self.host}: expected object"
                )

            warning = data.get("warning")
            if warning:
                _LOGGER.warning(
                    "WTH UMR2 at %s returned a warning for %s: %s",
                    self.host,
                    path_text,
                    warning,
                )

            response_status = data.get("status")
            if not isinstance(response_status, dict):
                raise UpdateFailed(
                    f"Invalid {path_text} response from {self.host}: "
                    "missing status object"
                )

            section_data: Any = response_status
            for key in path:
                if not isinstance(section_data, dict):
                    section_data = None
                    break
                section_data = section_data.get(key)

            if not isinstance(section_data, dict) or not section_data:
                raise UpdateFailed(
                    f"Invalid {path_text} response from {self.host}: "
                    f"missing or empty status.{path_text} object"
                )

            return section_data

        except TimeoutError as err:
            raise UpdateFailed(
                f"Timeout fetching {path_text} from {self.host}"
            ) from err
        except ClientError as err:
            raise UpdateFailed(
                f"Error communicating with {self.host} while fetching {path_text}: {err}"
            ) from err
        except ValueError as err:
            raise UpdateFailed(
                f"Invalid JSON while fetching {path_text} from {self.host}"
            ) from err


type WTHConfigEntry = ConfigEntry[WTHCoordinator]
