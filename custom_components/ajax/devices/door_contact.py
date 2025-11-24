"""Door/Window contact sensor handler for Ajax DoorProtect series.

Handles:
- DoorProtect
- DoorProtect Plus (with tilt sensor and temperature)
- Wired input modules with door contacts
"""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfTemperature,
)

from .base import AjaxDeviceHandler


class DoorContactHandler(AjaxDeviceHandler):
    """Handler for Ajax DoorProtect door/window contact sensors."""

    def get_binary_sensors(self) -> list[dict]:
        """Return binary sensor entities for door contacts."""
        sensors = []

        # Main door sensor - always create it even if attribute doesn't exist yet
        # The attribute will be populated by SQS notifications
        sensors.append(
            {
                "key": "door",
                "translation_key": "door",
                "device_class": BinarySensorDeviceClass.DOOR,
                "value_fn": lambda: self.device.attributes.get("door_opened", False),
                "enabled_by_default": True,
            }
        )

        # External contact (for connecting wired sensors)
        # Only create if the device has this capability
        if "external_contact_opened" in self.device.attributes:
            sensors.append(
                {
                    "key": "external_contact",
                    "translation_key": "external_contact",
                    "device_class": BinarySensorDeviceClass.DOOR,
                    "value_fn": lambda: self.device.attributes.get("external_contact_opened", False),
                    "enabled_by_default": True,
                }
            )

        # Always active mode
        sensors.append(
            {
                "key": "always_active",
                "translation_key": "always_active",
                "icon": "mdi:moon-waning-crescent",
                "value_fn": lambda: self.device.attributes.get("always_active", False),
                "enabled_by_default": True,
            }
        )

        # Armed in night mode
        sensors.append(
            {
                "key": "armed_in_night_mode",
                "translation_key": "armed_in_night_mode",
                "icon": "mdi:shield-moon",
                "value_fn": lambda: self.device.attributes.get("armed_in_night_mode", False),
                "enabled_by_default": True,
            }
        )

        # Tamper / Couvercle - inverted: False = closed (OK), True = open (problem)
        sensors.append(
            {
                "key": "tamper",
                "translation_key": "tamper",
                "device_class": BinarySensorDeviceClass.TAMPER,
                "value_fn": lambda: self.device.attributes.get("tampered", False),
                "enabled_by_default": True,
            }
        )

        # Tilt sensor / Capteur d'inclinaison (DoorProtect Plus)
        if "tilt_detected" in self.device.attributes or "tilt" in self.device.attributes:
            sensors.append(
                {
                    "key": "tilt",
                    "translation_key": "tilt",
                    "device_class": BinarySensorDeviceClass.MOVING,
                    "icon": "mdi:angle-acute",
                    "value_fn": lambda: self.device.attributes.get("tilt_detected", self.device.attributes.get("tilt", False)),
                    "enabled_by_default": True,
                }
            )

        # Shock sensor / Capteur de choc (DoorProtect Plus)
        if "shock_detected" in self.device.attributes or "shock" in self.device.attributes:
            sensors.append(
                {
                    "key": "shock",
                    "translation_key": "shock",
                    "device_class": BinarySensorDeviceClass.VIBRATION,
                    "icon": "mdi:vibrate",
                    "value_fn": lambda: self.device.attributes.get("shock_detected", self.device.attributes.get("shock", False)),
                    "enabled_by_default": True,
                }
            )

        return sensors

    def get_sensors(self) -> list[dict]:
        """Return sensor entities for door contacts."""
        sensors = []

        # Battery level - always create even if None, will be updated by notifications
        sensors.append(
            {
                "key": "battery",
                "translation_key": "battery",
                "device_class": SensorDeviceClass.BATTERY,
                "native_unit_of_measurement": PERCENTAGE,
                "state_class": SensorStateClass.MEASUREMENT,
                "value_fn": lambda: self.device.battery_level if self.device.battery_level is not None else None,
                "enabled_by_default": True,
            }
        )

        # Signal strength - always create even if None, will be updated by notifications
        sensors.append(
            {
                "key": "signal_strength",
                "translation_key": "signal_strength",
                "device_class": SensorDeviceClass.SIGNAL_STRENGTH,
                "native_unit_of_measurement": SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
                "state_class": SensorStateClass.MEASUREMENT,
                "value_fn": lambda: self.device.signal_strength if self.device.signal_strength is not None else None,
                "enabled_by_default": True,
            }
        )

        # Temperature (DoorProtect Plus)
        if "temperature" in self.device.attributes:
            sensors.append(
                {
                    "key": "temperature",
                    "translation_key": "temperature",
                    "device_class": SensorDeviceClass.TEMPERATURE,
                    "native_unit_of_measurement": UnitOfTemperature.CELSIUS,
                    "state_class": SensorStateClass.MEASUREMENT,
                    "value_fn": lambda: self.device.attributes.get("temperature"),
                    "enabled_by_default": True,
                }
            )

        # Firmware version - enable by default and also add hardware version
        if self.device.firmware_version is not None:
            sensors.append(
                {
                    "key": "firmware_version",
                    "translation_key": "firmware_version",
                    "icon": "mdi:chip",
                    "value_fn": lambda: self.device.firmware_version,
                    "enabled_by_default": True,
                }
            )

        # Hardware version
        if self.device.hardware_version is not None:
            sensors.append(
                {
                    "key": "hardware_version",
                    "translation_key": "hardware_version",
                    "icon": "mdi:chip",
                    "value_fn": lambda: self.device.hardware_version,
                    "enabled_by_default": True,
                }
            )

        # Connection type / Connexion via Jeweller
        if "connection_type" in self.device.attributes:
            sensors.append(
                {
                    "key": "connection_type",
                    "translation_key": "connection_type",
                    "icon": "mdi:wifi",
                    "value_fn": lambda: self.device.attributes.get("connection_type"),
                    "enabled_by_default": True,
                }
            )

        # Operating mode / Mode de fonctionnement
        if "operating_mode" in self.device.attributes:
            sensors.append(
                {
                    "key": "operating_mode",
                    "translation_key": "operating_mode",
                    "icon": "mdi:cog",
                    "value_fn": lambda: self.device.attributes.get("operating_mode"),
                    "enabled_by_default": True,
                }
            )

        # Battery state / État de la batterie (normal/faible/critique)
        if self.device.battery_state is not None:
            sensors.append(
                {
                    "key": "battery_state",
                    "translation_key": "battery_state",
                    "icon": "mdi:battery-heart-variant",
                    "value_fn": lambda: self.device.battery_state,
                    "enabled_by_default": True,
                }
            )

        return sensors
