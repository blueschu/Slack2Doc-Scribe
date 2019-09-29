import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_secrets_default = os.path.join(BASE_DIR, '.secrets.json')

# Load local settings that we don't like to talk about
with open(os.getenv('FLASK_SETTINGS_SECRETS', _secrets_default)) as secrets_file:
    SECRETS = json.load(secrets_file)

SLACK_SIGNING_SECRET = SECRETS['signing_secret']

SLACK_WATCHED_CHANNELS = SECRETS['channels']

GOOGLE_DOCUMENT_ID = SECRETS['doc_id']

SLACK_ENDPOINT = SECRETS['endpoint']
