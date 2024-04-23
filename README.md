# SengledWifiPy

[![License][license-badge]][license]
[![Python version compatibility][python-badge]][python]
[![Version on PyPi][pypi-badge]][pypi]


Python package for controlling Sengled Wifi devices. 

`NOTE`: This has no relation with Sengled. There's no official API. 

Features:
* Simulates the behavior of the Android App.
* Create a websocket connection to the MQTT broker to receive updates (Cloud Push).
* Alternative method to publish an update without creating a websocket connection.

## Documentation

[Code Documentation][documentation]

TL;DR The package is based on 3 classes:
* `SengledWifiLogin` - Takes care of the login (requires credentials), reduces the API calls to a minimum by saving a session cookie locally.
* `SengledWifiMqtt` - Requires a login (SengledWifiLogin), creates the connection to the MQTT server, subscribe to topics and publish updates. Is a wrapper for [paho-mqtt][paho-mqtt-link].
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

## Contributing

1. [Check for open features/bugs][issues].
2. [Fork the repository][fork].
3. (Recommended) Use the latest version of Python supported >= 3.12.
4. (Recommended) Install [poetry][poetry-link] (recommended installation method: [pipx][pipx-link]):
    - ```pipx install poetry```
5. Install the development environment:
    - ```poetry install --with dev```
    - ```pre-commit install```
6. Code your new feature or bug fix on a new branch.
7. Make sure to update the docstring as required.
8. Submit a pull request!

## Credits

Inspired by:
- [alexapy](https://gitlab.com/keatontaylor/alexapy) (design ideas)
- [ha-sengledapi](https://github.com/jfarmer08/ha-sengledapi)

[pypi]: https://pypi.org/project/sengledwifipy
[pypi-badge]: https://img.shields.io/pypi/v/sengledwifipy
[python]: https://pypi.org/project/sengledwifipy
[python-badge]: https://img.shields.io/pypi/pyversions/sengledwifipy
[license]: https://github.com/cpadil/sengledwifipy?tab=Apache-2.0-1-ov-file
[license-badge]: https://img.shields.io/badge/License-Apache%202.0-blue.svg
[issues]: https://github.com/cpadil/sengledwifipy/issues
[fork]: https://github.com/cpadil/sengledwifipy/fork
[documentation]: https://cpadil.github.io/sengledwifipy
[paho-mqtt-link]: https://pypi.org/project/paho-mqtt/
[poetry-link]: https://python-poetry.org/docs/#installation
[pipx-link]: https://pipx.pypa.io/stable/
