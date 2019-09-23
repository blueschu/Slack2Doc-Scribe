import json
import os

from flask import Flask
from slackeventsapi import SlackEventAdapter

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_secrets_default = os.path.join(BASE_DIR, '../.secrets.json')

# Load local settings that we don't like to talk about
with open(os.getenv('FLASK_SETTINGS_SECRETS', _secrets_default)) as secrets_file:
    SECRETS = json.load(secrets_file)

slack_events_adapter = SlackEventAdapter(SECRETS['SLACK_SIGNING_SECRET'], "/slack/events", server=app)


@app.route('/')
def redirect_to_doc():
    # TODO: redirect user to the logger's output document
    pass


@slack_events_adapter.on("message")
def reaction_added(event_data):
    # TODO: write the incoming message to the Google Doc
    pass


if __name__ == '__main__':
    app.run()
