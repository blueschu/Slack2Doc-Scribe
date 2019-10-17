"""
A simple Flask app to log Slack messages to a Google Docs document
for permanent and accessible storage.
"""

import http
import logging.config

from flask import Flask, redirect, Response
from slackeventsapi import SlackEventAdapter

from . import settings, slack_utils, message_utils, google_client

__version__ = "0.1.0"


def create_app() -> Flask:
    """Initialize a Flask app instance"""
    # Setup this app's loggers.
    logging.config.dictConfig(settings.LOGGING)

    app = Flask(__name__)

    # Perform slack_utils module's app initialization
    slack_utils.init_app(app)

    # Perform google_client module's app initialization
    google_client.init_app(app)

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
            app.logger.debug(f"Message being ignored due to bad channel '{event['channel']}'. "
                             f"Only {settings.SLACK_WATCHED_CHANNELS} are allowed."
            )
            return

        try:
            message_utils.register_message_for_update(event)
        except Exception as e:
            app.logger.exception(f"Failed to call Google Sheets API!")

        # Invoke Flask to send a streaming request to force this app
        # to close connection with the client BEFORE running the after_request
        # handles. This is critical, since updating a Google Sheets at the end
        # of a request can cause this app to exceed the three-second timeout
        # for the Slack Event's API, resulting in Slack sending a duplicate
        # event message.
        def response_stream():
            yield ''

        return Response(response_stream())

    return app



def _google_url_from_doc_id(doc_id: str) -> str:
    return f'https://docs.google.com/document/d/{doc_id}/'
