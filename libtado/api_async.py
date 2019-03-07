"""libtado

This module provides bindings to the API of https://www.tado.com/ to control
your smart thermostats.

Example:
  import tado.api
  t = tado.api('Username', 'Password')
  print(t.get_me())

Disclaimer:
  This module is in NO way connected to tado GmbH and is not officially
  supported by them!

License:
  Copyright (C) 2017  Max Rosin

  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
import functools
import typing
from typing import Dict
from urllib.parse import urljoin

import aiohttp
import cachetools
import glom

Object = typing.Dict[
    str, typing.Union[str, int, float, "Object", typing.List["Object"]]
]

HEADERS = {"Referer": "https://my.tado.com/"}
API_URL = "https://my.tado.com/api/v2/"


def async_cache(method):
    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        return method(*args, **kwargs)

    return wrapper


def async_cached_property(
    prop=None, *, maxsize=16, ttl=60, cache_attribute="__cache__"
) -> typing.Union[functools.partial, property]:
    if prop is None:
        return functools.partial(async_cached_property, maxsize=maxsize, ttl=ttl)

    key = prop.__name__

    @functools.wraps(prop)
    async def cached_get(self):
        if not hasattr(self, cache_attribute):
            setattr(self, cache_attribute, cachetools.TTLCache(maxsize, ttl))

        cache = getattr(self, cache_attribute)
        if key in cache:
            return cache[key]

        value = await prop(self)
        cache[key] = value
        return value

    return property(cached_get)


class Home:
    def __init__(
        self,
        username: str,
        secret: str,
        session: aiohttp.ClientSession,
        home_id: id,
        access_token: str,
        refresh_token: str,
        access_headers: typing.Dict[str, str],
        temperature_unit: str = "celsius",
    ):
        """Authenticate to the api."""
        self.username = username
        self.secret = secret

        self.session = session
        self.id = home_id
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.access_headers = access_headers
        self.temperature_unit = temperature_unit

    async def _api_call(self, cmd, method, json=None, data=None):
        """Perform an API call."""

        url = urljoin(API_URL, cmd)

        async with self.session.request(
            method=method, url=url, json=json, data=data, headers=self.access_headers
        ) as response:
            response.raise_for_status()
            return await response.json()

    get: typing.Callable[..., typing.Awaitable] = functools.partialmethod(
        _api_call, method="GET"
    )
    post: typing.Callable[..., typing.Awaitable] = functools.partialmethod(
        _api_call, method="POST"
    )
    put: typing.Callable[..., typing.Awaitable] = functools.partialmethod(
        _api_call, method="PUT"
    )
    delete: typing.Callable[..., typing.Awaitable] = functools.partialmethod(
        _api_call, method="DELETE"
    )

    async def refresh_auth(self):
        """Refresh an active session."""
        url = "https://auth.tado.com/oauth/token"
        data = {
            "client_id": "tado-web-app",
            "client_secret": self.secret,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "scope": "home.user",
        }

        async with self.session.post(
            url, data=data, headers=self.access_headers
        ) as request:
            request.raise_for_status()
            response = await request.json()

        self.access_token = response["access_token"]
        self.refresh_token = response["refresh_token"]
        self.access_headers["Authorization"] = "Bearer " + self.access_token

    @property
    async def presence(self):
        return await self.get(f"homes/{self.id}/presence")

    async def get_capabilities(self, zone) -> Object:
        """
    Args:
      zone (int): The zone ID.

    Returns:
      dict: The capabilities of a tado zone as dictionary.

    Example
    =======
    ::

      {
        'temperatures': {
          'celsius': {'max': 25, 'min': 5, 'step': 1.0},
          'fahrenheit': {'max': 77, 'min': 41, 'step': 1.0}
        },
        'type': 'HEATING'
      }

    """
        return await self.get(f"homes/{self.id}/zones/{zone}/capabilities")

    @async_cached_property
    async def devices(self) -> typing.List[Dict]:
        """
    Returns:
      list: All devices of the home as a list of dictionaries.

    Example
    =======
    ::

      [
        {
          'characteristics': { 'capabilities': [] },
          'connectionState': {
            'timestamp': '2017-02-20T18:51:47.362Z',
            'value': True
          },
          'currentFwVersion': '25.15',
          'deviceType': 'GW03',
          'gatewayOperation': 'NORMAL',
          'serialNo': 'SOME_SERIAL',
          'shortSerialNo': 'SOME_SERIAL'
        },
        {
          'characteristics': {
            'capabilities': [ 'INSIDE_TEMPERATURE_MEASUREMENT', 'IDENTIFY']
          },
          'connectionState': {
            'timestamp': '2017-01-22T16:03:00.773Z',
            'value': False
          },
          'currentFwVersion': '36.15',
          'deviceType': 'VA01',
          'mountingState': {
            'timestamp': '2017-01-22T15:12:45.360Z',
            'value': 'UNMOUNTED'
          },
          'serialNo': 'SOME_SERIAL',
          'shortSerialNo': 'SOME_SERIAL'
        },
        {
          'characteristics': {
            'capabilities': [ 'INSIDE_TEMPERATURE_MEASUREMENT', 'IDENTIFY']
          },
          'connectionState': {
            'timestamp': '2017-02-20T18:33:49.092Z',
            'value': True
          },
          'currentFwVersion': '36.15',
          'deviceType': 'VA01',
          'mountingState': {
            'timestamp': '2017-02-12T13:34:35.288Z',
            'value': 'CALIBRATED'},
          'serialNo': 'SOME_SERIAL',
          'shortSerialNo': 'SOME_SERIAL'
        },
        {
          'characteristics': {
            'capabilities': [ 'INSIDE_TEMPERATURE_MEASUREMENT', 'IDENTIFY']
          },
          'connectionState': {
            'timestamp': '2017-02-20T18:51:28.779Z',
            'value': True
          },
          'currentFwVersion': '36.15',
          'deviceType': 'VA01',
          'mountingState': {
            'timestamp': '2017-01-12T13:22:11.618Z',
            'value': 'CALIBRATED'
           },
          'serialNo': 'SOME_SERIAL',
          'shortSerialNo': 'SOME_SERIAL'
        }
      ]
    """
        return await self.get(f"homes/{self.id}/devices")

    async def get_early_start(self, zone) -> bool:
        """
    Get the early start configuration of a zone.

    Args:
      zone (int): The zone ID.

    Returns:
      bool

    Example
    =======
    ::

      { 'enabled': True }
    """
        response = await self.get(f"homes/{self.id}/zones/{zone}/earlyStart")
        return response["enabled"]

    @async_cached_property
    async def home(self) -> Object:
        """
    Get information about the home.

    Returns:
      dict: A dictionary with information about your home.

    Example
    =======
    ::

      {
        'address': {
          'addressLine1': 'SOME_STREET',
          'addressLine2': None,
          'city': 'SOME_CITY',
          'country': 'SOME_COUNTRY',
          'state': None,
          'zipCode': 'SOME_ZIP_CODE'
        },
        'contactDetails': {
          'email': 'SOME_EMAIL',
          'name': 'SOME_NAME',
          'phone': 'SOME_PHONE'
        },
        'dateTimeZone': 'Europe/Berlin',
        'geolocation': {
          'latitude': SOME_LAT,
          'longitude': SOME_LONG
        },
        'id': SOME_ID,
        'installationCompleted': True,
        'name': 'SOME_NAME',
        'partner': None,
        'simpleSmartScheduleEnabled': True,
        'temperatureUnit': 'CELSIUS'
      }
    """
        return await self.get(f"homes/{self.id}")

    @property
    async def home_state(self) -> Object:
        return await self.get(f"homes/{self.id}/state")

    async def set_presence(self, to: str):
        return await self.put(f"homes/{self.id}/presence", json={"homePresence": to})

    @async_cached_property
    async def installations(self) -> typing.List[Object]:
        """
    It is unclear what this does.

    Returns:
      list: Currently only an empty list.

    Example
    =======
    ::

      []
    """
        return await self.get(f"homes/{self.id}/installations")

    @async_cached_property
    async def invitations(self) -> typing.List[Object]:
        """
    Get active invitations.

    Returns:
      list: A list of active invitations to your home.

    Example
    =======
    ::

      [
        {
          'email': 'SOME_INVITED_EMAIL',
          'firstSent': '2017-02-20T21:01:44.450Z',
          'home': {
            'address': {
              'addressLine1': 'SOME_STREET',
              'addressLine2': None,
              'city': 'SOME_CITY',
              'country': 'SOME_COUNTRY',
              'state': None,
              'zipCode': 'SOME_ZIP_CODE'
            },
            'contactDetails': {
              'email': 'SOME_EMAIL',
              'name': 'SOME_NAME',
              'phone': 'SOME_PHONE'
            },
            'dateTimeZone': 'Europe/Berlin',
            'geolocation': {
              'latitude': SOME_LAT,
              'longitude': SOME_LONG
            },
            'id': SOME_ID,
            'installationCompleted': True,
            'name': 'SOME_NAME',
            'partner': None,
            'simpleSmartScheduleEnabled': True,
            'temperatureUnit': 'CELSIUS'
          },
          'inviter': {
            'email': 'SOME_INVITER_EMAIL',
            'enabled': True,
            'homeId': SOME_ID,
            'locale': 'SOME_LOCALE',
            'name': 'SOME_NAME',
            'type': 'WEB_USER',
            'username': 'SOME_USERNAME'
          },
          'lastSent': '2017-02-20T21:01:44.450Z',
          'token': 'SOME_TOKEN'
        }
      ]
    """

        return await self.get(f"homes/{self.id}/invitations")

    @async_cached_property
    async def me(self) -> Object:
        """
    Get information about the current user.

    Returns:
      dict: A dictionary with information about the current user.

    Example
    =======
    ::

      {
        'email': 'SOME_EMAIL',
        'homes': [
          {
            'id': SOME_ID,
            'name': 'SOME_NAME'
          }
        ],
        'locale': 'en_US',
        'mobileDevices': [],
        'name': 'SOME_NAME',
        'username': 'SOME_USERNAME',
        'secret': 'SOME_CLIENT_SECRET'
      }
    """

        return await self.get("me")

    @async_cached_property
    async def mobile_devices(self) -> typing.List[Object]:
        """Get all mobile devices."""
        return await self.get(f"homes/{self.id}/mobileDevices")

    async def get_schedule(self, zone) -> Object:
        """
    Get the type of the currently configured schedule of a zone.

    Args:
      zone (int): The zone ID.

    Returns:
      dict: A dictionary with the ID and type of the schedule of the zone.

    Tado allows three different types of a schedule for a zone:

    * The same schedule for all seven days of a week.
    * One schedule for weekdays, one for saturday and one for sunday.
    * Seven different schedules - one for every day of the week.


    Example
    =======
    ::

      {
        'id': 1,
        'type': 'THREE_DAY'
      }
    """

        return await self.get(f"homes/{self.id}/zones/{zone}/schedule/activeTimetable")

    async def get_state(self, zone) -> Object:
        """
    Get the current state of a zone including its desired and current temperature. Check out the example output for more.

    Args:
      zone (int): The zone ID.

    Returns:
      dict: A dictionary with the current settings and sensor measurements of the zone.

    Example
    =======
    ::

      {
        'activityDataPoints': {
          'heatingPower': {
            'percentage': 0.0,
            'timestamp': '2017-02-21T11:56:52.204Z',
            'type': 'PERCENTAGE'
          }
        },
        'geolocationOverride': False,
        'geolocationOverrideDisableTime': None,
        'link': {'state': 'ONLINE'},
        'overlay': None,
        'overlayType': None,
        'preparation': None,
        'sensorDataPoints': {
          'humidity': {
            'percentage': 44.0,
            'timestamp': '2017-02-21T11:56:45.369Z',
            'type': 'PERCENTAGE'
          },
          'insideTemperature': {
            'celsius': 18.11,
            'fahrenheit': 64.6,
            'precision': {
              'celsius': 1.0,
              'fahrenheit': 1.0
            },
            'timestamp': '2017-02-21T11:56:45.369Z',
            'type': 'TEMPERATURE'
          }
        },
        'setting': {
          'power': 'ON',
          'temperature': {
            'celsius': 20.0,
            'fahrenheit': 68.0
          },
          'type': 'HEATING'
        },
        'tadoMode': 'HOME'
      }
    """
        return await self.get(f"homes/{self.id}/zones/{zone}/state")

    @async_cached_property
    async def users(self) -> typing.List[Object]:
        """Get all users of your home."""
        return await self.get(f"homes/{self.id}/users")

    @async_cached_property
    async def weather(self) -> Object:
        """
    Get the current weather of the location of your home.

    Returns:
      dict: A dictionary with weather information for your home.

    Example
    =======
    ::

      {
        'outsideTemperature': {
          'celsius': 8.49,
          'fahrenheit': 47.28,
          'precision': {
            'celsius': 0.01,
            'fahrenheit': 0.01
          },
          'timestamp': '2017-02-21T12:06:11.296Z',
          'type': 'TEMPERATURE'
        },
        'solarIntensity': {
          'percentage': 58.4,
          'timestamp': '2017-02-21T12:06:11.296Z',
          'type': 'PERCENTAGE'
        },
        'weatherState': {
          'timestamp': '2017-02-21T12:06:11.296Z',
          'type': 'WEATHER_STATE',
          'value': 'CLOUDY_PARTLY'
        }
      }
    """

        return await self.get(f"homes/{self.id}/weather")

    @async_cached_property
    async def zones(self) -> Dict[int, "Zone"]:
        """
    Get all zones of your home.

    Returns:
      list: A list of dictionaries with all your zones.

    Example
    =======
    ::

      [
        { 'dateCreated': '2016-12-23T15:53:43.615Z',
          'dazzleEnabled': True,
          'deviceTypes': ['VA01'],
          'devices': [
            {
              'characteristics': {
                'capabilities': [ 'INSIDE_TEMPERATURE_MEASUREMENT', 'IDENTIFY']
              },
              'connectionState': {
                'timestamp': '2017-02-21T14:22:45.913Z',
                'value': True
              },
              'currentFwVersion': '36.15',
              'deviceType': 'VA01',
              'duties': ['ZONE_UI', 'ZONE_DRIVER', 'ZONE_LEADER'],
              'mountingState': {
                'timestamp': '2017-02-12T13:34:35.288Z',
                'value': 'CALIBRATED'
              },
              'serialNo': 'SOME_SERIAL',
              'shortSerialNo': 'SOME_SERIAL'
            }
          ],
          'id': 1,
          'name': 'SOME_NAME',
          'reportAvailable': False,
          'supportsDazzle': True,
          'type': 'HEATING'
        },
        {
          'dateCreated': '2016-12-23T16:16:11.390Z',
          'dazzleEnabled': True,
          'deviceTypes': ['VA01'],
          'devices': [
            {
              'characteristics': {
                'capabilities': [ 'INSIDE_TEMPERATURE_MEASUREMENT', 'IDENTIFY']
              },
              'connectionState': {
                'timestamp': '2017-02-21T14:19:40.215Z',
                'value': True
              },
              'currentFwVersion': '36.15',
              'deviceType': 'VA01',
              'duties': ['ZONE_UI', 'ZONE_DRIVER', 'ZONE_LEADER'],
              'mountingState': {
                'timestamp': '2017-01-12T13:22:11.618Z',
                'value': 'CALIBRATED'
              },
              'serialNo': 'SOME_SERIAL',
              'shortSerialNo': 'SOME_SERIAL'
            }
          ],
          'id': 3,
          'name': 'SOME_NAME ',
          'reportAvailable': False,
          'supportsDazzle': True,
          'type': 'HEATING'
        }
      ]

    """

        zones = await self.get(f"homes/{self.id}/zones")
        return {zone["id"]: Zone(self, **zone) for zone in zones}

    async def set_early_start(self, zone, enabled) -> Dict[str, bool]:
        """
    Enable or disable the early start feature of a zone.

    Args:
      zone (int): The zone ID.
      enabled (bool): Enable (True) or disable (False) the early start feature of the zone.

    Returns:
      dict: The new configuration of the early start feature.

    Example
    =======
    ::

      {'enabled': True}
    """
        payload = {"enabled": enabled}

        return await self.put(f"homes/{self.id}/zones/{zone}/earlyStart", json=payload)

    async def set_temperature(
        self, zone, temperature: float, termination="MANUAL"
    ) -> Object:
        """
    Set the desired temperature of a zone.

    Args:
      zone (int): The zone ID.
      temperature (float): The desired temperature in celsius.
      termination (str/int): The termination mode for the zone.

    Returns:
      dict: A dictionary with the new zone settings.

    If you set a desired temperature less than 5 celsius it will turn of the zone!

    The termination supports three different mode:

    * "MANUAL": The zone will be set on the desired temperature until you change it manually.
    * "AUTO": The zone will be set on the desired temperature until the next automatic change.
    * INTEGER: The zone will be set on the desired temperature for INTEGER seconds.

    Example
    =======
    ::

      {
        'setting': {
          'power': 'ON',
          'temperature': {'celsius': 12.0, 'fahrenheit': 53.6},
          'type': 'HEATING'
        },
        'termination': {
          'projectedExpiry': None,
          'type': 'MANUAL'
        },
        'type': 'MANUAL'
      }
    """

        def get_termination_dict():
            if termination == "MANUAL":
                return {"type": "MANUAL"}
            elif termination == "AUTO":
                return {"type": "TADO_MODE"}
            else:
                return {"type": "TIMER", "durationInSeconds": termination}

        def get_setting_dict():
            if temperature < 5:
                return {"type": "HEATING", "power": "OFF"}
            else:
                return {
                    "type": "HEATING",
                    "power": "ON",
                    "temperature": {"celsius": temperature},
                }

        payload = {"setting": get_setting_dict(), "termination": get_termination_dict()}

        return await self.put(f"homes/{self.id}/zones/{zone}/overlay", json=payload)

    async def end_manual_control(self, zone):
        """End the manual control of a zone."""
        return await self.delete(f"homes/{self.id}/zones/{zone}/overlay")


class Zone:
    def __init__(self, api: Home, id: int, name: str, **extras):
        self.id = id
        self.name = name
        self.api = api
        self.extras = extras

    @async_cached_property
    async def schedule(self) -> Object:
        return await self.api.get_schedule(self.id)

    @async_cached_property
    async def early_start(self) -> bool:
        return await self.api.get_early_start(self.id)

    @early_start.setter
    async def early_start(self, val: bool):
        await self.api.set_early_start(self.id, val)

    @async_cached_property
    async def state(self) -> Object:
        return await self.api.get_state(self.id)

    @async_cached_property
    async def capabilities(self) -> Object:
        return await self.api.get_capabilities(self.id)

    @property
    async def inside_temperature(self) -> float:
        return glom.glom(
            await self.state,
            ("sensorDataPoints.insideTemperature", self.api.temperature_unit),
        )

    @property
    async def humidity(self) -> float:
        return glom.glom(await self.state, "sensorDataPoints.humidity.percentage")

    async def end_manual_control(self) -> Object:
        return await self.api.end_manual_control(self.id)

    async def set_temperature(self, temperature, termination="MANUAL") -> Object:
        return await self.api.set_temperature(
            self.id, temperature, termination=termination
        )


async def login(username, password, secret) -> Home:
    """Login and setup the HTTP session."""
    url = "https://auth.tado.com/oauth/token"
    data = {
        "client_id": "tado-web-app",
        "client_secret": secret,
        "grant_type": "password",
        "password": password,
        "scope": "home.user",
        "username": username,
    }

    session = aiohttp.ClientSession()

    async with session.post(url, data=data) as response:
        decoded = await response.json()

    access_token = decoded["access_token"]
    refresh_token = decoded["refresh_token"]
    access_headers = HEADERS.copy()
    access_headers["Authorization"] = "Bearer " + decoded["access_token"]
    # We need to talk to api v1 to get a JSESSIONID cookie
    await session.get("https://my.tado.com/api/v1/me", headers=access_headers)

    async with session.get(
        urljoin(API_URL, "me"), headers=access_headers
    ) as me_response:
        me = await me_response.json()

    return Home(
        username=username,
        secret=secret,
        home_id=me["homes"][0]["id"],
        session=session,
        access_token=access_token,
        refresh_token=refresh_token,
        access_headers=access_headers,
    )
