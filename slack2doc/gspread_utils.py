import json
from oauth2client.service_account import ServiceAccountCredentials as SACreds
import gspread
import time

_spreadsheet_file_name = "NU Rover Slack Log"
_col_headers = ["Username", "Message", "Timestamp Converted", "User ID",
                "Timestamp", "Edited Timestamp"]

# Added Dictionary to be able to get column indices based on name
_headers_dict = {}
for i in range(len(_col_headers)):
    _headers_dict[_col_headers[i]] = i+1


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
        if cell.col == _headers_dict['Timestamp']:
            valid_cells.append(cell)

    # If only one cell is found with the timestamp of the original message
    if len(valid_cells) == 1:

        # Get row value
        cell_row = valid_cells[0].row
        # Get column value where the message is stored
        message_cell_col = _headers_dict['Message']
        # Get column value where edited timestamp is stored
        edited_timestamp_cell_col = _headers_dict['Edited Timestamp']

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
        if cell.col == _headers_dict['Timestamp']:
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
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S',
                              time.localtime(int(float(msg['ts']))))

    # Prepares row to be inserted into spreadsheet
    insertRow = [msg['user'], msg['text'], timestamp, msg['user'], msg['ts']]

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

    # Confirming that event is a message event
    if payload['type'] == 'message':

        # Connecting to google's API
        # Giving permissions
        scope = ["https://spreadsheets.google.com/feeds",
                 'https://www.googleapis.com/auth/spreadsheets',
                 "https://www.googleapis.com/auth/drive.file",
                 "https://www.googleapis.com/auth/drive"]
        # Getting credentials
        creds = SACreds.from_json_keyfile_name("Slack2Docscreds.json", scope)

        # Initializing connection with GSpread
        client = gspread.authorize(creds)

        # Opening Spreadsheet
        sheet = client.open(_spreadsheet_file_name)

        # Finding the worksheet within the overall spreadsheet that
        # corresponds to the channel
        worksheets = sheet.worksheets()

        # Gets the name of the worksheet that the message belongs in
        desired_worksheet = payload['channel']

        # Assumes that there is not an existing spreadsheet
        desired_worksheet_exists = False

        # Intializing the variable that will point to worksheet
        # of the desired channel
        current_channel_log_worksheet = None

        # Loops through all worksheets and determines if a previous
        # one exists or not.
        for worksheet in worksheets:
            if worksheet.title == desired_worksheet:
                desired_worksheet_exists = True
                break

        # If worksheet exists
        if desired_worksheet_exists:
            # Store worksheet in current_channel_log_worksheet
            current_channel_log_worksheet = sheet.worksheet(desired_worksheet)

            # Important Variables
            # Current headers of the worksheet. Used to check
            # to see if they are different/incorrect/updated
            current_headers = current_channel_log_worksheet.row_values(1)
            # Number of rows in the spreadsheet
            num_rows = len(current_channel_log_worksheet.col_values(1))

            # If the current_headers line up with the updated header structure
            if len(current_headers) == len(_col_headers):

                # If there is only 1 row in the spreadsheet
                if num_rows == 1:
                    """
                    With the current setup of inserting messages and keeping a
                    header row, there must be an empty row below the header
                    row.This if statement takes care of this special case where
                    there is only a header row and 0 rows below it
                    """
                    current_channel_log_worksheet.insert_row([], 1)
                    current_channel_log_worksheet.insert_row(current_headers, 1)
                    current_channel_log_worksheet.delete_row(3)

                # Assumes that they are set up properly
                headers_properly_setup = True

                # Loops through official headers to see if they line up with
                # current headers (in case of update)
                for column in range(len(_col_headers)):
                    if _col_headers[column] != current_headers[column]:
                        # Headers don't line up with new headers --> set
                        # variable to false to trigger update later
                        headers_properly_setup = False
                        break

                # If the header rows are not set up properly, change them
                if not headers_properly_setup:
                    logging.warning("Prexisting table, with improper formatting: Fixing")
                    # TODO: move all data, not just headers
                    current_channel_log_worksheet.delete_row(1)
                    current_channel_log_worksheet.insert_row(_col_headers, 1)
            # If the official header row doesn't have the same amount of
            # headers as the header row in the doc
            else:
                if num_rows == 1 or num_rows == 0:
                    current_channel_log_worksheet.insert_row([], 1)
                    current_channel_log_worksheet.insert_row(current_headers, 1)
                    current_channel_log_worksheet.delete_row(3)

                # TODO: move all data, not just headers
                current_channel_log_worksheet.delete_row(1)
                current_channel_log_worksheet.insert_row(_col_headers, 1)

        # If no worksheet exists
        else:
            # Set up variables for creating a new spreadsheet
            rows = 1
            cols = len(_col_headers)

            # Creates new worksheet
            sheet.add_worksheet(desired_worksheet, rows, cols)
            current_channel_log_worksheet = sheet.worksheet(desired_worksheet)
            current_channel_log_worksheet.insert_row(_col_headers, 1)

        if 'subtype' in payload:
            if payload['subtype'] == "message_changed":
                _message_edit(payload, current_channel_log_worksheet)
            elif payload['subtype'] == "message_deleted":
                _message_delete(payload, current_channel_log_worksheet)
            elif payload['subtype'] == "message_replied":
                _message_reply(payload, current_channel_log_worksheet)
            else:
                # Generic Handler?
                pass
        else:
            # Normal message
            _message(payload, current_channel_log_worksheet)
