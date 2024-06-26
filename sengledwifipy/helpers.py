"""Python Package for controlling Sengled Wifi devices. SPDX-License-Identifier: Apache-2.0."""

import functools
import logging
from asyncio import CancelledError
from http.cookies import CookieError, Morsel
from json import JSONDecodeError
from types import MappingProxyType

from aiohttp import ClientConnectionError, ContentTypeError, ServerDisconnectedError

from .const import EXCEPTION_TEMPLATE
from .errors import (
    SengledWifipyConnectionError,
    SengledWifipyLoginCloseRequested,
    SengledWifipyLoginError,
    SengledWifipyTooManyRequestsError,
)

_LOGGER = logging.getLogger(__name__)


def hide_email(email: str) -> str:
    """Obfuscate email."""
    part = email.split("@")
    if len(part) > 1:
        return f"{part[0][0]}{'*' * (len(part[0]) - 2)}{part[0][-1]}@{part[1][0]}{'*' * (len(part[1]) - 2)}{part[1][-1]}"
    return hide_serial(email)


def hide_password(value: str) -> str:
    """Obfuscate password."""
    return f"REDACTED {len(value)} CHARS"


def hide_serial(item: dict | str | list) -> dict | str | list:
    """Obfuscate serial."""
    if item is None:
        return ""
    if isinstance(item, dict):
        response = item.copy()
        for key, value in item.items():
            if (
                isinstance(value, (dict, list))
                or key
                in [
                    "deviceSerialNumber",
                    "serialNumber",
                    "destinationUserId",
                    "customerId",
                    "access_token",
                    "refresh_token",
                ]
                or "secret" in key
            ):
                response[key] = hide_serial(value)
    elif isinstance(item, str):
        response = f"{item[0]}{'*' * (len(item) - 4)}{item[-3:]}" if len(item) > 6 else f"{'*' * len(item)}"

    elif isinstance(item, list):
        response = []
        for list_item in item:
            if isinstance(list_item, dict):
                response.append(hide_serial(list_item))
            else:
                response.append(list_item)
    return response


def obfuscate(item):
    """Obfuscate email, password, and other known sensitive keys."""
    if item is None:
        return ""
    if isinstance(item, (Morsel)):
        response = dict({item.key: item.value})
        response[item.key] = "OBFUSCATEDCOOKIE"
        return response
    if isinstance(item, (MappingProxyType, dict)):
        response = item.copy()
        for key, value in item.items():
            if key in ["password"]:
                response[key] = hide_password(value)
            elif key in ["email"]:
                response[key] = hide_email(value)
            elif key in ["cookies_txt"]:
                response[key] = "OBFUSCATED COOKIE"
            elif (
                key
                in [
                    "deviceSerialNumber",
                    "serialNumber",
                    "destinationUserId",
                    "customerId",
                    "access_token",
                    "refresh_token",
                ]
                or "secret" in key
            ):
                response[key] = hide_serial(value)
            elif isinstance(value, (dict, list, tuple)):
                response[key] = obfuscate(value)
    elif isinstance(item, (list, tuple)):
        response = []
        for list_item in item:
            if isinstance(list_item, (dict, list, tuple)):
                response.append(obfuscate(list_item))
            else:
                response.append(list_item)
        if isinstance(item, tuple):
            response = tuple(response)
    else:
        return item

    return response


def catch_all_exceptions(func):  # noqa: D103
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except (ClientConnectionError, KeyError, ServerDisconnectedError) as ex:
            _LOGGER.warning(
                "SengledWifi %s.%s(%s, %s): A connection error occurred: %s",
                func.__module__[func.__module__.find(".") + 1 :],
                func.__name__,
                obfuscate(args),
                obfuscate(kwargs),
                EXCEPTION_TEMPLATE.format(type(ex).__name__, ex.args),
            )
            raise SengledWifipyConnectionError from ex
        except (JSONDecodeError, CookieError, ContentTypeError) as ex:
            _LOGGER.warning(
                "SengledWifi %s.%s(%s, %s): A error occurred while calling an api: %s",
                func.__module__[func.__module__.find(".") + 1 :],
                func.__name__,
                obfuscate(args),
                obfuscate(kwargs),
                EXCEPTION_TEMPLATE.format(type(ex).__name__, ex.args),
            )
            raise SengledWifipyLoginError from ex
        except CancelledError as ex:
            _LOGGER.warning(
                "SengledWifi %s.%s(%s, %s): Timeout error occurred accessing SengledWifiAPI: %s",
                func.__module__[func.__module__.find(".") + 1 :],
                func.__name__,
                obfuscate(args),
                obfuscate(kwargs),
                EXCEPTION_TEMPLATE.format(type(ex).__name__, ex.args),
            )
            return None
        except SengledWifipyLoginCloseRequested:
            raise
        except Exception as ex:
            _LOGGER.warning(
                "SengledWifi %s.%s(%s, %s): An error occurred accessing SengledWifiAPI: %s",
                func.__module__[func.__module__.find(".") + 1 :],
                func.__name__,
                obfuscate(args),
                obfuscate(kwargs),
                EXCEPTION_TEMPLATE.format(type(ex).__name__, ex.args),
            )
            raise

    return wrapper


def valid_login_required(func):  # noqa: D103
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        login = (
            getattr(args[0], "_login", None) if hasattr(args[0], "_login") else [arg for arg in args if hasattr(arg, "_urls")][0]
        )

        if not await login.valid_login():
            await login.login(SkipTest=True)
        return await func(*args, **kwargs)

    return wrapper


async def valid_response(response) -> None:
    """Response validation for aiohttp request.

    Args:
        response (ClientResponse): response from aiohttp request
    Returns:
        None
    """
    if response.status == 401:
        raise SengledWifipyLoginError(response.reason)
    if response.status == 429:
        raise SengledWifipyTooManyRequestsError(response.reason)
    if response.status >= 400:
        raise SengledWifipyConnectionError(response.reason)
