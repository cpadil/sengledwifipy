"""Python Package for controlling Sengled Wifi devices. SPDX-License-Identifier: Apache-2.0."""

HA_DOMAIN = "sengledwifi"
"""For Home Assistant integration."""

APP_NAME = "Sengled Wifi"
"""For Home Assistant integration."""

EXCEPTION_TEMPLATE = "An exception of type {0} occurred. Arguments:\n{1!r}"
"""Useful for unexpected errors."""

USER_AGENT = "okhttp/4.9.2"
"""Needed for Login."""

SENGLED_ENDPOINTS = {
    "login": "https://ucenter.cloud.sengled.com/user/app/customer/v3/AuthenCross.json",
    "validSession": "https://ucenter.cloud.sengled.com/user/app/customer/v2/isSessionTimeout.json",
    "serverDetails": "https://life2.cloud.sengled.com/life2/server/getServerInfo.json",
}
"""Needed for Login."""
