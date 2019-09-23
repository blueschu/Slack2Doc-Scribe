"""
A simple Flask app to log Slack messages to a Google Docs document
for permanent and accessible storage.
"""

from flask import Flask
from slackeventsapi import SlackEventAdapter

from . import settings

__version__ = "0.1.0"

app = Flask(__name__)

slack_events_adapter = SlackEventAdapter(settings.SLACK_SIGNING_SECRET, "/slack/events", server=app)


@app.route('/')
def redirect_to_doc():
    # TODO: redirect user to the logger's output document
    pass


@slack_events_adapter.on("message")
def reaction_added(event_data):
    # TODO: write the incoming message to the Google Doc
    # See https://api.slack.com/events/message.
    pass


if __name__ == '__main__':
    app.run()
