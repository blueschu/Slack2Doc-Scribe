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


def _message_edit(msg, sheet):
    """
    Helper function to handle editting messages. Searchs for
    timestamp of the message that is being edited. If found,
    the message will be altered and the "Edited Timestamp"
    column will be assigned the new timestamp
    """

    # Gathering important information from msg
    old_time_stamp = msg['message']['ts']
    new_time_stamp = msg['message']['edited']['ts']
    new_message = msg['message']['text']

    # Finding other cells with same timestamp
    # TODO: Change 'findall' to 'find' to prevent
    # issues when lots of messages are in the spreadsheet
    cells = sheet.findall(old_time_stamp)

    # Make sure found cells come from timestamp column
    valid_cells = []
    for cell in cells:
        if cell.col == ColumnHeaders['Timestamp']:
            valid_cells.append(cell)

    # If only one cell is found with the timestamp of the original message
    if len(valid_cells) == 1:

        # Get row value
        cell_row = valid_cells[0].row
        # Get column value where the message is stored
        message_cell_col = ColumnHeaders['Message']
        # Get column value where edited timestamp is stored
        edited_timestamp_cell_col = ColumnHeaders['Edited Timestamp']

        # Updated the cells with new edits
        sheet.update_cell(cell_row, message_cell_col, new_message)
        sheet.update_cell(cell_row, edited_timestamp_cell_col, new_time_stamp)

        # Prints success to console
        logging.info(f"Cells ({cell_row}, {message_cell_col}), ({cell_row}, {edited_timestamp_cell_col}) updated")

    # If no previous messages were found
    # with the timestamp of the message to edit
    elif len(valid_cells) == 0:
        # Make no changes, print to console
        logging.warning("Original message not found")
    # If more than one message was found with
    # the original timestamp, unable to make edit
    elif len(valid_cells) > 1:
        # Make no changes, print to console
        logging.warning("Multiple Cells with same time stamp: Unable to edit")


def _message_delete(msg, sheet):
    """
    Helper function to handle deleting messages. Searchs for
    timestamp of the message that is being deleted. If found,
    the whole row with the message will be deleted
    """

    # Gathering important information from msg
    old_time_stamp = msg['ts']

    # Finding other cells with same timestamp
    # TODO: Change 'findall' to 'find' to prevent
    # issues when lots of messages are in the spreadsheet
    cells = sheet.findall(old_time_stamp)

    # Make sure found cells come from timestamp column
    valid_cells = []
    for cell in cells:
        if cell.col == ColumnHeaders['Timestamp']:
            valid_cells.append(cell)

    # If only one cell is found with the timestamp of the original message
    if len(valid_cells) == 1:

        # Get row value
        cell_row = valid_cells[0].row

        # Delete row
        sheet.delete_row(cell_row)

        # Prints Success message to console
        logging.info(f"Row {cell_row} deleted")

    # If there are no messages found with the timestamp of the original message
    elif len(valid_cells) == 0:
        # Do nothing, print to console
        logging.warning("Original message not found")

    # If there are more than 1 message found with the timestamp
    # of the original message
    elif len(valid_cells) > 1:
        # Do nothing, print to console
        logging.warning("Multiple Cells with same time stamp: Unable to delete")


def _message_reply(msg, sheet):
    """
    Helper function to handle replying to messages.
    Yet to be implemented
    """
    pass


def _message(msg, sheet):
    """
    Helper function to handle messages. Creates readable
    timestamp and inserts data into the spreadsheet above all other messages
    """

    # Formats timestamp
    timestamp = datetime.fromtimestamp(msg['ts'], tz=DISPLAY_TIMEZONE)

    # Prepares row to be inserted into spreadsheet
    insertRow = [msg['user'], msg['text'], timestamp.isoformat(), msg['user'], msg['ts']]

    # Inserts row into the spreadsheet with an offset of 2
    # (After row 1 (header row))
    sheet.insert_row(insertRow, 2)

    # Prints success to console
    logging.info("Message Added")


def put_into_sheets(payload):
    """
    Function to handle inserting different types of slack messages into a
    google spreadsheet
    """

    if payload['type'] != 'message':
        raise TypeError("payload must be a Slack Event dictionary of type 'message'")

    # Connecting to google's API
    creds = SACreds.from_json_keyfile_name("Slack2Docscreds.json", GOOGLE_ACCESS_SCOPES)
    client = gspread.authorize(creds)

    sheet = client.open(settings.GOOGLE_SPREADSHEET_NAME)

    # Gets the name of the worksheet that the message belongs in
    desired_worksheet = payload['channel']

    # Initializing the variable that will point to worksheet
    # of the desired channel
    current_channel_log_worksheet = None

    try:
        current_channel_log_worksheet = sheet.worksheet(desired_worksheet)

        # Current headers of the worksheet. Used to check
        # to see if they are different/incorrect/updated
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

        # Creates new worksheet
        sheet.add_worksheet(desired_worksheet, rows, cols)
        current_channel_log_worksheet = sheet.worksheet(desired_worksheet)

    current_channel_log_worksheet.insert_row(ColumnHeaders.__members__.keys(), 1)

    message_callback_lookup = {
        'message_change': _message_edit,
        'message_deleted': _message_delete,
        'message_reply': _message_reply,
        None: _message
    }

    callback = message_callback_lookup[payload.get('subtype')]

    callback(payload, current_channel_log_worksheet)
