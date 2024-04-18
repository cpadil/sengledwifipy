"""Python Package for controlling Sengled Wifi devices. SPDX-License-Identifier: Apache-2.0"""

from __future__ import annotations
import logging
import json

import asyncio
from yarl import URL
from typing import Callable, Any, Optional, Iterable, TYPE_CHECKING
from collections.abc import Coroutine
from paho.mqtt import client as mqtt, enums as mqttenums

from .helpers import valid_login_required

if TYPE_CHECKING:
    from .sengledwifilogin import SengledLogin

_LOGGER = logging.getLogger(__name__)


class SengledWifiMQTT:
    """Connect to Sengled MQTT broker, subscribe to topics and publish updates. Uses paho-mqtt package.

    Attributes:
        _login (SengledLogin): SengledLogin object
        _session (SengledLogin session): SengledLogin session attribute
        _jsession_id (SengledLogin session JSESSIONID): value of cookie JSESSIONID saved in SengledLogin session
        _headers (dict[str, str]): same headers used in Android app
        _clientid (str): used during the creation of the mqtt client f"{_jsession_id}@lifeApp"
        mqtt_server (URL): url is obtained during the login and fetched from SengledLogin object
        mqtt_client (paho.mqtt.client): initialization of paho.mqtt client
        _status (bool): to indicate if mqtt connection is active
        devices (list[dict[str, str]]): list of Sengled devices, used to create the topic strings and subscribe, \
            during the initialization is set to None
        open_callback (Callable): an async function to call within the on_connect callback
        msg_callback (Callable): an async function to call within the on_message callback
        close_callback (Callable): an async function to call within the on_disconnect callback
        error_callback (Callable): an async function to call within the on_error callback
        _loop (asyncio.AbstractEventLoop): used for callbacks
    """

    def __init__(
        self,
        login: SengledLogin,
        msg_callback: Optional[Callable[[], Coroutine[Any, Any, None]]] = None,
        open_callback: Optional[Callable[[], Coroutine[Any, Any, None]]] = None,
        close_callback: Optional[Callable[[], Coroutine[Any, Any, None]]] = None,
        error_callback: Optional[Callable[[], Coroutine[Any, Any, None]]] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        """Initialization of SengledWifiMQTT class, requires a valid SengledLogin object.

        Args:
            login (SengledLogin): Defines if instance exhibits this preference.
            msg_callback (Optional[Callable]): callback function when new messages arrive.
            open_callback (Optional[Callable]): callback function when connection is opened.
            close_callback (Optional[Callable]): callback function when when the connection is closed.
            error_callback (Optional[Callable]): callback function when there is an error.
            loop: (Optional[asyncio.AbstractEventLoop]).
        """
        self._login = login
        self._session = login.session
        self._jsession_id = self._session.cookie_jar.filter_cookies("https://sengled.com")["JSESSIONID"].value
        self._headers = {
            "Cookie": f"JSESSIONID={self._jsession_id}",
            "X-Requested-With": "com.sengled.life2",
        }
        self._clientid = f"{self._jsession_id}@lifeApp"
        self.mqtt_server = URL(login.urls["mqtt"])
        self.mqtt_client: mqtt.Client = None
        self._status: bool = False
        self.devices: Iterable = None
        self.open_callback: Callable[[], Coroutine[Any, Any, None]] = open_callback
        self.msg_callback: Callable[[], Coroutine[Any, Any, None]] = msg_callback
        self.close_callback: Callable[[], Coroutine[Any, Any, None]] = close_callback
        self.error_callback: Callable[[str], Coroutine[Any, Any, None]] = error_callback
        self._loop: asyncio.AbstractEventLoop = loop if loop else asyncio.get_event_loop()
        self.mqtt_client = mqtt.Client(
            callback_api_version=mqttenums.CallbackAPIVersion.VERSION2,
            client_id=self._clientid,
            transport="websockets",
        )
        self.mqtt_client.tls_set_context()
        self.mqtt_client.ws_set_options(
            path=self.mqtt_server.path,
            headers=self._headers,
        )
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_disconnect = self.on_disconnect
        self.mqtt_client.on_subscribe = self.on_subscribe
        self.mqtt_client.on_log = self.on_log

    @valid_login_required
    async def async_connect(self, devices: Iterable = None) -> None:
        """Initialize MQTT connection async.

        Args:
            devices: list of Sengled devices, used to create the topic strings and subscribe

        Returns:
            None
        """
        _LOGGER.debug(f"SengledWifiApi: MQTT Initialize the connection, {self.mqtt_server.host}, {self.mqtt_server.port}")
        self.devices = devices

        self.mqtt_client.connect_async(
            self.mqtt_server.host,
            port=self.mqtt_server.port,
            keepalive=60,
        )
        self.mqtt_client.loop_start()

    def on_connect(self, mqttc, userdata, flags, rc, properties) -> None:
        """Callback. Called when the broker responds to our connection request. Calls the async function open_callback defined. \
            Uses devices input argument to subscribe if connection is successful.

        Args:
            mqttc (Client): the client instance for this callback
            userdata: the private user data as set in Client() or user_data_set()
            flags (ConnectFlags): the flags for this connection
            rc (ReasonCode): the connection reason code received from the broken. \
                In MQTT v5.0 it is the reason code defined by the standard.
            properties (Properties): the MQTT v5.0 properties received from the broker. 

        Returns:
            None
        """
        if rc == 0:
            _LOGGER.debug(f"SengledWifiApi: MQTT open connection result: {rc}")

            topics = [("wifielement/" + device["deviceUuid"] + "/status", 2) for device in self.devices]
            self.mqtt_client.subscribe(topics)
            self._status = True
            if self.open_callback:
                asyncio.run_coroutine_threadsafe(self.open_callback(), self._loop)
            return
        _LOGGER.debug(f"SengledWifiApi: MQTT open connection error: {rc} ")

    def on_message(self, mqttc, userdata, msg) -> None:
        """Callback. Called when a message has been received from mqtt broker. \
            Parses the message and then calls the async function msg_callback defined.

        Args:
            mqttc (Client): the client instance for this callback
            userdata: the private user data as set in Client() or user_data_set()
            msg (MQTTMessage): the received message. This is a class with members topic, payload, qos, retain.

        Returns:
            None
        """
        _LOGGER.debug(f"SengledWifiApi: MQTT Message received: \
                      \n{msg.dup}, {msg.info}, {msg.mid}, {msg.payload}, \
                      \n{msg.properties}, {msg.qos}, {msg.retain}, {msg.state}, {msg.timestamp}....")

        if msg.topic.split("/")[0] != "wifielement":
            _LOGGER.debug("SengledWifiApi: MQTT Message unexpected topic")
            return

        device = dict(id=msg.topic.split("/")[1], time=json.loads(msg.payload.decode("utf-8"))[0]["time"], attributes=dict())

        for attrs in json.loads(msg.payload.decode("utf-8")):
            device["attributes"][attrs["type"]] = attrs["value"]

        _LOGGER.debug(f"SengledWifiApi: MQTT Message parsed: {device}")

        if self.msg_callback:
            asyncio.run_coroutine_threadsafe(self.msg_callback(), self._loop)

    def on_subscribe(self, mqttc, userdata, mid, rc_list, properties):
        """Callback. Called when the broker responds to a subscription request. 

        Args:
            mqttc (Client): the client instance for this callback
            userdata: the private user data as set in Client() or user_data_set()
            mid (int): matches the mid variable returned from the corresponding subscribe() call.
            rc_list (list[ReasonCode]): reason codes received from the broker for each subscription. \
                In MQTT v5.0 it is the reason code defined by the standard. 
            properties (Properties): the MQTT v5.0 properties received from the broker. 

        Returns:
            None
        """
        _LOGGER.debug(f"SengledWifiApi: MQTT subscribe result: {mid}")

    def on_log(self, mqttc, userdata, level, buf):
        """Callback. Called when the client has log information. Only used when the logger is set to debug. 

        Args:
            mqttc (Client): the client instance for this callback
            userdata: the private user data as set in Client() or user_data_set()
            level (int): gives the severity of the message and will be one of \
                MQTT_LOG_INFO, MQTT_LOG_NOTICE, MQTT_LOG_WARNING, MQTT_LOG_ERR, and MQTT_LOG_DEBUG.
            buf (str): the message itself

        Returns:
            None
        """
        _LOGGER.debug(f"SengledWifiApi: MQTT log received: {buf}")
        self._status = False

    def on_disconnect(self, mqttc, userdata, flags, rc, properties):
        """Callback. Called when there is an issue with the connection to the mqtt broker.

        Args:
            mqttc (Client): the client instance for this callback
            userdata: the private user data as set in Client() or user_data_set()
            flags (ConnectFlags): the flags for this connection
            rc (ReasonCode): the connection reason code received from the broken. \
                In MQTT v5.0 it’s the reason code defined by the standard.
            properties (Properties): the MQTT v5.0 properties received from the broker. 

        Returns:
            None
        """
        _LOGGER.debug(f"SengledWifiApi: MQTT disconnected: {rc}")
        self._status = False

    def sync_connect(self) -> None:
        """An alternative connection method to connect without asyncio."""
        self.mqtt_client.connect(
            self.mqtt_server.host,
            port=self.mqtt_server.port,
            keepalive=60,
        )

    def publish_mqtt(self, topic: str, payload: str) -> bool:
        """Publish an MQTT message.

        Args:
            topic (str): topic to publish the message on
            payload (str): message to send as string in json format
        Returns:
            True if publish was successful or False if there was an issue
        """

        if not self.mqtt_client.is_connected():
            _LOGGER.debug("SengledWifiApi: MQTT Publish - not connected, trying to connect and publish")
            self.sync_connect()
            self.mqtt_client.loop_start()

        r = self.mqtt_client.publish(topic, payload=payload, qos=0)
        _LOGGER.debug(f"SengledWifiApi: MQTT Publish message {r.rc}")
        try:
            r.wait_for_publish()
            return r.is_published()
        except ValueError:
            pass

        return False

    def subscribe_mqtt(self, topic: tuple[str, str] | list[tuple[str, str]], callback: Callable[[]] = None) -> bool:
        """Subscribe to an MQTT topic.

        Args:
            topic (str): topic to subscribe to
            callback -- callback to call when a message comes in
        Returns:
            bool
        """
        if not self.mqtt_client.is_connected():
            _LOGGER.debug("SengledWifiApi: MQTT Subscribe - not connected, trying to connect and subscribe")
            self.sync_connect()

        r = self.mqtt_client.subscribe(topic)

        _LOGGER.debug("SengledWifiApi: MQTT Subscribe to an topic")
        if r[0] != mqtt.MQTT_ERR_SUCCESS:
            return False

        self.mqtt_client.message_callback_add(topic, callback)
        self.mqtt_client.loop_forever()
        return True
