"""Python Package for controlling Sengled Wifi devices programmatically.

SPDX-License-Identifier: Apache-2.0

Constants.

For more details about this api, please refer to the documentation at
https://gitlab.com/cpadil/sengledwifipy
"""

HA_DOMAIN = "sengledwifi"

EXCEPTION_TEMPLATE = "An exception of type {0} occurred. Arguments:\n{1!r}"

CALL_VERSION = "2.2.556530.0"
APP_NAME = "Sengled Wifi"
USER_AGENT = f"okhttp/4.9.2"
#some additional endpoints are added dynamically
SENGLED_ENDPOINTS = {
        "login": "https://ucenter.cloud.sengled.com/user/app/customer/v3/AuthenCross.json",
        "validSession": "https://ucenter.cloud.sengled.com/user/app/customer/v2/isSessionTimeout.json",
        "serverDetails": "https://life2.cloud.sengled.com/life2/server/getServerInfo.json"
    }