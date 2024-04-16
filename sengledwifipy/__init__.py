"""Python Package for controlling Sengled Wifi devices. SPDX-License-Identifier: Apache-2.0"""

from importlib.metadata import PackageNotFoundError, metadata as __load
import logging
from pathlib import Path
from .sengledwifiapi import SengledWifiAPI
from .sengledwifilogin import SengledLogin
from .sengledwifimqtt import SengledWifiMQTT

from .errors import (
    SengledWifipyConnectionError,
    SengledWifipyLoginCloseRequested,
    SengledWifipyLoginError,
    SengledWifipyPyotpInvalidKey,
)
from .helpers import catch_all_exceptions, hide_email, hide_serial, obfuscate

pkg = Path(__file__).absolute().parent.name
logger = logging.getLogger(pkg)
metadata = None

try:
    metadata = __load(pkg)
    __uri__ = metadata["home-page"]
    __title__ = metadata["name"]
    __summary__ = metadata["summary"]
    __license__ = metadata["license"]
    __version__ = metadata["version"]
    __author__ = metadata["author"]
    __maintainer__ = metadata["maintainer"]
    __contact__ = metadata["maintainer"]

except PackageNotFoundError:
    logger.error("Could not load package metadata for %s. Is it installed?", pkg)

__all__ = [
    "SengledLogin",
    "SengledWifiAPI",
    "SengledWifiMQTT",
    "SengledWifipyConnectionError",
    "SengledWifipyLoginCloseRequested",
    "SengledWifipyLoginError",
    "SengledWifiProxy",
    "SengledWifipyPyotpInvalidKey",
    "hide_email",
    "hide_serial",
    "obfuscate",
    "catch_all_exceptions",
]
