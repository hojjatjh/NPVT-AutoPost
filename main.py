import os
import asyncio
import logging
from typing import List
from src.config import *
from src.controllers import *
from src.models import setup
from src.orm import SimpleORM
from telethon import TelegramClient, events, Button
from src.utilities import is_owner,OWNERS,safe_answer_callback, show_logo
from src.handlers import handle_panel, configure_panel_handler
from src.bot_helper import start_helper_bot

async def main() -> None:
    settings = load_settings()
    orm      = SimpleORM.from_settings(settings)

    # ------- Logging -------
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s - %(message)s')
    log = logging.getLogger('userbot')

    # setup orm
    setup(orm)

    # ------- Clients -------
    user_client : TelegramClient | None = None
    bot_client  : TelegramClient | None = None
    BOT_USERNAME: str | None = None

    # ------- Run Self -------
    show_logo()
    log.info('\n\n🍓 The script was launched with force')

    user_client = TelegramClient(USER_SESSION, API_ID, API_HASH)
    await user_client.start(phone=PHONE)
    me = await user_client.get_me()
    log.info('✅ SELF: %s (ID: %s)', me.first_name, me.id)

    user_client.add_event_handler(handle_panel)

    bot_client, BOT_USERNAME = await start_helper_bot(
        user_client,
        BOT_SESSION,
        API_ID,
        API_HASH,
        BOT_TOKEN,
        SELF_USER_ID
    )
    configure_panel_handler(user_client, BOT_USERNAME)
    log.info('✅ HELPER BOT: @%s', BOT_USERNAME)

    await asyncio.gather(
        user_client.run_until_disconnected(),
        bot_client.run_until_disconnected()
    )



if __name__ == "__main__":
    asyncio.run(main())