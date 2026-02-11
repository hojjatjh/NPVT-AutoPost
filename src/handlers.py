from telethon import TelegramClient, events
from src.utilities import is_owner

user_client: TelegramClient | None = None
BOT_USERNAME: str | None = None


def configure_panel_handler(client: TelegramClient, bot_username: str | None) -> None:
    global user_client, BOT_USERNAME
    user_client = client
    BOT_USERNAME = bot_username


@events.register(events.NewMessage(pattern=r"^\.panel$"))
async def handle_panel(event: events.NewMessage.Event) -> None:
    if not is_owner(event.sender_id):
        return

    if not BOT_USERNAME:
        await event.reply("Helper bot username is not configured yet.")
        return

    active_client = user_client or event.client
    if active_client is None:
        await event.reply("User client is not ready.")
        return

    results = await active_client.inline_query(BOT_USERNAME, "panel")
    if results:
        await results[0].click(event.chat_id)
