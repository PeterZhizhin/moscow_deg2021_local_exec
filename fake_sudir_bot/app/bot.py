#!/usr/bin/env python
# -*- coding: utf-8 -*-


from ast import Call
from curses import use_default_colors
import logging
import hmac
import hashlib
import os
import random
from typing import Dict, List
import json
from venv import create

import requests

from telegram import Update, ForceReply, User as TgUser
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Enable logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

logger = logging.getLogger(__name__)


USER_KEYS = ["id", "first_name", "last_name", "middle_name", "mobile", "mail"]

MALE_NAMES = [
    ["Александр", "Сергей", "Дмитрий", "Андрей", "Алексей", "Максим"],
    ["Александрович", "Сергеевич", "Дмитриевич", "Андреевич", "Алексеевич", "Максимович"],
    ["Александров", "Сергеев", "Дмитриев", "Андреев", "Алексеев", "Максимов"],
]

FEMALE_NAMES = [
    ["Елена", "Ольга", "Наталья", "Екатерина", "Анна", "Татьяна"],
    ["Александровна", "Сергеевна", "Дмитриевна", "Андреевна", "Алексеевна", "Максимовна"],
    ["Александрова", "Сергеева", "Дмитриева", "Андреева", "Алексеева", "Максимова"],
]


# Define a few command handlers. These usually take the two arguments update and
# context.
def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    update.message.reply_markdown_v2(
        f'Hi {user.mention_markdown_v2()}\\!\n'
        f'Use /register command to register for fake election',
    )


def create_user(tg_user: TgUser):
    first_names, middle_names, last_names = random.choice([MALE_NAMES, FEMALE_NAMES])

    first_name = random.choice(first_names)
    last_name = random.choice(last_names)
    middle_name = random.choice(middle_names)

    mobile_int = random.randrange(10**10)
    mobile = f"7{mobile_int:010}"
    mail = f"{mobile}@telegram.org"
    mobile = f"{mobile}"
    return {
        "id": str(tg_user.id),
        "first_name": first_name,
        "last_name": last_name,
        "middle_name": middle_name,
        "mobile": mobile,
        "mail": mail,
    }


# def canonize_dict(d: Dict, keys: List[str]) -> str:
#     return json.dumps([d.get(key) for key in keys])


# def sign(data: Dict, keys: List[str]) -> None:
#     key = os.environ.get("TELEGRAM_BOT_SECRET").encode()
#     canonized = canonize_dict(data, keys)
#     h = hmac.new(key, canonized.encode(), hashlib.sha256)
#     logger.debug(f"Canonized: {canonized.encode()}, digest: {h.hexdigest()}")
#     data["auth_hmac"] = h.hexdigest()


def register(update: Update, context: CallbackContext) -> None:
    tg_user = update.effective_user
    if tg_user is None:
        return
    user_dict = create_user(tg_user)
    user_dict["token"] = os.environ.get("TELEGRAM_BOT_SECRET")
    # sign(user_dict, USER_KEYS)
    fake_sudir_url = "http://fake_sudir"
    rsp = requests.post(fake_sudir_url + "/oauth/tg/register", data=user_dict)
    if rsp.status_code == 200:
        update.message.reply_text(
            f'Registration complete.\n'
            f'I have generated a random account for you.\n'
            f'Use your "mobile" to login for the election\n'
            f'  mobile: {user_dict["mobile"]}\n'
            f'  mail: {user_dict["mail"]}\n'
            f'  first name: {user_dict["first_name"]}\n'
            f'  middle name: {user_dict["middle_name"]}\n'
            f'  last name: {user_dict["last_name"]}'
        )
    else:
        update.message.reply_text(f'Registration request failed:\n{rsp.content}')


def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')


def echo(update: Update, context: CallbackContext) -> None:
    """Echo the user message."""
    tg_user = update.effective_user
    if tg_user is None:
        return


def main() -> None:
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    updater = Updater(token)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("register", register))
    dispatcher.add_handler(CommandHandler("help", help_command))

    # on non command i.e message - echo the message on Telegram
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
