# This script deletes all emails in Outlook except the most recent email in each thread.
# It is useful for cleaning up your inbox and other folders.
# The script uses the win32com.client module to interact with Outlook. 
# It retrieves emails from the specified folders, organizes them by conversation ID, 
#   and determines which emails to delete based on their conversation ID.
# The script then deletes the emails from the specified folders and moves them to the 
#   Deleted Items folder. 
# It marks the emails as unread and displays a progress bar to track the deletion process.
# The script can be run from the command line with the --inbox flag to include the inbox 
#   in the cleanup.
# You can also include a regular expression to specify categories that should be kept
#  and not deleted.
# IMPORTANT:
#  * This script only works on Windows and requires the win32com.client module.
#  * The first time you run, Windows might ask you to configure the previous 
#       version of Outlook. This is because the newest version of Outlook does not support 
#       the win32com.client module. But Office installs the previous version of Outlook 
#       together with the newer, so you can still use the script to clean up your emails.
#  * It also requires Outlook to be installed on the system.
#  * At the beginning of the script, all instances of Outlook are killed to prevent 
#       any conflicts.
#  * The script will move the emails to the Deleted folder, NOT permanently delete them. 
#       You can recover them from the Deleted Items folder if needed.
#  * The script may take some time to run, depending on the number of emails in your folders.
#       Especially the first time you run, since you may have a lot of emails to process.

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta

if sys.platform != "win32":
    print("This script only works on Windows.")
    sys.exit(1)
import win32com.client

