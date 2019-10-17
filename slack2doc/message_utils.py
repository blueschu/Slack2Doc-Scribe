"""
Utilities for converting Slack message data into Google Sheets updates.
"""

import logging

from . import google_client, settings

logger = logging.getLogger(__name__)


def register_message_for_update(slack_event_data):
    """
    Register the Slack message update specified by the provided data to be
    applied to the configured Google Sheet during the next batch update.
    """
    if slack_event_data['type'] != 'message':
        raise TypeError("payload must be a Slack Event dictionary of type 'message'")

    update_builder_lookup = {
        'message_changed': _build_update_edit,
        'message_deleted': _build_update_delete,
        'message_replied': _build_update_reply,
        None: _build_update_new
    }

    spreadsheet_name = settings.GOOGLE_SPREADSHEET_NAME

    # Lookup the builder function for the slack message type received.
    logger.debug(f"Received message of type {slack_event_data.get('subtype')}. Calling type handler...")
    builder = update_builder_lookup[slack_event_data.get('subtype')]

    # Register the SheetUpdate instance associated with the slack message for
    # application in the update next batch.
    sheet_update = builder(slack_event_data)
    google_client.register_update(spreadsheet_name, sheet_update)


def _build_update_edit(slack_event) -> google_client.BaseSheetUpdate:
    """
    Build a sheet update that corresponds to the specified Slack message
    edit event.
    """
    return google_client.SheetUpdateEdit(
        message_id=slack_event['message']['client_msg_id'],
        message=slack_event['message']['text'],
        timestamp=slack_event['message']['ts'],
        edit_timestamp=slack_event['message']['edited']['ts']
    )


def _build_update_delete(slack_event):
    """
    Build a sheet update that corresponds to the specified Slack message
    delete event.
    """
    return google_client.SheetUpdateDelete(
        message_id=slack_event['message']['client_msg_id'],
        message=slack_event['message']['text'],
        timestamp=slack_event['message']['ts'],
    )


def _build_update_reply(slack_event):
    """
    Build a sheet update that corresponds to the specified Slack message
    reply event.
    """
    return google_client.SheetUpdateReply(
        message_id=slack_event['message']['client_msg_id'],
        message=slack_event['message']['text'],
        timestamp=slack_event['message']['ts'],
    )


def _build_update_new(slack_event):
    """
    Build a sheet update that corresponds to the specified new Slack message
    event.
    """
    return google_client.SheetUpdateNew(
        message_id=slack_event['client_msg_id'],
        message=slack_event['text'],
        timestamp=slack_event['ts'],
        user_id=slack_event['user'],
    )
