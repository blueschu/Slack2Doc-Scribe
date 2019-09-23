"""
A simple Flask app to log Slack messages to a Google Docs document
for permanent and accessible storage.
"""

import http
import logging

from flask import Flask, redirect
from slackeventsapi import SlackEventAdapter

from . import settings

__version__ = "0.1.0"

app = Flask(__name__)

slack_events_adapter = SlackEventAdapter(settings.SLACK_SIGNING_SECRET, "/slack/events", server=app)


@app.route('/')
def redirect_to_doc():
    return redirect(
        _google_url_from_doc_id(settings.GOOGLE_DOCUMENT_ID),
        code=http.HTTPStatus.TEMPORARY_REDIRECT.value
    )


@slack_events_adapter.on("message.channels")
def message_posted(event_data):
    logging.debug("Message: {}".format(event_data))

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


def _google_url_from_doc_id(doc_id: str) -> str:
    return f'https://docs.google.com/document/d/{doc_id}/'


if __name__ == '__main__':
    app.run()
