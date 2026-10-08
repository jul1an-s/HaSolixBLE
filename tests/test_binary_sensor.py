"""Test binary sensors for SolixBLE integration."""

import asyncio
from typing import Any
from unittest.mock import PropertyMock, patch

import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ICON,
    STATE_OFF,
    STATE_ON,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry
from SolixBLE import SolixBLEDevice

from custom_components.solix_ble.const import DOMAIN

from . import MOCK_SOLAR_BANK_2_DETAILS, MockDeviceDetails


@pytest.mark.parametrize(
    "mock_config_entry,mock_device_details,class_name,attribute,device_class,"
    "icon,icon_off",
    [
        pytest.param(
            MOCK_SOLAR_BANK_2_DETAILS,
            MOCK_SOLAR_BANK_2_DETAILS,
            "Solarbank2",
            "battery_heating",
            BinarySensorDeviceClass.RUNNING,
            "mdi:radiator",
            "mdi:radiator-disabled",
            id="sb2_battery_heating",
        ),
    ],
    indirect=["mock_config_entry"],
)
async def test_binary_sensor_entities(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_device_details: MockDeviceDetails,
    class_name: str,
    attribute: str,
    device_class: BinarySensorDeviceClass,
    icon: str,
    icon_off: str,
) -> None:
    """Test that the entities are added and follow the state of the device."""

    mock_config_entry.add_to_hass(hass)

    captured_self: SolixBLEDevice = None

    def connect_side_effect(
        self: SolixBLEDevice,
    ):
        """We use this to capture the device object so we can run callbacks on it."""
        nonlocal captured_self
        captured_self = self
        return True

    with (
        patch(
            "custom_components.solix_ble.async_ble_device_from_address",
            return_value=mock_device_details.get_ble_device(),
        ),
        patch(
            "custom_components.solix_ble.async_scanner_count",
            return_value=1,
        ),
        patch(
            f"SolixBLE.{class_name}.connect",
            autospec=True,
            side_effect=connect_side_effect,
        ),
        patch(
            f"SolixBLE.{class_name}.connected",
            side_effect=[True],
        ),
        patch(
            f"SolixBLE.{class_name}.negotiated",
            side_effect=[True],
        ),
        patch(
            "SolixBLE.SolixBLEDevice.available",
            side_effect=[True],
        ),
        patch(
            f"SolixBLE.{class_name}.{attribute}",
            new_callable=PropertyMock,
            return_value=None,
        ) as mock_attribute,
    ):

        # Set up the integration
        assert await async_setup_component(hass, DOMAIN, {}) is True
        await hass.async_block_till_done()
        await asyncio.sleep(1)

        # Calculate entity ID
        device_name = mock_config_entry.title.lower().replace(" ", "_")
        entity_id = f"binary_sensor.{device_name}_{attribute}"
        entity = hass.states.get(entity_id)

        assert entity is not None, f"Expected to find an entity at '{entity_id}'!"

        # An unknown value from the device should not be reported as off
        assert entity.state == STATE_UNKNOWN, "Expected initial state to be unknown!"

        assert entity.attributes.get(ATTR_DEVICE_CLASS) == device_class

        # But it does show the off icon
        assert (
            entity.attributes.get(ATTR_ICON) == icon_off
        ), "Expected the off icon while the state is unknown!"

        # The state and the icon should follow the device
        for value, expected_state, expected_icon in (
            (True, STATE_ON, icon),
            (False, STATE_OFF, icon_off),
        ):
            mock_attribute.return_value = value
            captured_self._run_state_changed_callbacks()
            await hass.async_block_till_done()

            entity = hass.states.get(entity_id)

            assert (
                entity.state == expected_state
            ), f"Expected '{expected_state}' when the device reports '{value}'!"

            assert (
                entity.attributes.get(ATTR_ICON) == expected_icon
            ), f"Expected icon '{expected_icon}' when the state is '{entity.state}'!"
