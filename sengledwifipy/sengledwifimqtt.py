"""Python Package for controlling Sengled Wifi devices programmatically.

SPDX-License-Identifier: Apache-2.0

MQTT actions.

For more details about this api, please refer to the documentation at
https://gitlab.com/cpadil/sengledwifipy
"""
from __future__ import annotations
import logging
import json
import asyncio
from yarl import URL
from typing import Callable, Any, Optional,Iterable, TYPE_CHECKING
from collections.abc import Coroutine
from paho.mqtt import client as mqtt, enums as mqttenums, properties as mqttproperties, packettypes
from .helpers import valid_login_required
if TYPE_CHECKING:
    from .sengledwifilogin import SengledLogin

_LOGGER = logging.getLogger(__name__)


class SengledWifiMQTT:
    """Class for handling mqtt actions. 

    Args:
    login (SengledLogin): Successfully logged in SengledLogin
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
        self._loop: asyncio.AbstractEventLoop = (
            loop if loop else asyncio.get_event_loop()
        )
        self.mqtt_client = mqtt.Client(
            callback_api_version=mqttenums.CallbackAPIVersion.VERSION2
            ,client_id=self._clientid
            ,transport="websockets"
            #not supported yet ,protocol = mqttenums.MQTTProtocolVersion.MQTTv5
        )
        self.mqtt_client.tls_set_context()
        self.mqtt_client.ws_set_options(
            path=self.mqtt_server.path,
            headers=self._headers,
        )
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_disconnect= self.on_disconnect
        self.mqtt_client.on_subscribe= self.on_subscribe
        self.mqtt_client.on_log = self.on_log

    @valid_login_required
    async def async_connect(self, devices: Iterable = None) -> None:
        """Initialize MQTT connection.
        
        Args:
        devices: devices list to map it to the topics required to susubscribe        
        
        """
        _LOGGER.debug(f"SengledWifiApi: MQTT Initialize the connection, {self.mqtt_server.host}, {self.mqtt_server.port}")
        self.devices= devices

        self.mqtt_client.connect_async(
            self.mqtt_server.host,
            port=self.mqtt_server.port,
            keepalive=60,
        )
        self.mqtt_client.loop_start()

    def on_connect(self,  mqttc, userdata, flags, rc, properties) -> None:
        """Called when the broker responds to our connection request.
        
        0: Connection successful
        1: Connection refused - incorrect protocol version
        2: Connection refused - invalid client identifier
        3: Connection refused - server unavailable
        4: Connection refused - bad username or password
        5: Connection refused - not authorised
        6-255: Currently unused.

        """
        if rc == 0:
            _LOGGER.debug(f"SengledWifiApi: MQTT open connection result: {rc}")

            topics = [("wifielement/"+device["deviceUuid"]+"/status",2) for device in self.devices]
            self.mqtt_client.subscribe(topics)
            self._status = True
            if self.open_callback:
                asyncio.run_coroutine_threadsafe(
                    self.open_callback(), self._loop
                )
            return
        _LOGGER.debug(f"SengledWifiApi: MQTT open connection error: {rc}")

    def on_message(self, mqttc, userdata, msg):
        """Called when a message has been received."""
        _LOGGER.debug(f"SengledWifiApi: MQTT Message received: {msg.dup}, {msg.info}, {msg.mid}, {msg.payload}, {msg.properties}, {msg.qos}, {msg.retain}, {msg.state}, {msg.timestamp}....",
            # str(msg.topic),
            # str(msg.payload.decode("utf-8"))
            )
        
        if msg.topic.split("/")[0] != "wifielement":
            _LOGGER.debug("SengledWifiApi: MQTT Message unexpected topic")
            return
        
        device = dict( id = msg.topic.split("/")[1],time = json.loads(msg.payload.decode("utf-8"))[0]["time"], attributes = dict())

        for attrs in json.loads(msg.payload.decode("utf-8")):
            device["attributes"][attrs["type"]] = attrs["value"]

        _LOGGER.debug(f"SengledWifiApi: MQTT Message parsed: {device}")
        
        if self.msg_callback:
            asyncio.run_coroutine_threadsafe(
                self.msg_callback(), self._loop
            )

    def on_subscribe(self, mqttc, userdata, mid, rc_list, properties):
        """Called when the broker responds to a subscribe request."""
        _LOGGER.debug(f"SengledWifiApi: MQTT subscribe result: {mid}")

    def on_log(self,  mqttc, userdata, level, buf):
        """Called when the client receives has log."""
        _LOGGER.debug(f"SengledWifiApi: MQTT log received: {buf}")
        self._status = False
    
    def on_disconnect(self,  mqttc, userdata, flags, rc, properties):
        """Called when the client disconnects from the broker."""
        _LOGGER.debug(f"SengledWifiApi: MQTT disconnected: {rc}")
        self._status = False

    def sync_connect(self) -> None:
        """Connect using a blocking call. Used when an async connection is not in place."""
        self.mqtt_client.connect(
            self.mqtt_server.host,
            port=self.mqtt_server.port,
            keepalive=60,
        )

    def publish_mqtt(self, topic, payload=None):
        """Publish an MQTT message.

        Args:
        topic: topic to publish the message on
        payload: message to send
        returns bool
        """

        if not self.mqtt_client.is_connected():
            _LOGGER.debug(f"SengledWifiApi: MQTT Publish - not connected, trying to connect and publish")
            self.sync_connect()
            self.mqtt_client.loop_start()

        # mproperties = mqttproperties.Properties(packettypes.PacketTypes.PUBLISH)
        # mproperties.UserProperty = ("ha","ha")
        # r = self.mqtt_client.publish(topic, payload=payload, qos=0,properties=mproperties)
            
        r = self.mqtt_client.publish(topic, payload=payload, qos=0)
        _LOGGER.debug(f"SengledWifiApi: MQTT Publish message {r.rc}")
        try:
            r.wait_for_publish()
            return r.is_published()
        except ValueError:
            pass

        return False

    def subscribe_mqtt(self, topic, callback: Callable[[]] = None):
        """Subscribe to an MQTT topic.
        
        Args:
        topic -- topic to subscribe to
        callback -- callback to call when a message comes in
        returns bool
        """
        if not self.mqtt_client.is_connected():
            _LOGGER.debug(f"SengledWifiApi: MQTT Subscribe - not connected, trying to connect and subscribe")
            self.sync_connect()

        r = self.mqtt_client.subscribe(topic)

        _LOGGER.debug("SengledWifiApi: MQTT Subscribe to an topic")
        if r[0] != mqtt.MQTT_ERR_SUCCESS:
            return False

        self.mqtt_client.message_callback_add(topic,callback)
        self.mqtt_client.loop_forever()
        return True