# ANSI color codes
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[0;33m"
RED = "\033[0;31m"
NO_COLOR = "\033[0m"
# Widths for the progress bar and message
TERMINAL_WIDTH = os.get_terminal_size().columns
PROGRESS_WIDTH = int(TERMINAL_WIDTH / 3)
MESSAGE_WIDTH = TERMINAL_WIDTH - PROGRESS_WIDTH - 4
# Outlook folder constants
DELETED_ITEMS = 3
OUTBOX_ITEMS = 4
SENT_ITEMS = 5
INBOX_ITEMS = 6

KEEP_CATEGORY_REGEX = re.compile("Keep")
DEFAULT_START_DATE = (datetime.now() - timedelta(days=3650)).strftime("%Y-%m-%d")

# Simple function to print the attributes of an object, for debugging purposes only.
def dj(x: object) -> None:
    print(json.dumps(dir(x), indent=2, default=str))

def get_item_data(id: str, i: int, count:int) -> dict:
   """Returns a dictionary with the EntryId, ConversationId, and CreationTime of an Outlook item."""
   try:
     item = OUTLOOK.GetItemFromID(id)
     progress(
         i + 1,
         count,
         f"{CYAN}{i+1}{GREEN}/{CYAN}{count} {GREEN}{item.Subject[:32]}                  {NO_COLOR}",
     )
     return {
         'EntryId': item.EntryID,
         'ConversationId': item.ConversationId,
         'CreationTime': datetime.fromtimestamp(item.CreationTime.timestamp()),
         'Categories': item.categories
     }
   except:
     return None


def progress(counter: int, total: int, message: str = "") -> None:
    percent = counter / total
    percent_width = PROGRESS_WIDTH * percent
    bar = "=" * int(percent_width)
    bar += " " * (int(PROGRESS_WIDTH - percent_width))
    print(end=f"\r{YELLOW}|{bar}| {message[:MESSAGE_WIDTH]}{NO_COLOR}")

def retrieve_emails(
    folders: list["win32com.client.CDispatch"], 
    total_count: int,
    start_date:datetime
) -> dict[str, list[tuple]]:
    """
    This function retrieves emails from the given folders and organizes them by conversation ID.

    I am not using folder.GetTable().GetArray(folder.Items.Count + 1) here because GetArray does not return the
        item's ConversationId, which is the way I coalesce conversation items.

    Parameters:
    folders (list['win32com.client.CDispatch']): A list of Outlook folders to retrieve emails from.
    total_count (int): The total number of items to be processed.

    Returns:
    dict[str, list[tuple]]: A dictionary where the keys are conversation IDs and the values are 
        lists of tuples. Each tuple contains the email's creation time, entry ID, folder object, 
        item index, and folder name.

    """
    def quick_retrieve_items_from_folders(folders: list["win32com.client.CDispatch"], start_date: datetime) -> set:
        print(f"{GREEN}Retrieving ids from folders, this is quick.{NO_COLOR}")
        msgIds = set()
        for i, folder in enumerate(folders):
            progress(i + 1, len(folders), folder.Name)
            msgIds = msgIds.union(set([
                msg[0] 
                for 
                    msg 
                in
                    folder.GetTable().GetArray(folder.Items.Count + 1)
                if
                    msg
                    and
                    msg[2].timestamp() >= start_date.timestamp()
            ]))
        return msgIds

    print(f"\n\n{GREEN}Found {CYAN}{total_count}{GREEN} items, now checking threads.{NO_COLOR}")
    msgIds = quick_retrieve_items_from_folders(folders, start_date)
    
    print(f"\n{GREEN}Retrieving items from ids, this takes time...{NO_COLOR}\n")
    items = [get_item_data(id, i, len(msgIds)) for i,id in enumerate(msgIds)]
    items = [item for item in items if item] # remove items we could not retrieve
    items = [item for item in items if item['CreationTime'].timestamp() >= start_date.timestamp()] # remove items older than start_date
    items = [item for item in items if not KEEP_CATEGORY_REGEX.match(item['Categories'], re.IGNORECASE)] # remove items with categories to keep
    emails = defaultdict(list)
    for item in items:
        emails[item['ConversationId']].append(
            (item['CreationTime'], item['EntryId'])
        )
    return emails



def determine_items_to_be_deleted(emails: dict[str, list[tuple]], older_than:datetime = DEFAULT_START_DATE) -> list:
    """
    This function identifies which emails should be deleted based on their conversation IDs.

    Parameters:
    emails (dict[str, list[tuple]]): A dictionary where the keys are conversation IDs and the 
        values are lists of tuples. Each tuple contains the email's creation time, entry ID, 
        folder object, item index, and folder name.

    Returns:
    list: A list of entry IDs that should be deleted.

    The function iterates over the emails dictionary, sorts the emails within each conversation
        by creation time, and adds the entry IDs of all but the most recent email to the 'to_be_deleted' set.
    """
    def mark_conversation_items_other_than_the_last_to_be_deleted(
            emails: dict[str, list[tuple]], 
            to_be_deleted:set, 
            conversation_id:str) ->set:
        return to_be_deleted.union(
            set(
                [
                    item_description[1]
                    for 
                        item_description 
                    in sorted(
                        emails[conversation_id], reverse=True
                        )[1:]
                ]
            )
        )

    def mark_older_messages_to_be_deleted(
            emails: dict[str, list[tuple]], 
            older_than_timestamp: datetime,
              to_be_deleted:set, 
              conversation_id:str) -> set:
        return to_be_deleted.union(
            set(
                [
                    item_description[1]
                    for 
                        item_description 
                    in 
                        emails[conversation_id]
                    if 
                        item_description[0].timestamp() < older_than_timestamp
                ]
            )
        )
    
    older_than_timestamp = older_than.timestamp()
    to_be_deleted = set()
    total_count = sum(len(emails[k]) for k in emails.keys())
    print(
        f"\n\n{GREEN}Finding which emails to delete: {CYAN}{len(emails)}{GREEN} unique items out of "
        f"{CYAN}{total_count}{GREEN} overall.{NO_COLOR}"
    )
    for i, conversation_id in enumerate(emails):
        progress(
            i + 1,
            len(emails),
            f"Adding emails to be deleted {i + 1} of {len(emails)}, {len(to_be_deleted)} "
            "to be deleted.                ",
        )
        to_be_deleted = mark_older_messages_to_be_deleted(emails, older_than_timestamp, to_be_deleted, conversation_id)
        to_be_deleted = mark_conversation_items_other_than_the_last_to_be_deleted(emails, to_be_deleted, conversation_id)
    return list(to_be_deleted) 

def retrieve_folders(include_inbox: bool) -> list["win32com.client.CDispatch"]:
    """
    Retrieves folders from Outlook.

    Parameters:
    include_inbox (bool): A flag indicating whether to include the inbox in the retrieval.

    Returns:
    list['win32com.client.CDispatch']: A list of folders retrieved from Outlook.

    This function retrieves folders from Outlook. If the 'include_inbox' flag is True,
    it includes the inbox in the retrieval. It prints the number of folders being looked at.
    """
    inbox = OUTLOOK.GetDefaultFolder(INBOX_ITEMS)
    print(f"\n\n{GREEN}Looking at {CYAN}{inbox.Folders.Count} {GREEN} Folders{NO_COLOR}")
    folders = [inbox.Folders(i) for i in range(1, inbox.Folders.Count + 1)]
    folders.extend([inbox] if include_inbox else [])
    return folders


def delete_items(to_be_deleted: set[str]) -> int:
    """
    Deletes emails from the specified folders based on their EntryIDs.

    Parameters:
    to_be_deleted (set[str]): A set of EntryIDs of emails to be deleted.

    Returns:
    int: The number of emails deleted.

    This function iterates over the specified folders and their emails. 
    It checks if an email's EntryID is in the 'to_be_deleted' set.
    If it is, the function moves the email to the Deleted Items folder, marks it as unread, 
        and increments the 'deleted' counter.
    The function also keeps track of the total number of emails processed and displays 
        a progress bar.
    """
    print(f"\n\n{GREEN}Deleting {CYAN}{len(to_be_deleted)} {GREEN} emails.{NO_COLOR}")
    processed = 0
    deleted = 0
    deleted_items_folder = OUTLOOK.GetDefaultFolder(DELETED_ITEMS)
    for entry_id_to_delete in to_be_deleted:
        processed += 1
        progress(
            processed,
            len(to_be_deleted),
            f"{processed}/{len(to_be_deleted)} Deleted {deleted}.                ",
        )
        try:
            item = OUTLOOK.GetItemFromID(entry_id_to_delete)
        except Exception as e:
            continue
        if KEEP_CATEGORY_REGEX.match(item.Categories, re.IGNORECASE):
            continue
        item.Unread = False
        item.Move(deleted_items_folder)
        deleted += 1
    return deleted


def get_initial_description() -> str:
    """
    Retrieves the initial description from this script file.
    The initial description is the text that comes after lines starting with "# " 
        until the first line that does not start with "# ".

    Parameters:
    None

    Returns:
    str: The initial description of the script.

    """
    initial_description = ""
    description_mark = "# "
    with open(__file__) as f:
        lines = f.readlines()
        for line in lines:
            if line.startswith(description_mark):
                initial_description += line[len(description_mark) :]
            else:
                break
    return initial_description

def kill_process(process_name: str) -> None:
    """
    Kill a process using PowerShell.

    Parameters:
    process_name (str): The name of the process to kill.
    """
    cmd = '" Get-Process #PROCESS_NAME# -ErrorAction SilentlyContinue | ForEach-Object { $_.Kill(); }"'
    cmd = cmd.replace("#PROCESS_NAME#", process_name)
    subprocess.call(["powershell", cmd,])

def kill_outlook() -> None:
    """
    Kill any existing Outlook processes using PowerShell.
    """
    kill_process("OUTLOOK")
    kill_process("olk")

def validate_date(date_text):
    """Validate a date string in the format YYYY-MM-DD, returns the date as datetime if OK, or throws ArgumentTypeError otherwise."""
    try:
        return datetime.strptime(date_text, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid date format: '{date_text}'. Expected format: YYYY-MM-DD"
        )

def main(include_inbox: bool = False, start_date:datetime = DEFAULT_START_DATE, older_than:datetime = DEFAULT_START_DATE) -> None:
    kill_outlook()    
    folders = retrieve_folders(include_inbox)
    total_count = sum(f.Items.Count for f in folders)
    emails = retrieve_emails(folders, total_count, start_date)
    to_be_deleted = determine_items_to_be_deleted(emails, older_than)
    deleted_count = delete_items(to_be_deleted)
    print(f"\n\n{GREEN}Done, deleted {deleted_count} items.{NO_COLOR}")

OUTLOOK = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")

if __name__ == "__main__":
    usage = f"""

{GREEN}python CleanupEmails.py {CYAN}[-h] [--inbox] [--keep-category-regex KEEP_CATEGORY_REGEX]{GREEN}

  {GREEN}Example: {CYAN}python CleanupEmails.py --inbox --keep-category-regex "Keep|Important"
  {NO_COLOR}
"""
    usage += f"\n\n{YELLOW}{get_initial_description()}{NO_COLOR}\n\n"
    parser = argparse.ArgumentParser(
        description="Cleanup your emails from Outlook.", usage=usage
    )
    parser.add_argument(
        "--inbox", 
        "-i", 
        help="Include the inbox in the cleanup", 
        action="store_true"
    )
    parser.add_argument(
        "--keep-category-regex",
        "-k",
        help="Regular expression with the categories to be kept, ignoring case. "
            "Items marked with these categories will not be deleted.",
        type=str,
        default="Keep",
    )
    parser.add_argument(
        "-s",
        "--start-date",
        type=validate_date,
        default=DEFAULT_START_DATE,
        required=False,
        help=f"Start date to start email search in format YYYY-MM-DD, default is {DEFAULT_START_DATE}. You can use either --start-date or --older-than, but not both.",
    )
    parser.add_argument(
        "-o",
        "--older-than",
        type=validate_date,
        default=DEFAULT_START_DATE,
        required=False,
        help=f"Will delete emails up to this date in format YYYY-MM-DD, default is {DEFAULT_START_DATE}. You can use either --start-date or --older-than, but not both.",
    )
    dsd = validate_date(DEFAULT_START_DATE)
    args = parser.parse_args()
    if args.start_date != dsd and args.older_than != dsd:
        parser.error("--start-date and --older-than are mutually exclusive.")
    KEEP_CATEGORY_REGEX = re.compile(args.keep_category_regex)
    main(args.inbox, args.start_date, args.older_than)
    OUTLOOK.Application.Quit()
    del OUTLOOK
