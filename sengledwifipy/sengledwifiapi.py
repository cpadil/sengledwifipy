"""Python Package for controlling Sengled Wifi devices. SPDX-License-Identifier: Apache-2.0."""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING, Any

import backoff
from aiohttp import ClientConnectionError, ClientResponse
from yarl import URL

from .errors import (
    SengledWifipyConnectionError,
    SengledWifipyTooManyRequestsError,
)

if TYPE_CHECKING:
    from .sengledwifilogin import SengledLogin
    from .sengledwifimqtt import SengledWifiMQTT


from .helpers import (
    catch_all_exceptions,
    hide_email,
    valid_login_required,
)

_LOGGER = logging.getLogger(__name__)


class SengledWifiAPI:
    """Uses SengledWifiMqtt and SengledLogin to get information of the devices and set their state.

    Attributes:
        login (SengledLogin):  SengledLogin object
    """

    devices: dict[str, Any] = {}
    """Class attribute. Saves the devices registered in the related Sengled account."""

    def __init__(self, login: SengledLogin) -> None:
        """Initialize Sengled Wifi device."""
        self._login = login

    @staticmethod
    @backoff.on_exception(
        backoff.expo,
        (SengledWifipyTooManyRequestsError, SengledWifipyConnectionError, ClientConnectionError),
        max_time=60,
        max_tries=5,
        logger=__name__,
    )
    @valid_login_required
    async def _static_request(
        method: str,
        login: SengledLogin,
        uri: str,
        data: dict[str, str] = None,
        query: dict[str, str] = None,
    ) -> ClientResponse:
        """Call an API.

        Args:
            login (SengledLogin): needs a valid login
            uri (str): will use the appserver endpoint with this uri
            data (dict[str, str]): payload
            query (dict[str, str]): query parameters

        Returns:
            None or aiohttp ClientResponse
        """
        url = URL(login.urls["appserver"] + uri).update_query(query)

        response = await getattr(login.session, method)(url, json=data)

        _LOGGER.debug(f"SengledWifiApi: API {hide_email(login.email)}: \
                      \n--static {response.request_info.method}: {response.request_info.url} \
                      \n--returned {response.status}:{response.reason}:{response.content_type}")

        return response

    @staticmethod
    @catch_all_exceptions
    async def get_devices(
        login: SengledLogin,
        entity_ids: list[str] = None,
    ) -> dict[str, str | int | bool]:
        """Retrieve all Sengled Wifi Devices or the specified ones via entity_ids arg.

        Args:
            login (SengledLogin): Successfully logged in SengledLogin
            entity_ids (List[str]): The list of entities you want information about. \
                Optional if all devices information is required. (replaces get_entity_state)

        Returns:
            Json. Device information.
        """
        response = await SengledWifiAPI._static_request(
            "post",
            login,
            "device/list.json",
        )

        SengledWifiAPI.devices[login.email] = (
            [
                item
                for item in (await response.json(content_type=None))["deviceList"]
                if (item["category"] == "wifielement" and (entity_ids is None or item["deviceUuid"] in entity_ids))
            ]
            if response
            else SengledWifiAPI.devices
        )

        _LOGGER.debug(f"SengledWifiApi: API get_devices returned {SengledWifiAPI.devices[login.email]}")

        return SengledWifiAPI.devices[login.email]

    @staticmethod
    @catch_all_exceptions
    async def set_device_state(
        mqttc: SengledWifiMQTT,
        entity_id: str,
        power_on: bool = None,
        brightness: int = None,
        color: str = None,
        color_temperature: int = None,
    ) -> bool:
        """Set state of a device.

        Args:
            mqttc (SengledWifiMQTT): MQTT client
            entity_id (str): Entity ID of The light.
            power_on (bool): Should the light be on or off.
            brightness (Optional[int]): 0-255 (translated to 0-100) or None to leave as is
            color (Optional[str]): red(0-255):green(0-255):blue(0-255) or None to leave as is
            color_temperature (Optional[int]): in kelvin 2500-6500 (translated to 0-100, color '255:45:41') or None to leave as is

        Returns:
            Bool. True if the publish was successful, False otherwise.
        """

        def convert_color_HA(hacolor):
            sengled_color = str(hacolor)
            for r in ((" ", ""), (",", ":"), ("(", ""), (")", "")):
                sengled_color = sengled_color.replace(*r)
            return sengled_color

        power_on = (
            {
                "value": ("1" if power_on else "0"),
                "name": "switch",
            }
            if isinstance(power_on, bool)
            else None
        )
        brightness = (
            {
                "value": str(round((brightness / 255) * 100)),
                "name": "brightness",
            }
            if isinstance(brightness, int)
            else None
        )
        color = (
            {
                "value": convert_color_HA(color),
                "name": "color",
            }
            if isinstance(color, str)
            else None
        )
        color_temperature = (
            {
                "value": str(round((color_temperature / 6500) * 100)),
                "name": "colorTemperature",
            }
            if isinstance(color_temperature, int)
            else None
        )

        color_temp = (
            {
                "value": "255:45:41",
                "name": "color",
            }
            if isinstance(color_temperature, int)
            else None
        )

        timev = str(int(time.time()) - 1577858400)

        data = [
            {
                "dn": entity_id,
                "type": option["name"],
                "value": option["value"],
                "time": timev,  # seconds since the device is up until now
            }
            for option in [power_on, brightness, color, color_temperature, color_temp]
            if option is not None
        ]

        _LOGGER.debug(f"SengledWifiApi: API update device state : {data}")

        if mqttc.publish_mqtt(
            f"wifielement/{entity_id}/update",
            json.dumps(data),
        ):
            _LOGGER.debug("SengledWifiApi: API update device state successful")
            return True
        _LOGGER.debug("SengledWifiApi: API update device state error")
