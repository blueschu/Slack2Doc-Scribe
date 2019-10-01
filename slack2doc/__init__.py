"""
A simple Flask app to log Slack messages to a Google Docs document
for permanent and accessible storage.
"""

import http
import logging.config

from flask import Flask, redirect
from slackeventsapi import SlackEventAdapter

from . import settings

__version__ = "0.1.0"

# Setup this app's loggers.
logging.config.dictConfig(settings.LOGGING)

logger = logging.getLogger(__name__)

app = Flask(__name__)

slack_events_adapter = SlackEventAdapter(
    settings.SLACK_SIGNING_SECRET,
    settings.SLACK_ENDPOINT,
    server=app
)


@app.route('/')
def redirect_to_doc():
    return redirect(
        _google_url_from_doc_id(settings.GOOGLE_DOCUMENT_ID),
        code=http.HTTPStatus.TEMPORARY_REDIRECT.value
    )


@slack_events_adapter.on("message.channels")
def message_posted(event_data):
    logger.debug("Message (message.channels): {}".format(event_data))

    # See https://api.slack.com/events/message.
    if event_data['channel'] in settings.SLACK_WATCHED_CHANNELS:
        if event_data['edited']:
            ...
            # Post "Edited:" message to the Google Doc
            # Could also attempt to edit the doc, but that could
            # be chaotic and introduce data races
        else:
            ...
            # Post standard message to the doc
            # Could include support for logging multiple channels
            # TODO: decide how to handle message subtypes
            # TODO: decide how to handle reactions, stars, pins
    else:
        ...
        # Return 400 code


@slack_events_adapter.on("message")
def message_posted_other(event_data):
    logger.debug("Message (message): {}".format(event_data))


def _google_url_from_doc_id(doc_id: str) -> str:
    return f'https://docs.google.com/document/d/{doc_id}/'


@app.after_request
def after_request():
    from flask import request
    logger.debug(request.json or request.data)

logger.debug("App startup complete.")

if __name__ == '__main__':
    app.run()
