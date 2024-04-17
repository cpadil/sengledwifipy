# SengledWifiPy

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python version compatibility](https://img.shields.io/pypi/pyversions/sengledwifipy)](https://pypi.org/project/sengledwifipy)
[![Version on PyPi](https://img.shields.io/pypi/v/sengledwifipy)](https://pypi.org/project/sengledwifipy)


Python package for controlling Sengled Wifi devices. 

`NOTE`: This has no relation with Sengled. There's no official API. 

Features:
* Simulates the behavior of the Android App.
* Create a websocket connection to the MQTT broker to receive updates (Cloud Push).
* Alternative method to publish an update without creating a websocket connection.

## Documentation

[Code Documentation](https://cpadil.github.io/sengledwifipy)

TL;DR The package is based on 3 classes:
* `SengledWifiLogin` - Takes care of the login (requires credentials), reduces the API calls to a minimum by saving a session cookie locally.
* `SengledWifiMqtt` - Requires a login (SengledWifiLogin), creates the connection to the MQTT server, subscribe to topics and publish updates. Is a wrapper for [paho-mqtt](https://pypi.org/project/paho-mqtt/).
* `SengledWifiApi` - Uses the other two classes to get/set devices state


## Usage example

Simple example that will subscribe to all the topics related to the devices in the Sengled account. SengledWifiMqtt can also receive callbacks for new messages (will be executed when an update is received).

```
import logging
import asyncio
from sengledwifipy import SengledLogin, SengledWifiAPI, SengledWifiMQTT

#set this for testing only
logging.basicConfig(level=logging.DEBUG)

def testing():
    async def testmqtt():
        login = SengledLogin(email = "email@domain.com",password  = "verysecure")
        await login.login()
        devices = await SengledWifiAPI.get_devices(login)
        MqttClient = SengledWifiMQTT(login)
        await MqttClient.async_connect(devices)
        while True:
            await asyncio.sleep(60)
    return asyncio.run(testmqtt())

testing()
```
This is a way to update the device state:

```
SengledWifiAPI.set_device_state(MqttClient,"deviceId",power_on=True, brightness=100)
```


## Credits

Inspired by:
- [alexapy](https://gitlab.com/keatontaylor/alexapy) (design ideas)
- [ha-sengledapi](https://github.com/jfarmer08/ha-sengledapi)
