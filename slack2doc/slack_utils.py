"""
Utilities to interface with Slack's Web API.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict

import slack

from . import settings

CACHE_TIME_TO_LIVE = timedelta(days=7)
"""
The duration of time for which a cached `SlackUser` instance is considered
to still be valid. 

SlackUser instances with a `last_refreshed` attribute older than this
duration will be refetched on their next access.
"""

_SLACK_USER_CACHE = {}
"""
Internal cache mapping Slack user ids to `SlackUser` instances. 
"""

_CLIENT = slack.WebClient(token=settings.SLACK_API_TOKEN)
"""
Slack WebClient instance for this module's interactions with the Slack WebAPI.
"""


class SlackUser:
    """
    Lightweight representation of a `Slack user`_.

    .. _Slack user: https://api.slack.com/types/user
    """

    def __init__(self, id, real_name, last_refreshed, **kwargs):
        self.id = id
        self.real_name = real_name

        self.__dict__.update(kwargs)

        if isinstance(last_refreshed, datetime):
            self.last_refreshed = last_refreshed
        else:
            self.last_refreshed = datetime.fromtimestamp(last_refreshed)

    @property
    def entry_expired(self) -> bool:
        """
        Return `True` is this `SlackUser` is older than the allotted TTL
        and should be refreshed.
        """
        return (datetime.now() - self.last_refreshed) > CACHE_TIME_TO_LIVE

    @property
    def display_name(self) -> str:
        """
        Return this user's preferred display name.
        """
        # TODO: Add logic to delegate between the various profile names
        return self.real_name

    def serialize(self) -> dict:
        """
        Convert this `SlackUser` into a JSON serializable dictionary.
        """

        return {**self.__dict__, 'last_refreshed': self.last_refreshed.timestamp()}

    def __str__(self):
        return f"SlackUser(id={self.id}, display_name='{self.display_name}', " \
               f"last_refreshed='{self.last_refreshed}'"


def init_app(app):
    """
    Initialize the specified slack app with this modules teardown routine.

    Save the current state of the user cache dictionary to the storage file
    on app teardown.
    """

    def _teardown(_e):
        _store_user_cache(_SLACK_USER_CACHE)

    app.teardown_appcontext(_teardown)


def get_user_display(user_id: str) -> str:
    """
    Return the display name of the Slack user with the specified user
    id.
    """
    if _SLACK_USER_CACHE is None:
        _SLACK_USER_CACHE.update(_load_user_cache())
    try:
        user = _SLACK_USER_CACHE[user_id]
        if user.entry_expired:
            user = _api_fetch_user_info(user_id)
            _SLACK_USER_CACHE[user_id] = user
    except KeyError:
        user = _api_fetch_user_info(user_id)
        _SLACK_USER_CACHE[user_id] = user
    return user.display_name


def _api_fetch_user_info(user_id: str) -> SlackUser:
    """
    Retrieve the information about the Slack user with the specified user
    id from the Slack Web API.

    Raises a `RuntimeError` if the API request is unsuccessful.
    """
    response = _CLIENT.users_info(user=user_id)

    if response["ok"]:
        user = response['user']
        return SlackUser(**user, last_refreshed=datetime.now())
    elif response["ok"] is False and response["headers"]["Retry-After"]:
        err_message = f"Slack Web API rate limit exceeded when fetching user info for user '{user_id}'"
        logging.error(err_message)
        raise RuntimeError(err_message)
    else:
        err_message = f"Failed to fetch user info for user '{user_id}' - API request failed with status code {response.status_code}"
        logging.error(err_message)
        raise RuntimeError(err_message)


def _load_user_cache() -> Dict[str, SlackUser]:
    """
    Read the configured user cache file and return is contents as a
    dictionary mapping between user ids and `SlackUser` instances.
    """
    try:
        with open(settings.SLACK_USER_CACHE_FILE, "r") as in_file:
            user_dict = json.load(in_file)
        return {k: SlackUser(**v) for k, v in user_dict.items()}
    except FileNotFoundError:
        return {}


def _store_user_cache(user_cache: Dict[str, SlackUser]):
    """
    Write the given user id to `SlackUser` mapping to the configured
    user cache file.
    """
    # Open storage file for writing, truncating existing contents
    with open(settings.SLACK_USER_CACHE_FILE, "w") as out_file:
        json.dump(
            {k: v.serialize() for k, v in user_cache.items()},
            out_file
        )
