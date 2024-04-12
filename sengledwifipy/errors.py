"""Python Package for controlling Sengled Wifi devices programmatically.

SPDX-License-Identifier: Apache-2.0

For more details about this api, please refer to the documentation at
https://gitlab.com/cpadil/sengledwifipy
"""


class SengledWifipyError(Exception):
    """Define a base error."""


class SengledWifipyConnectionError(SengledWifipyError):
    """Define an error related to invalid requests."""


class SengledWifipyLoginError(SengledWifipyError):
    """Define an error related to no longer being logged in."""


class SengledWifipyTooManyRequestsError(SengledWifipyError):
    """Define an error related to too many requests."""


class SengledWifipyLoginCloseRequested(SengledWifipyError):
    """Define an error related to requesting access to API after requested close."""


class SengledWifipyPyotpInvalidKey(SengledWifipyError):
    """Define an error related to invalid 2FA key."""
