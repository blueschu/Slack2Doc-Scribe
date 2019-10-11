"""
A simple Flask app to log Slack messages to a Google Docs document
for permanent and accessible storage.
"""

import http
import logging.config

from flask import Flask, redirect
from slackeventsapi import SlackEventAdapter

from . import settings, slack_utils, gspread_utils

__version__ = "0.1.0"


def create_app() -> Flask:
    """Initialize a Flask app instance"""
    # Setup this app's loggers.
    logging.config.dictConfig(settings.LOGGING)

    app = Flask(__name__)

    # Perform slack_utils module's app initialization
    slack_utils.init_app(app)

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

    @slack_events_adapter.on("message")
    def message_posted(event_data):
        app.logger.debug("Message: {}".format(event_data))
        event = event_data["event"]

        if event['channel'] not in settings.SLACK_WATCHED_CHANNELS:
            # Ignore message that were not sent to a whitelisted channel.
            return

        gspread_utils.publish_slack_message(event)

    return app



def _google_url_from_doc_id(doc_id: str) -> str:
    return f'https://docs.google.com/document/d/{doc_id}/'
