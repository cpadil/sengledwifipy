"""Python Package for controlling Sengled Wifi devices programmatically.

SPDX-License-Identifier: Apache-2.0

Login class.

This file could not have been written without referencing MIT code from https://github.com/cpadil/sengledwifipy

For more details about this api, please refer to the documentation at
https://gitlab.com/cpadil/sengledwifipy
"""
import logging
import os as oos
from datetime import datetime
from json import JSONDecodeError, dumps
from typing import Callable, Optional, Union
from uuid import uuid4
from aiofiles import os
from aiohttp import ContentTypeError, ClientSession, CookieJar
from simplejson import JSONDecodeError as SimpleJSONDecodeError
from .const import EXCEPTION_TEMPLATE, USER_AGENT, SENGLED_ENDPOINTS,HA_DOMAIN
from .helpers import (
    catch_all_exceptions,
    hide_email,
    obfuscate,
)
from .errors import (
    SengledWifipyLoginError
)

_LOGGER = logging.getLogger(__name__)


class SengledLogin:
    """Class to handle login connection to Sengled. 

    Args:
    email (string): Sengled login account
    password (string): Password for Sengled login account
    outputpath (function): Local path with write access for storing files
    uuid: (string): Unique 32 char hex to serve as app serial number for registration

    """

    hass_domain = HA_DOMAIN

    def __init__(
        self,
        email: str,
        password: str,
        outputpath: Callable[[str], str] = None,
        uuid: Optional[str] = None,
    ) -> None:
        """Set up initial connection and log in."""
        import ssl
        import certifi

        self._urls = SENGLED_ENDPOINTS
        self._email: str = email
        self._password: str = password
        self._session: Optional[ClientSession] = None
        self._ssl = ssl.create_default_context(
            purpose=ssl.Purpose.SERVER_AUTH, cafile=certifi.where()
        )
        self._headers: dict[str, str] = {}
        self.status: Optional[dict[str, Union[str, bool]]] = {}
        self.stats: Optional[dict[str, Union[str, bool]]] = {
            "login_timestamp": datetime(1, 1, 1),
            "api_calls": 0,
        }
        self._outputpath = outputpath if not outputpath == None else (lambda b: oos.path.join("temp",b))
        self._cookiefile: str = self._outputpath(f".storage/{type(self).hass_domain}.{self.email}.pickle")
        self._customer_id: Optional[str] = None
        self.uuid = uuid if uuid else uuid4().hex.upper()
        self._data = {
                "user": self._email,
                "pwd": self._password,
                "uuid": self.uuid,
                "osType": "android",
                "productCode": "life",
                "appCode": "life"
            }

        self._create_session()

    @property
    def urls(self) -> str:
        """Return email or mobile account for this Login."""
        return self._urls

    @property
    def email(self) -> str:
        """Return email or mobile account for this Login."""
        return self._email

    @property
    def customer_id(self) -> Optional[str]:
        """Return customer_id for this Login."""
        return self._customer_id

    @property
    def session(self) -> Optional[ClientSession]:
        """Return session for this Login."""
        return self._session

    def _create_session(self, force=False) -> None:
        """Function to create a session. """
        _LOGGER.debug("SengledWifiApi: LOGIN Creating seesion")

        if not self._session or force:
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
        """Function that will test the connection is logged in. """

        _LOGGER.debug(f'SengledWifiApi: LOGIN validation of session \
                      \nURL {self._urls["validSession"]}  \
                      \nHeaders {dumps(self._headers)} \
                      \nlast login: {self.stats["login_timestamp"]} -- {round((datetime.now() - self.stats["login_timestamp"]).total_seconds()/3600)}h s')
        
        if (datetime.now() - self.stats["login_timestamp"]).total_seconds() < 86400 \
            and await os.path.exists(self._cookiefile):

            resp = None

            if len(self._session.cookie_jar) == 0:
                self._session.cookie_jar.load(self._cookiefile)

            _LOGGER.debug(f'SengledWifiApi: LOGIN calling validation api')
            resp = await self._session.post(
                self._urls["validSession"],
                json={},
                ssl=self._ssl,
            )

            try:
                resp = await resp.json()
            except (JSONDecodeError, SimpleJSONDecodeError, ContentTypeError) as ex:
                _LOGGER.debug(f"SengledWifiApi: LOGIN Error during login validation: {EXCEPTION_TEMPLATE.format(type(ex).__name__, ex.args)}" )

            if (resp and int(resp.get("messageCode")) == 200):
                _LOGGER.debug("SengledWifiApi: LOGIN login validation with cookie successful")
                self.stats["api_calls"] += 1
                return True
            _LOGGER.debug(f'SengledWifiApi: LOGIN validation api problem: {resp}')
        _LOGGER.debug(f'SengledWifiApi: LOGIN login not valid, either the login is old >24h or cookie is not valid')

        await self.reset()
        return False

    @catch_all_exceptions
    async def login(self, SkipTest: bool = False) -> None:
        """Login to Sengled."""

        if not SkipTest:
            if await self.valid_login():
                return

        _LOGGER.debug("SengledWifiApi: LOGIN Using credentials to log in")

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
        """Save login session cookies to file."""
        cookie_jar = self._session.cookie_jar
        assert isinstance(cookie_jar, CookieJar)
        
        _LOGGER.debug(f'SengledWifiApi: LOGIN Saving cookie to {self._cookiefile.split("/")[0]}')
        try:
            if await os.path.exists(self._cookiefile):
                await self.delete_cookie(self._cookiefile)
            cookie_jar.save(self._cookiefile)
        except (OSError, EOFError, TypeError, AttributeError) as ex:
            _LOGGER.debug(f'Error saving pickled cookie to {self._cookiefile.split("/")[0]} .... {EXCEPTION_TEMPLATE.format(type(ex).__name__, ex.args)}')
            raise SengledWifipyLoginError

        _LOGGER.debug("SengledWifiApi: LOGIN Saved session Cookies:\n%s", self._print_session_cookies())

    def _print_session_cookies(self) -> str:
        result: str = ""
        if not self._session.cookie_jar:
            result = "Session cookie jar is empty."
        for cookie in self._session.cookie_jar:
            result += f"{obfuscate(cookie)}"
        return result

    async def _get_server_info(self) ->None:
        """Function that will get server endpoints. """
        
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
            _LOGGER.debug(f"SengledWifiApi: LOGIN Error during getServerDetails: {EXCEPTION_TEMPLATE.format(type(ex).__name__, ex.args)}")
        
        if int(post_resp.get("messageCode")) == 200:
            self._urls.update({
                "appserver":post_resp.get("appServerAddr"),
                "mqtt":post_resp.get("inceptionAddr"),
                "mqttport":post_resp.get("mqttSslPort"),
            })
            _LOGGER.debug(f"SengledWifiApi: LOGIN Success getting endpoints: \n {dumps(self._urls)}" )
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
        if await os.path.exists(self._cookiefile):
            await self.delete_cookie(self._cookiefile)
        self._create_session()

    async def delete_cookie(self,cookiefile: str) -> None:
        """Delete a cookie.

        Args:
            cookiefile (Text): Path to cookie

        """
        _LOGGER.debug(f'SengledWifiApi: LOGIN Deleting cookiefile {cookiefile.split("/")[0]} ')
        try:
            try:
                await os.remove(cookiefile)
            except AttributeError:
                os.remove(cookiefile)
        except (OSError, EOFError, TypeError, AttributeError) as ex:
            _LOGGER.debug(f"SengledWifiApi: LOGIN Error deleting cookie: {EXCEPTION_TEMPLATE.format(type(ex).__name__, ex.args)}; please manually remove")


