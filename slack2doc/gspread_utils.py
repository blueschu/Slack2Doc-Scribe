"""
Utilities for interfacing with Google Sheet's API.
"""

import logging
from datetime import datetime
from enum import Enum, unique

import gspread
import pytz
from oauth2client.service_account import ServiceAccountCredentials as SACreds

from . import settings

GOOGLE_ACCESS_SCOPES = [
    "https://spreadsheets.google.com/feeds",
    'https://www.googleapis.com/auth/spreadsheets',
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

DISPLAY_TIMEZONE = pytz.timezone('US/Eastern')


@unique
class ColumnHeaders(Enum):
    """The possible headers for the Google Sheet's spreadsheet."""
    Username = 1
    Message = 2
    TimestampConverted = 3
    UserID = 4
    Timestamp = 5
    TimestampEdited = 6


def publish_slack_message(slack_event_data):
    """
    Write the Slack message specified by the provided data to the configured
    Google Sheet
    """

    if slack_event_data['type'] != 'message':
        raise TypeError("payload must be a Slack Event dictionary of type 'message'")

    # Connecting to google's API
    creds = SACreds.from_json_keyfile_name(settings.GOOGLE_CREDENTIALS_FILE, GOOGLE_ACCESS_SCOPES)
    client = gspread.authorize(creds)

    sheet = client.open(settings.GOOGLE_SPREADSHEET_NAME)

    # Gets the name of the worksheet that the message belongs in
    desired_worksheet = slack_event_data['channel']

    try:
        current_channel_log_worksheet = sheet.worksheet(desired_worksheet)

        current_headers = current_channel_log_worksheet.row_values(1)
        num_rows = current_channel_log_worksheet.col_count

        # Check if the current_headers line up with the updated header structure
        if current_headers != list(ColumnHeaders.__members__.keys()):
            logging.warning("Prexisting table, with improper formatting: Fixing")
            # TODO: move all data, not just headers
            current_channel_log_worksheet.delete_row(1)
        else:
            if num_rows in (0, 1):
                current_channel_log_worksheet.insert_row([], 1)
                current_channel_log_worksheet.insert_row(current_headers, 1)
                current_channel_log_worksheet.delete_row(3)
            current_channel_log_worksheet.delete_row(1)

    except gspread.WorksheetNotFound:
        rows = 1
        cols = len(ColumnHeaders)

        # Create new worksheet
        sheet.add_worksheet(desired_worksheet, rows, cols)
        current_channel_log_worksheet = sheet.worksheet(desired_worksheet)

    current_channel_log_worksheet.insert_row(list(ColumnHeaders.__members__.keys()), 1)

    message_callback_lookup = {
        'message_changed': _publish_message_edit,
        'message_deleted': _publish_message_delete,
        'message_replied': _publish_message_reply,
        None: _publish_message_new
    }

    callback = message_callback_lookup[slack_event_data.get('subtype')]

    callback(slack_event_data, current_channel_log_worksheet)


def _publish_message_edit(msg, sheet):
    """
    Update the configured Google Sheet by altering the row corresponding
    to the edited message.

    Search for the timestamp of the message that was edited. If found,
    the message will be altered and the "Edited Timestamp"
    column will be assigned the new timestamp
    """

    old_time_stamp = msg['message']['ts']
    new_time_stamp = msg['message']['edited']['ts']
    new_message = msg['message']['text']

    # Finding other cells with same timestamp
    # TODO: Change 'findall' to 'find' to prevent
    # issues when lots of messages are in the spreadsheet
    cells = sheet.findall(old_time_stamp)

    # Make sure found cells come from timestamp column
    valid_cells = [c for c in cells if c.col == ColumnHeaders['Timestamp'].value]

    # If only one cell is found with the timestamp of the original message

    if not valid_cells:
        logging.warning("Original message not found")
        # TODO: Add additional error information
    elif len(valid_cells) > 1:
        logging.warning("Multiple Cells with same time stamp: Unable to edit")
        # TODO: Add additional error information
    else:
        # Get row value
        cell_row = valid_cells[0].row
        # Get column value where the message is stored
        message_cell_col = ColumnHeaders['Message'].value
        # Get column value where edited timestamp is stored
        edited_timestamp_cell_col = ColumnHeaders['TimestampEdited'].value

        # Updated the cells with new edits
        sheet.update_cell(cell_row, message_cell_col, new_message)
        sheet.update_cell(cell_row, edited_timestamp_cell_col, new_time_stamp)

        # Prints success to console
        logging.info(f"Cells ({cell_row}, {message_cell_col}), ({cell_row}, {edited_timestamp_cell_col}) updated")


def _publish_message_delete(msg, sheet):
    """
    Remove the row corresponding to the specified deleted message from
    the configured Google Sheet.

    Search for the timestamp of the message that was deleted. If found,
    the whole row with the message will be deleted
    """

    old_time_stamp = msg['ts']

    # Finding other cells with same timestamp
    # TODO: Change 'findall' to 'find' to prevent
    # issues when lots of messages are in the spreadsheet
    cells = sheet.findall(old_time_stamp)

    # Make sure found cells come from timestamp column
    valid_cells = [c for c in cells if c.col == ColumnHeaders['Timestamp'].value]

    if not valid_cells:
        logging.warning("Original message not found")
        # TODO: Add additional error information
    elif len(valid_cells) > 1:
        logging.warning("Multiple Cells with same time stamp: Unable to delete")
        # TODO: Add additional error information
    else:
        # Get row value
        cell_row = valid_cells[0].row
        # Delete row
        sheet.delete_row(cell_row)
        # Prints Success message to console
        logging.info(f"Row {cell_row} deleted")


def _publish_message_reply(msg, sheet):
    """
    Update the configured Google Sheet by adding row representing a reply
    to a previous message.
    """
    logging.warning("Reply functionality not implemented")


def _publish_message_new(msg, sheet):
    """
    Helper function to handle messages. Creates readable
    timestamp and inserts data into the spreadsheet above all other messages
    """
    timestamp = datetime.fromtimestamp(float(msg['ts']), tz=DISPLAY_TIMEZONE)
    row_data = [msg['user'], msg['text'], timestamp.isoformat(), msg['user'], msg['ts']]

    # Inserts row into the spreadsheet with an offset of 2
    # (After row 1 (header row))
    sheet.insert_row(row_data, 2)
    logging.info("Message Added")
