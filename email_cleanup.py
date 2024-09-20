#!/usr/bin/env python3
#
import argparse
import os
import subprocess
import sys
import platform
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from getpass import getpass

try:
    from exchangelib import Account, Configuration, Credentials,DELEGATE
except ImportError:
    if os.name == "posix":
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "exchangelib[kerberos]"]
        )
    if os.name == "nt":
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "exchangelib"]
        )

finally:
    from exchangelib import Account, Configuration, Credentials,DELEGATE

GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[0;33m"
RED = "\033[0;31m"
NO_COLOR = "\033[0m"
TERMINAL_WIDTH = os.get_terminal_size().columns
PROGRESS_WIDTH = int(TERMINAL_WIDTH / 3)
MESSAGE_WIDTH = TERMINAL_WIDTH - PROGRESS_WIDTH - 4


def start_green() -> None:
    print(GREEN, end="")


def start_yellow() -> None:
    print(YELLOW, end="")


def start_cyan() -> None:
    print(CYAN, end="")


def start_red() -> None:
    print(RED, end="")


def end_color() -> None:
    print(NO_COLOR, end="")


def print_green(s: str) -> None:
    start_green()
    print(s)
    end_color()


def print_yellow(s: str) -> None:
    start_yellow()
    print(s)
    end_color()


def print_cyan(s: str) -> None:
    start_cyan()
    print(s)
    end_color()


def print_red(s: str) -> None:
    start_red()
    print(s)
    end_color()


def progress(counter: int, total: int, message: str = "") -> None:
    percent = counter / total
    percent_width = PROGRESS_WIDTH * percent
    bar = "=" * int(percent_width)
    bar += " " * (int(PROGRESS_WIDTH - percent_width))
    print(end=f"\r{YELLOW}|{bar}| {message[:MESSAGE_WIDTH]}{NO_COLOR}")


def check_output(command: object) -> str:
    if type(command) is bytes:
        command = str(command)
    if type(command) is str:
        r = str(subprocess.check_output(command, shell=True))
    elif type(command) is list:
        r = str(subprocess.check_output(command))
    else:
        raise f"Could not handle type {type(command)}"
    if r.startswith("b'") and r.endswith("'"):
        r = r[2:-1]
    return r.replace("\\n", "\n").replace("\\t", "\t")


def get_user_sid(user_name: str) -> str:
    os_name = platform.system()
    if os_name == "Darwin":
        return check_output(f"dsmemberutil getsid -U {user_name}")
    elif os_name == "Windows":
        return check_output(f"wmic useraccount where name='{user_name}' get sid")
    else:
        raise f"Unsupported OS {os_name}"


def get_current_user_sid() -> str:
    return get_user_sid(os.environ["USER"])


def cleanup_folder(folder: object) -> None:
    print_green(f"\n\nCleaning folder {folder.name}")
    unique_messages_on_folder, message_count = get_repeated_items(folder)

    if message_count == len(unique_messages_on_folder):
        print_green(f"\nAll messages are unique in folder {folder.name}.")
    else:
        remove_older_items_from_conversations(folder, unique_messages_on_folder)


def get_repeated_items(folder: object) -> tuple:
    unique_messages_on_folder = defaultdict(lambda: [])
    emails = folder.filter(start__lte=datetime.now(timezone.utc))
    message_count = emails.count()
    print_green(
        f" {message_count} finding unique messages..."
    )
    for counter, email in enumerate(emails, start=1):
        unique_messages_on_folder[email.conversation_id.id].append(
            (email.datetime_received, email.id, email.changekey, email.subject)
        )
        progress(
            counter,
            message_count,
            f"{len(unique_messages_on_folder)}/{counter} unique messages until now.",
        )
    return unique_messages_on_folder, message_count


def remove_older_items_from_conversations(
    folder: object, unique_messages_on_folder: list
) -> None:
    unique_messages_counter = len(unique_messages_on_folder)
    print_green(
        f" {unique_messages_counter} unique messages.\nRemoving non-unique messages..."
    )
    for counter, (conversation_id, value) in enumerate(
        unique_messages_on_folder.items(), start=1
    ):
        progress(counter, unique_messages_counter)
        if len(value) > 1:
            to_delete = sorted(
                unique_messages_on_folder[conversation_id], reverse=True
            )[1:]
            progress(
                counter,
                unique_messages_counter,
                f"Deleting {len(to_delete)} items under conversation `{to_delete[0][3]}`",
            )
            for item in to_delete:
                email_id = item[1]
                changekey = item[2]
                email_item = folder.get(id=email_id, changekey=changekey)
                email_item.is_read = True
                email_item.delete()


def main(include_inbox_root: bool) -> int:
    username = os.environ["USER"] if os.name == "posix" else  os.environ["USERNAME"]
    domain = os.environ["USERDOMAIN"] if os.name == "nt" else "OH NO"
    credential_username = f"{domain}\{username}"

    print(
        f"\n\n{CYAN}{username}{GREEN}, please provide your password or {YELLOW}hit Control-C to cancel:{NO_COLOR}"
    )

    start_cyan()
    password = getpass()
    end_color()
    cred = Credentials(username=credential_username, password=password)
    config = Configuration(server="outlook.office365.com", credentials=cred)
    try:
        account = Account(
            f"{username}@microsoft.com",
            config=config,
            autodiscover=False,
            access_type=DELEGATE,
        )
    except Exception:
        print_red("Could not log in to your Exchange account. Wrong password, maybe?")
        return 2
    del password
    del cred
    account.identity.sid = get_current_user_sid()
    account.identity.upn = f"{username}@microsoft.com"
    inbox = account.root / "Top of Information Store" / "Inbox"
    folders_to_be_cleaned_up = [c.name for c in inbox.children]
    if include_inbox_root:
        print_green("Including inbox root to be cleaned up.")
        folders_to_be_cleaned_up.insert(0, "")
    for subfolder in folders_to_be_cleaned_up:
        folder = inbox / subfolder if subfolder else inbox
        cleanup_folder(folder)
    return 0


if __name__ == "__main__":
    description = f"""

{GREEN}Find all conversations with more than one item and delete all but the very last message.
Search is performed on all mail folders.
Inbox (root) folder will be cleaned up only with the {YELLOW}--include-inbox-root|-r{GREEN} option.
All discarded emails will be sent to the Deleted folder, marked as read.

{NO_COLOR}
"""
    usage = f"""
\n
{CYAN}{__file__}                      {GREEN}# Cleans up all folders except the inbox root folder. {NO_COLOR}
{GREEN}or
{CYAN}{__file__} --include-inbox-root {GREEN}# Cleans up all folders {YELLOW}including{GREEN} the inbox root folder. {NO_COLOR}
{GREEN}or
{CYAN}{__file__} -r                   {GREEN}# same as --include-inbox-root {NO_COLOR}
"""
    parser = argparse.ArgumentParser(
        usage=usage, description=description, add_help=True
    )
    parser.add_argument(
        "--include-inbox-root",
        "-r",
        help=f"{GREEN}If you use this flag, this script will also cleanup the inbox root. Default behavior is to cleanup only the child folders.{NO_COLOR}",
        action="store_true",
        required=False,
    )
    args = parser.parse_args()
    sys.exit(main(args.include_inbox_root))
