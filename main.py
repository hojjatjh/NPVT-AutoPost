import asyncio
import logging

from telethon import TelegramClient

from src.bot_helper import start_helper_bot
from src.config import (
    API_HASH,
    API_ID,
    BOT_SESSION,
    BOT_TOKEN,
    PHONE,
    SELF_USER_ID,
    USER_SESSION,
    load_settings,
)
from src.handlers import configure_panel_handler, handle_panel
from src.models import setup
from src.npvt_relay import start_npvt_relay
from src.orm import SimpleORM
from src.utilities import show_logo


async def main() -> None:
    settings = load_settings()
    orm = SimpleORM.from_settings(settings)

    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s")
    log = logging.getLogger("userbot")

    setup(orm)

    show_logo()
    log.info("🍓 Script launched")

    user_client = TelegramClient(USER_SESSION, API_ID, API_HASH)
    await user_client.start(phone=PHONE)
    me = await user_client.get_me()
    log.info("👤 SELF: %s (ID: %s)", me.first_name, me.id)

    user_client.add_event_handler(handle_panel)

    bot_client, bot_username = await start_helper_bot(
        user_client,
        BOT_SESSION,
        API_ID,
        API_HASH,
        BOT_TOKEN,
        SELF_USER_ID,
    )
    configure_panel_handler(user_client, bot_username)
    log.info("🤖 HELPER BOT: @%s", bot_username)

    relay_service = start_npvt_relay(user_client, orm, log)
    log.info("🛠 NPVT relay worker started")

    await asyncio.gather(
        user_client.run_until_disconnected(),
        bot_client.run_until_disconnected(),
    )

    _ = relay_service


if __name__ == "__main__":
    asyncio.run(main())