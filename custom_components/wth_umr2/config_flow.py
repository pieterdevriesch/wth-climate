"""Config flow for WTH UMR2 Regulator integration."""
from __future__ import annotations

import asyncio
import ipaddress
import logging
import re
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from aiohttp import ClientError
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
_HOST_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


class InvalidHostError(ValueError):
    """Raised when a configured host is not a valid IP or hostname."""


class InvalidResponseError(ValueError):
    """Raised when the device response is not a supported WTH response."""


class ConnectionTimeoutError(ConnectionError):
    """Raised when the device does not respond before the timeout."""


def normalize_host(value: str) -> str:
    """Normalize and validate an IP address or hostname."""
    host = value.strip()
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]

    try:
        return str(ipaddress.ip_address(host))
    except ValueError:
        pass

    host = host.rstrip(".").casefold()
    if (
        not host
        or len(host) > 253
        or any(character.isspace() for character in host)
        or any(character in host for character in "/?#@:")
        or any(
            not _HOST_LABEL.fullmatch(label) or len(label) > 63
            for label in host.split(".")
        )
    ):
        raise InvalidHostError("Invalid host")

    return host


def host_url_value(host: str) -> str:
    """Return a normalized host formatted for an HTTP URL."""
    return f"[{host}]" if ":" in host else host

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    host = normalize_host(data[CONF_HOST])
    url = f"http://{host_url_value(host)}/get.json?f=$.status.version.*"
    
    session = async_get_clientsession(hass)
    
    try:
        async with asyncio.timeout(10):
            async with session.get(url) as response:
                if response.status != 200:
                    raise ConnectionError(f"HTTP {response.status}")
                
                data = await response.json()
                
                if (
                    not isinstance(data, dict)
                    or not isinstance(data.get("status"), dict)
                    or not isinstance(data["status"].get("version"), dict)
                    or not data["status"]["version"]
                ):
                    raise InvalidResponseError("Invalid response format")
                
                return {
                    "title": f"WTH UMR2 ({host})",
                }
                
    except TimeoutError as err:
        _LOGGER.error("Timeout connecting to WTH UMR2 at %s", host)
        raise ConnectionTimeoutError("Timeout") from err
    except ClientError as err:
        _LOGGER.error("Error connecting to WTH UMR2 at %s: %s", host, err)
        raise ConnectionError(str(err)) from err
    except InvalidResponseError as err:
        _LOGGER.error("Invalid response from WTH UMR2 at %s: %s", host, err)
        raise InvalidResponseError("Invalid response") from err
    except ValueError as err:
        _LOGGER.error("Invalid JSON from WTH UMR2 at %s: %s", host, err)
        raise InvalidResponseError("Invalid response") from err
    except Exception:
        _LOGGER.exception("Unexpected error connecting to WTH UMR2 at %s", host)
        raise


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for WTH UMR2 Regulator."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            try:
                normalized_host = normalize_host(user_input[CONF_HOST])
                normalized_input = {**user_input, CONF_HOST: normalized_host}
                info = await validate_input(self.hass, normalized_input)
            except InvalidHostError:
                errors["base"] = "invalid_host"
            except ConnectionTimeoutError:
                errors["base"] = "timeout"
            except ConnectionError:
                errors["base"] = "cannot_connect"
            except InvalidResponseError:
                errors["base"] = "invalid_response"
            except Exception:
                _LOGGER.exception("Unexpected exception in config flow")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(normalized_host)
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(
                    title=info["title"],
                    data=normalized_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
