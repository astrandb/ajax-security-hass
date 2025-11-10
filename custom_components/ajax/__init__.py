"""The Ajax Security System integration."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv

from .api import AjaxApi, AjaxApiError, AjaxAuthError
from .const import DOMAIN
from .coordinator import AjaxDataCoordinator

if TYPE_CHECKING:
    from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.ALARM_CONTROL_PANEL,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Ajax Security System component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ajax Security System from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    email = entry.data[CONF_EMAIL]
    password = entry.data[CONF_PASSWORD]
    device_id = entry.entry_id  # Use entry ID as unique device ID

    # Create API instance
    api = AjaxApi(email=email, password=password, device_id=device_id)

    try:
        # Authenticate
        await api.async_login()
        _LOGGER.info("Successfully authenticated with Ajax API")

    except AjaxAuthError as err:
        _LOGGER.error("Authentication failed: %s", err)
        return False
    except AjaxApiError as err:
        _LOGGER.error("API error during setup: %s", err)
        raise ConfigEntryNotReady from err

    # Create coordinator
    coordinator = AjaxDataCoordinator(hass, api)

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    async def async_handle_force_arm(call: ServiceCall) -> None:
        """Handle the force_arm service call."""
        entity_id = call.data.get("entity_id")
        if not entity_id:
            _LOGGER.error("No entity_id provided for force_arm service")
            return

        # Get the alarm control panel entity
        entity_registry = hass.helpers.entity_registry.async_get(hass)
        entity_entry = entity_registry.async_get(entity_id)

        if not entity_entry:
            _LOGGER.error("Entity %s not found", entity_id)
            return

        # Get the space_id from the entity's unique_id
        # Format: {entry_id}_alarm_{space_id}
        unique_id_parts = entity_entry.unique_id.split("_")
        if len(unique_id_parts) < 3 or unique_id_parts[1] != "alarm":
            _LOGGER.error("Invalid entity unique_id format: %s", entity_entry.unique_id)
            return

        space_id = unique_id_parts[2]

        # Call coordinator method with force=True
        try:
            await coordinator.async_arm_space(space_id, force=True)
        except Exception as err:
            _LOGGER.error("Failed to force arm: %s", err)

    async def async_handle_force_arm_night(call: ServiceCall) -> None:
        """Handle the force_arm_night service call."""
        entity_id = call.data.get("entity_id")
        if not entity_id:
            _LOGGER.error("No entity_id provided for force_arm_night service")
            return

        # Get the alarm control panel entity
        entity_registry = hass.helpers.entity_registry.async_get(hass)
        entity_entry = entity_registry.async_get(entity_id)

        if not entity_entry:
            _LOGGER.error("Entity %s not found", entity_id)
            return

        # Get the space_id from the entity's unique_id
        unique_id_parts = entity_entry.unique_id.split("_")
        if len(unique_id_parts) < 3 or unique_id_parts[1] != "alarm":
            _LOGGER.error("Invalid entity unique_id format: %s", entity_entry.unique_id)
            return

        space_id = unique_id_parts[2]

        # Call coordinator method with force=True
        try:
            await coordinator.async_arm_night_mode(space_id, force=True)
        except Exception as err:
            _LOGGER.error("Failed to force arm night mode: %s", err)

    # Register services
    hass.services.async_register(
        DOMAIN,
        "force_arm",
        async_handle_force_arm,
        schema=vol.Schema({
            vol.Required("entity_id"): cv.entity_id,
        }),
    )

    hass.services.async_register(
        DOMAIN,
        "force_arm_night",
        async_handle_force_arm_night,
        schema=vol.Schema({
            vol.Required("entity_id"): cv.entity_id,
        }),
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator: AjaxDataCoordinator = hass.data[DOMAIN].pop(entry.entry_id)

        # Close API connection
        await coordinator.api.close()

        # Unregister services if this is the last config entry
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, "force_arm")
            hass.services.async_remove(DOMAIN, "force_arm_night")

    return unload_ok
