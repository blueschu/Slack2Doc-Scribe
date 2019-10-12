"""
Interface for writing Slack message updates to a Google Sheet.
"""

import logging
from _collections import defaultdict
from datetime import datetime
from enum import Enum, unique
from typing import DefaultDict, List, Optional

import gspread
import pytz
from oauth2client.service_account import ServiceAccountCredentials as SACreds

from . import settings, slack_utils

MESSAGE_WORKSHEET_NAME = 'ALL_MESSAGES'
"""
The name of the Google Sheets worksheet that slack messages should be written
to in the configured Google Sheets spreadsheet.
"""

MAX_PENDING_SHEET_WRITES = 10
"""
The maximum number of pending sheet writes before updates are applied to the
configured Google Sheet.
"""

DISPLAY_TIMEZONE = pytz.timezone('US/Eastern')

GOOGLE_ACCESS_SCOPES = [
    "https://spreadsheets.google.com/feeds",
    'https://www.googleapis.com/auth/spreadsheets',
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

_client: gspread.Client = None
"""
Client instance used to interface with the Google Sheets API.
"""

_pending_sheet_updates: DefaultDict[str, List['SheetUpdate']] = defaultdict(list)
"""
Dictionary mapping Google Sheets spreadsheets to a list of updates that
will be applied to them.
"""

logger = logging.getLogger(__name__)


@unique
class ColumnHeaders(Enum):
    """The possible headers for the Google Sheet's spreadsheet."""
    MessageId = 1
    Username = 2
    Message = 3
    MessageTimestamp = 4
    LastEdited = 5


class BaseSheetUpdate:
    """Base class for all sheet update classes."""
    def __init__(self, message_id: str, message: str, timestamp: str):
        self.message_id = message_id
        self.message = message
        self.timestamp = datetime.fromtimestamp(float(timestamp), tz=DISPLAY_TIMEZONE)

    message_id: str
    message: Optional[str]
    change_existing: bool
    slack_event_data: dict

    def apply_to_sheet(self, worksheet: gspread.Worksheet):
        raise NotImplemented


class SheetUpdateNew(BaseSheetUpdate):
    """A prepared update for adding a new Slack message to a Google sheet."""

    def __init__(self, message_id: str, message: str, timestamp: str, user_id):
        super().__init__(message_id, message, timestamp)
        self.user_id = user_id

    def apply_to_sheet(self, worksheet: gspread.Worksheet):
        """
        Add a row to the specified Google Sheet worksheet corresponding to
        this update's new Slack message.
        """
        user_name = slack_utils.get_user_display(self.user_id)
        row_data = [
            self.message_id,
            user_name,
            self.message,
            self.timestamp.isoformat()
        ]

        # Inserts row into the spreadsheet with an offset of 2
        # (After row 1 (header row))
        worksheet.insert_row(row_data, 2)
        logger.info(f"Message with id={self.message} by {user_name} added")


class SheetUpdateEdit(BaseSheetUpdate):
    """
    A prepared update for modifying an existing Slack message in
    a Google Sheet.
    """

    def __init__(self, message_id: str, message: str, timestamp: str, edit_timestamp):
        super().__init__(message_id, message, timestamp)
        self.edit_timestamp = datetime.fromtimestamp(float(edit_timestamp), tz=DISPLAY_TIMEZONE)

    def apply_to_sheet(self, worksheet: gspread.Worksheet):
        """
        Update the specified Google Sheet worksheet by altering the row
        corresponding to this update's edited message.
        """
        # Find existing cell with the same ID
        try:
            cell = worksheet.find(self.message_id)
        except gspread.CellNotFound:
            logger.error(f"Failed to edit message with id={self.message_id} - original message not found in sheet.")
            return

        if not cell.col == ColumnHeaders['MessageID'].value:
            logger.error(f"Failed to edit message with id={self.message_id} - no message with same ID found.")
            return

        # Get column value where the message is stored
        message_cell_col = ColumnHeaders['Message'].value
        # Get column value where edited timestamp is stored
        edited_timestamp_cell_col = ColumnHeaders['LastEdited'].value

        # Updated the cells with new edits
        worksheet.update_cell(cell.row, message_cell_col, self.message)
        worksheet.update_cell(cell.row, edited_timestamp_cell_col, self.edit_timestamp.isoformat())

        # Prints success to console
        logger.info(f"Cells ({cell.row}, {message_cell_col}), ({cell.row}, {edited_timestamp_cell_col}) updated")


class SheetUpdateDelete(BaseSheetUpdate):
    """
    A prepared update for removing an existing Slack message
     in a Google Sheet.
     """

    def apply_to_sheet(self, worksheet: gspread.Worksheet):
        """
        Remove the row corresponding to this update's deleted message from
        the specified Google Sheet worksheet.
        """
        # Find existing cell with the same ID
        try:
            cell = worksheet.find(self.message_id)
        except gspread.CellNotFound:
            logger.error(f"Failed to delete message with id={self.message_id} - original message not found in sheet.")
            return

        if not cell.col == ColumnHeaders['MessageID'].value:
            logger.error(f"Failed to delete message with id={self.message_id} - no message with same ID found.")
            return

        worksheet.delete_row(cell.row)
        # Prints Success message to console
        logger.info(f"Successfully deleted message with id={self.message_id}.")


class SheetUpdateReply(BaseSheetUpdate):
    """A prepared update for recording a reply to a Slack message."""

    def apply_to_sheet(self, worksheet: gspread.Worksheet):
        # TODO: Implement reply handler
        logger.warning("Reply functionality not implemented")


def init_app(app):
    """
    Initialize the specified slack app with this module's teardown callback.
    """

    def _teardown(_e):
        if len(_pending_sheet_updates) > MAX_PENDING_SHEET_WRITES:
            _write_pending_updates(get_google_client())
        logger.debug("Tearing down")

    # Register callback for app teardown
    app.teardown_appcontext(_teardown)


def register_update(sheet_name: str, update: BaseSheetUpdate):
    """
    Add the specified update to the specified sheet's pending update list.
    """
    _pending_sheet_updates[sheet_name].append(update)


def get_google_client():
    """
    Return this module's Google API client, creating a connection is one
    does not already exist.
    """
    global _client
    if not _client:
        # Connecting to google's API
        logger.debug(f"Connecting to Google API...")
        creds = SACreds.from_json_keyfile_name(settings.GOOGLE_CREDENTIALS_FILE, GOOGLE_ACCESS_SCOPES)
        _client = gspread.authorize(creds)

    return _client


def _write_pending_updates(client):
    """
    Write all pending Google Sheet updates to the Google API.
    """
    global _pending_sheet_updates
    logger.debug("Writing updates to sheet...")
    for sheet_name, updates in _pending_sheet_updates.items():
        try:
            spreadsheet = client.open(sheet_name)
        except gspread.SpreadsheetNotFound:
            logger.exception(f"Failed to open spreadsheet {sheet_name}: no such sheet exists")
            raise

        try:
            worksheet = spreadsheet.worksheet(MESSAGE_WORKSHEET_NAME)
        except gspread.WorksheetNotFound:
            logger.info(f"Worksheet '{MESSAGE_WORKSHEET_NAME}' does not exist. Creating new worksheet.")
            worksheet = spreadsheet.add_worksheet(MESSAGE_WORKSHEET_NAME, rows=1, cols=len(ColumnHeaders))

        _ensure_sheet_formatting(worksheet)

        for update in updates:
            update.apply_to_sheet(worksheet)

    _pending_sheet_updates.clear()


def _ensure_sheet_formatting(worksheet: gspread.Worksheet):
    """
    Ensure that the specified worksheet has the correct header row.

    Overwrites the header row if a header mismatch is found.
    """
    worksheet_headers = worksheet.row_values(1)
    expected_headers = list(ColumnHeaders.__members__.keys())

    # Check if the current_headers line up with the updated header structure
    if worksheet_headers != expected_headers:
        logger.warning("Prexisting table, with improper formatting: Fixing")
        # TODO: move all data, not just headers
        worksheet.delete_row(1)
    else:
        # TODO: ensure the below is still necessary
        if worksheet.row_count in (0, 1):
            worksheet.insert_row([], 1)
            worksheet.insert_row(expected_headers, 1)
            worksheet.delete_row(3)
        worksheet.delete_row(1)
