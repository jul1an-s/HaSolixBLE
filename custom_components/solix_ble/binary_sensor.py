"""Binary sensor platform."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from SolixBLE import Solarbank2, SolixBLEDevice

_LOGGER = logging.getLogger(__name__)


if TYPE_CHECKING:
    from . import SolixBLEConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: SolixBLEConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensors."""

    device = config_entry.runtime_data
    binary_sensors: list[SolixBinarySensorEntity] = []

    # Heater status
    if type(device) in [Solarbank2]:
        binary_sensors.append(
            SolixBinarySensorEntity(
                device,
                "Battery Heating",
                "battery_heating",
                BinarySensorDeviceClass.RUNNING,
                "mdi:radiator",
                "mdi:radiator-disabled",
            )
        )

    async_add_entities(binary_sensors)


class SolixBinarySensorEntity(BinarySensorEntity):
    """Representation of a device."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(
        self,
        device: SolixBLEDevice,
        name: str,
        attribute: str,
        device_class: BinarySensorDeviceClass | None = None,
        icon: str | None = None,
        icon_off: str | None = None,
    ) -> None:
        """Initialize the device object. Does not connect.

        :param device: The device API object.
        :param name: Name of the binary sensor entity.
        :param attribute: Name of the boolean attribute in the API object.
        :param device_class: Device class of the binary sensor entity.
        :param icon: Icon to use instead of the device class default.
        :param icon_off: Icon to use when off. Defaults to the on icon.
        """

        self._attribute_name = attribute

        self._device = device
        self._address = device.address
        self._attr_name = name
        self._attr_unique_id = f"{device.address}_{attribute}"
        self._attr_device_class = device_class
        self._icon_on = icon
        self._icon_off = icon_off or icon
        self._attr_device_info = DeviceInfo(
            name=device.name,
            connections={(CONNECTION_BLUETOOTH, device.address)},
        )
        self._update_updatable_attributes()

    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to HA."""
        self._device.add_callback(self._state_change_callback)

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from HA."""
        self._device.remove_callback(self._state_change_callback)

    def _update_updatable_attributes(self) -> None:
        """Update this entities updatable attrs from the devices state."""
        self._attr_available = self._device.available
        self._attr_is_on = getattr(self._device, self._attribute_name)

        # An unknown state shows the off icon
        self._attr_icon = self._icon_on if self._attr_is_on else self._icon_off

    def _state_change_callback(self) -> None:
        """Run when device informs of state update. Updates local properties."""
        _LOGGER.debug("Received state notification from device %s", self.name)
        self._update_updatable_attributes()
        self.async_write_ha_state()
