"""Python Package for controlling Sengled Wifi devices. SPDX-License-Identifier: Apache-2.0."""

import logging
import os as oos
import ssl
from datetime import datetime
from json import JSONDecodeError, dumps
from typing import Callable
from uuid import uuid4

import certifi
from aiofiles import os
from aiohttp import ClientSession, ContentTypeError, CookieJar
from simplejson import JSONDecodeError as SimpleJSONDecodeError

from .const import EXCEPTION_TEMPLATE, HA_DOMAIN, SENGLED_ENDPOINTS, USER_AGENT
from .errors import SengledWifipyLoginError
from .helpers import (
    catch_all_exceptions,
    hide_email,
    obfuscate,
)

_LOGGER = logging.getLogger(__name__)


class SengledLogin:
    """Handle login connection to Sengled.

    Attributes:
        _email (string): Sengled login account
        _password (string): Password for Sengled login account
        _outputpath (function): os.path.join function pointing to the folder to save a session cookie
        _uuid: (string): Unique 32 char hex to serve as app serial number for registration
        _urls(dict[str, str]): points to the constant SENGLED_ENDPOINTS which is an initial list of Sengled endpoints
        _session (aiohttp.ClientSession): initializes an empty aiohttp.ClientSession to store the cookie information
        _ssl (ssl): used during the authentication
        _headers (dict[str, str]): based on USER_AGENT constant
        status (dict[str, str | bool]): track if the connection is still valid
        stats (dict[str, str | bool]): track number of api calls done
        _cookiefile (str): in combination with _outputpath, provides the path to save the cookie
        _customer_id (str): to store the customer id provided by the authentication api
        _data (dict[str,str]): body for the authentication api
    """

    hass_domain = HA_DOMAIN
    """class attribute; from constant HA_DOMAIN"""

    def __init__(
        self,
        email: str,
        password: str,
        outputpath: Callable[[str], str] = None,
        uuid: str = None,
    ) -> None:
        """Initialization of SengledLogin class. Calls _create_session to initialize a aiohttp.ClientSession.

        Args:
            email (string): Sengled login account
            password (string): Password for Sengled login account
            outputpath (function): Local path with write access for storing files
            uuid: (string): Unique 32 char hex to serve as app serial number for registration

        """
        self._urls: dict[str, str] = SENGLED_ENDPOINTS
        self._email: str = email
        self._password: str = password
        self._session: ClientSession = None
        self._ssl = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH, cafile=certifi.where())
        self._headers: dict[str, str] = {}
        self.status: dict[str, str | bool] = {}
        self.stats: dict[str, str | bool] = {
            "login_timestamp": datetime(1, 1, 1),
            "api_calls": 0,
        }
        self._outputpath = outputpath if outputpath is not None else (lambda b: oos.path.join("temp", b))
        self._cookiefile: str = self._outputpath(f".storage/{type(self).hass_domain}.{self.email}.pickle")
        self._customer_id: str = None
        self._uuid = uuid if uuid else uuid4().hex.upper()
        self._data = {
            "user": self._email,
            "pwd": self._password,
            "uuid": self._uuid,
            "osType": "android",
            "productCode": "life",
            "appCode": "life",
        }

        self._create_session()

    @property
    def urls(self) -> str:
        """SENGLED_ENDPOINTS plus the endpoints provided by _get_server_info."""
        return self._urls

    @property
    def email(self) -> str:
        """Email account for this Login."""
        return self._email

    @property
    def customer_id(self) -> str | None:
        """customer_id for this Login."""
        return self._customer_id

    @property
    def session(self) -> ClientSession | None:
        """Session for this Login."""
        return self._session

    def _create_session(self) -> None:
        """Create an aiohttp session. Called during the initialization."""
        _LOGGER.debug("SengledWifiApi: LOGIN Creating session")

        if not self._session:
            #  define session headers
            self._headers = {
                "User-Agent": USER_AGENT,
                "Accept": "*/*",
                "Accept-Language": "*",
                "Content-Type": "application/json",
            }
            #  initiate session
            self._session = ClientSession(headers=self._headers)

    async def valid_login(self) -> bool:
        """Function that will test the connection is logged in.

        Args:
            None
        Returns:
            Bool. True if the session is still valid, because the cookies has been created recently.
            False if for some reason the cookie no longer exists or there was an error with the validSession endpoint.
        """
        _LOGGER.debug(f'SengledWifiApi: LOGIN validation of session \
                      \n--URL {self._urls["validSession"]}  \
                      \n--Headers {dumps(self._headers)} \
                      \n--last login: {self.stats["login_timestamp"]} \
                      \n--hours: {round((datetime.now() - self.stats["login_timestamp"]).total_seconds()/3600)}h ')
        if (datetime.now() - self.stats["login_timestamp"]).total_seconds() < 86400 and await os.path.exists(self._cookiefile):
            resp = None

            if len(self._session.cookie_jar) == 0:
                self._session.cookie_jar.load(self._cookiefile)

            _LOGGER.debug("SengledWifiApi: LOGIN calling validation api")
            resp = await self._session.post(
                self._urls["validSession"],
                json={},
                ssl=self._ssl,
            )

            try:
                resp = await resp.json()
            except (JSONDecodeError, SimpleJSONDecodeError, ContentTypeError) as ex:
                _LOGGER.debug(f"SengledWifiApi: LOGIN Error during login validation: \
                              \n--{EXCEPTION_TEMPLATE.format(type(ex).__name__, ex.args)}")

            if resp and int(resp.get("messageCode")) == 200:
                _LOGGER.debug("SengledWifiApi: LOGIN login validation with cookie successful")
                self.stats["api_calls"] += 1
                return True
            _LOGGER.debug(f"SengledWifiApi: LOGIN validation api problem: {resp}")
        _LOGGER.debug("SengledWifiApi: LOGIN login not valid, either the login is old >24h or cookie is not valid")

        await self.reset()
        return False

    @catch_all_exceptions
    async def login(self, SkipTest: bool = False) -> None:
        """Login to Sengled.

        Args:
            SkipTest (bool): login without validation (in case there is a cookie in storage)

        Returns:
            None
        """
        if not SkipTest:
            if await self.valid_login():
                return

        _LOGGER.debug("SengledWifiApi: LOGIN Using credentials to login")

        post_resp = await self._session.post(
            self._urls["login"],
            json=self._data,
            headers=self._headers,
            ssl=self._ssl,
        )
        post_resp = await post_resp.json()

        if post_resp:
            if int(post_resp.get("ret")) == 0:
                _LOGGER.debug(f"SengledWifiApi: LOGIN Login successful for {hide_email(self._email)}; saving cookie")
                self._customer_id = post_resp.get("customerId")
                self.status["login_successful"] = True
                self.stats["login_timestamp"] = datetime.now()
                self.stats["api_calls"] += 1
                await self.save_cookiefile()
                await self._get_server_info()
                return
            _LOGGER.debug(f"SengledWifiApi: LOGIN Login not possible for {hide_email(self._email)}")

    async def save_cookiefile(self) -> None:
        """Save login session cookie to file."""
        cookie_jar = self._session.cookie_jar
        assert isinstance(cookie_jar, CookieJar)

        _LOGGER.debug(f'SengledWifiApi: LOGIN Saving cookie to {self._cookiefile.split("/")[0]}')
        try:
            await self.delete_cookie()
            cookie_jar.save(self._cookiefile)
        except (OSError, EOFError, TypeError, AttributeError) as ex:
            _LOGGER.debug(f'SengledWifiApi: LOGIN Error saving pickled cookie to {self._cookiefile.split("/")[0]} .... \
                          \n--{EXCEPTION_TEMPLATE.format(type(ex).__name__, ex.args)}')
            raise SengledWifipyLoginError

        _LOGGER.debug(f"SengledWifiApi: LOGIN Saved session Cookies: \
                      \n--{self._print_session_cookies()}")

    def _print_session_cookies(self) -> str:
        """Prints the value of the cookies in aiohttp session."""
        result: str = ""
        if not self._session.cookie_jar:
            result = "Session cookie jar is empty."
        for cookie in self._session.cookie_jar:
            result += f"{obfuscate(cookie)}"
        return result

    async def _get_server_info(self) -> None:
        """Call to serverDetails endpoint to get Mqtt related endpoints. Called from Login."""
        _LOGGER.debug("SengledWifiApi: LOGIN Getting server endpoints from: %s", self._urls["serverDetails"])

        post_resp = await self._session.post(
            self._urls["serverDetails"],
            json={},
            headers=self._headers,
            ssl=self._ssl,
        )

        try:
            post_resp = await post_resp.json()
        except (JSONDecodeError, SimpleJSONDecodeError, ContentTypeError) as ex:
            _LOGGER.debug(f"SengledWifiApi: LOGIN Error during getServerDetails: \
                          \n--{EXCEPTION_TEMPLATE.format(type(ex).__name__, ex.args)}")

        if int(post_resp.get("messageCode")) == 200:
            self._urls.update(
                {
                    "appserver": post_resp.get("appServerAddr"),
                    "mqtt": post_resp.get("inceptionAddr"),
                    "mqttport": post_resp.get("mqttSslPort"),
                }
            )
            _LOGGER.debug(f"SengledWifiApi: LOGIN Success getting endpoints: \n {dumps(self._urls)}")
        return

    async def close(self) -> None:
        """Close connection for login."""
        if self._session and not self._session.closed:
            if self._session._connector_owner:
                assert self._session._connector is not None
                await self._session._connector.close()
            self._session._connector = None

    async def reset(self) -> None:
        """Remove data related to existing login."""
        _LOGGER.debug(f"SengledWifiApi: LOGIN reset login for {hide_email(self._email)}")
        await self.close()
        self._session = None
        self.status = {}
        await self.delete_cookie()
        self._create_session()

    async def delete_cookie(self) -> None:
        """Deletes the session cookie."""
        _LOGGER.debug(f'SengledWifiApi: LOGIN Deleting cookiefile {self._cookiefile.split("/")[0]} ')

        if await os.path.exists(self._cookiefile):
            try:
                await os.remove(self._cookiefile)
                _LOGGER.debug("SengledWifiApi: LOGIN Deleting cookiefile successful")
                return
            except (OSError, EOFError, TypeError, AttributeError) as ex:
                _LOGGER.debug(f"SengledWifiApi: LOGIN Error deleting cookie: \
                              \n{EXCEPTION_TEMPLATE.format(type(ex).__name__, ex.args)}; please manually remove")
