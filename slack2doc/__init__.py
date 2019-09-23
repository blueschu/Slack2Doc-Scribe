"""
A simple Flask app to log Slack messages to a Google Docs document
for permanent and accessible storage.
"""

import http

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


@slack_events_adapter.on("message")
def reaction_added(event_data):
    # TODO: write the incoming message to the Google Doc
    # See https://api.slack.com/events/message.
    pass


def _google_url_from_doc_id(doc_id: str) -> str:
    return f'https://docs.google.com/document/d/{doc_id}/'


if __name__ == '__main__':
    app.run()
