"""
Utilities to interface with Slack's Web API.
"""

import functools
import json
from datetime import datetime, timedelta
import logging

import slack

from . import settings

CACHE_TIME_TO_LIVE = timedelta(days=7)

_SLACK_USER_CACHE = {}

_CLIENT = slack.WebClient(token=settings.SLACK_API_TOKEN)

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
        return (datetime.now() - self.last_refreshed) > CACHE_TIME_TO_LIVE

    @property
    def display_name(self) -> str:
        # TODO: Add logic to delegate between the various profile names
        return self.real_name

    def serialize(self):
        return {**self.__dict__, 'updated': self.last_refreshed.timestamp()}

    def __str__(self):
        return f"SlackUser(id={self.id}, display_name='{self.display_name}', " \
               f"last_refreshed='{self.last_refreshed}'"


def init_app(app):
    """
    Initialize the specified slack app with this modules teardown routine.

    Save the current state of the user cache dictionary to the storage file
    on app teardown.
    """
    app.teardown_appcontext(
        functools.partial(_store_user_cache, _SLACK_USER_CACHE)
    )


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


def _load_user_cache():
    try:
        with open(settings.SLACK_USER_CACHE_FILE, "r") as in_file:
            user_dict = json.load(in_file)
        return {k: SlackUser(**v) for k, v in user_dict.iteritems()}
    except FileNotFoundError:
        return {}


def _store_user_cache(user_cache):
    # Open storage file for writing, truncating existing contents
    with open(settings.SLACK_USER_CACHE_FILE, "w") as out_file:
        json.dump(
            {k: v.serialize() for k, v in user_cache.iteritems()},
            out_file
        )
