"""Python Package for controlling Sengled Wifi devices programmatically.

SPDX-License-Identifier: Apache-2.0

API access.

For more details about this api, please refer to the documentation at
https://gitlab.com/cpadil/sengledwifipy
"""
from __future__ import annotations
import json
import logging
import time
from typing import Any, Optional, TYPE_CHECKING
from aiohttp import ClientConnectionError, ClientResponse
import backoff
from yarl import URL
if TYPE_CHECKING:
    from .sengledwifilogin import SengledLogin
    from .sengledwifimqtt import SengledWifiMQTT

from .errors import (
    SengledWifipyConnectionError,
    SengledWifipyLoginCloseRequested,
    SengledWifipyLoginError,
    SengledWifipyTooManyRequestsError
)

from .helpers import catch_all_exceptions, hide_email, valid_login_required

_LOGGER = logging.getLogger(__name__)


class SengledWifiAPI:
    """Class for accessing a specific Sengled device using API.

    Args:
        login (SengledLogin): Successfully logged in SengledLogin
    """
    devices: dict[str, Any] = {}
    def __init__(self, login: SengledLogin):
        """Initialize Sengled Wifi device."""
        self._login = login
        self._session = login.session
   
    @classmethod
    async def _process_response(
        self, response: ClientResponse, login: SengledLogin
    ) -> Optional[ClientResponse]:
        """Process a response from _static_request.

        Args:
            ClientResponse (response): Response from _request

        Returns:
            None | ClientResponse: Response from server
        """
        login.stats["api_calls"] += 1
        if response.status == 401:
            login.status["login_successful"] = False
            raise SengledWifipyLoginError(response.reason)
        if response.status == 429:
            raise SengledWifipyTooManyRequestsError(response.reason)
        if response.status >= 400:
            _LOGGER.debug(f"SengledWifiApi: API Returning None due to status: {response.status}")
            return None
        return response
    
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
        data: Optional[dict[str, str]] = None,
        query: Optional[dict[str, str]] = None,
    ) -> ClientResponse:

        session = login.session
        url: URL = URL(login.urls["appserver"] + uri).update_query( query )

        response = await getattr(session, method)(
            url,
            json=data,
            headers=login._headers,
            ssl=login._ssl,
        )
        
        _LOGGER.debug(f"SengledWifiApi: API {hide_email(login.email)}: static {response.request_info.method}: {response.request_info.url} returned {response.status}:{response.reason}:{response.content_type}")
        return await SengledWifiAPI._process_response(response, login)

    @staticmethod
    @catch_all_exceptions
    async def get_devices(
        login: SengledLogin,
        entity_ids: Optional[list[str]] = None
    ) -> Optional[dict[str, Any]]:
        """Retrieve all Sengled Wifi Devices or the specified ones via entity_ids arg.

        Args:
        login (SengledLogin): Successfully logged in SengledLogin
        entity_ids (List[str]): The list of entities you want information about. Optional if all devices information is required. (replaces get_entity_state)

        Returns json

        """
        _LOGGER.debug(f"SengledWifiApi: API  get_devices args {login}")
        response = await SengledWifiAPI._static_request(
            "post", login, "device/list.json", query=None, data={}
        )

        SengledWifiAPI.devices[login.email] = (
            [item for item in (await response.json(content_type=None))["deviceList"] if (item["category"] == "wifielement" and (entity_ids == None or item["deviceUuid"] in entity_ids)) ]
            if response
            else SengledWifiAPI.devices
        )

        _LOGGER.debug(f"SengledWifiApi: API  get_devices returned {SengledWifiAPI.devices[login.email]}")

        return SengledWifiAPI.devices[login.email]
    
    @staticmethod
    @catch_all_exceptions
    async def set_device_state(
        mqttc: SengledWifiMQTT,
        entity_id: str,
        power_on: bool = None,
        brightness: Optional[int] = None,
        color: Optional[str] = None,
        color_temperature: Optional[int] = None
    ) -> bool:
        """Set state of a device.

        Args:
        mqttc (SengledWifiMQTT): MQTT client
        entity_id (str): Entity ID of The light. 
        power_on (bool): Should the light be on or off.
        brightness (Optional[int]): 0-255 (translated to 0-100) or None to leave as is
        color (Optional[str]): red(0-255):green(0-255):blue(0-255) or None to leave as is
        color_temperature (Optional[int]): in kelvin 2500-6500 (translated to 0-100, color '255:45:41') or None to leave as is

        Returns json
        """
        def convert_color_HA(hacolor):
            sengled_color = str(hacolor)
            for r in ((" ", ""), (",", ":"), ("(", ""), (")", "")):
                sengled_color = sengled_color.replace(*r)
            return sengled_color

        power_on= {
           "value": ("1" if power_on else "0"),
           "name": "switch"
        } if isinstance(power_on, bool) else None
        brightness={
           "value": str(round((brightness / 255) * 100)),
           "name": "brightness"
        } if isinstance(brightness, int) else None
        color={
           "value": convert_color_HA(color),
           "name": "color"
        } if isinstance(color, str) else None
        color_temperature={
           "value": str(round((color_temperature / 6500) * 100)),
           "name": "colorTemperature"
        } if isinstance(color_temperature, int) else None

        color_temp={
           "value": '255:45:41',
           "name": "color"
        } if isinstance(color_temperature, int) else None

        timev= str(int(time.time()) - 1577858400)

        data = [{
            "dn": entity_id,
            "type": option["name"],
            "value": option["value"],
            "time": timev, #seconds since the device is up until now, didn't find a way to know when was the last time so instead this is using the seconds since 2020
        } for option in [power_on, brightness, color,color_temperature,color_temp] if option != None]

        _LOGGER.debug(f"SengledWifiApi: API udate device state : {data}") 

        if mqttc.publish_mqtt(
            f"wifielement/{entity_id}/update",
            json.dumps(data),
            ):
            _LOGGER.debug(f"SengledWifiApi: API udate device state successful") 
            return
        _LOGGER.debug(f"SengledWifiApi: API udate device state error") 



