from telethon import TelegramClient, events, Button
from src.utilities import is_owner, safe_answer_callback
from src.config import VERSION

async def start_helper_bot(user_client: TelegramClient, BOT_SESSION: str, API_ID: int, API_HASH: str, BOT_TOKEN: str, SELF_USER_ID: int):
    bot = TelegramClient(BOT_SESSION, API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)

    # ======================================== [ InlineQuery ]
    @bot.on(events.InlineQuery)
    async def inline_handler(event: events.InlineQuery.Event):
        if event.sender_id != SELF_USER_ID:
            await event.answer([], cache_time=0)
            return

        q = (event.text or '').strip().lower()
        if q in ('panel', ''):
            result = event.builder.article(
                title='🔮 Self-adhesive panel',
                description='Admin Panel — For Admins Only',
                text='🍓 **Welcome to the Self Admin Panel** \n\n👇 Use the buttons:',
                buttons=[
                    [Button.inline('🗞 Script information', b'script_info'), Button.inline('👤 Account information', b'acc_info')],
                ]
            )
            await event.answer([result], cache_time=0)



    # ======================================== [ CallbackQuery ]
    @bot.on(events.CallbackQuery)
    async def callback_handler(event: events.CallbackQuery.Event):
        sender = event.sender_id
        data = event.data.decode() if event.data else ''
        if not is_owner(sender):
            return

        # acc_info
        if data == 'acc_info':
            me = await user_client.get_me()
            info_text = (
                f"🛡️ **Self account information**\n"
                f"─────────────────\n"
                f"👤 Name: {me.first_name}\n"
                f"🆔 ID: {me.id}\n"
                f"📛 Username: @{me.username if me.username else 'Not found'}\n"
                f"─────────────────"
            )
            buttons = [[Button.inline('🔙 Return to main menu', b'main_menu')]]
            try:
                await event.edit(info_text, buttons=buttons)
            except:
                await safe_answer_callback(event, info_text, alert=True)

        # script_info
        if data == 'script_info':

            # developers
            developers = [
                {"name": "Hojjat Jahanpour", "github": "https://github.com/hojjatjh"},
                {"name": "Anita Bagheri", "github": "https://github.com/anitabg00"},
            ]

            # Build developers text
            dev_text = "\n".join([f"👤 {dev['name']} — [GitHub]({dev['github']})" for dev in developers])


            info_text = (
                f"🍓 **Script Information**\n"
                f"─────────────────────────────\n"
                f"⚡ Version: {VERSION}\n"
                f"🐍 Python: >=3.10\n"
                f"📜 License: MIT\n"
                f"─────────────────────────────\n"
                f"🧑‍💻 **Developers:**\n"
                f"{dev_text}\n"
                f"─────────────────────────────\n"
                f"✨ Thank you for using this selfbot!"
            )

            # Buttons for GitHub project and main developer
            buttons = [
                [
                    Button.url('📂 GitHub Project', 'https://github.com/hojjatjh/NPVT-AutoPost'),
                    Button.url('👨‍💻 Main Developer', 'https://t.me/hojjat_jh')
                ],
                [Button.inline('🔙 Return to main menu', b'main_menu')]
            ]
            try:
                await event.edit(info_text, buttons=buttons)
            except:
                await safe_answer_callback(event, info_text, alert=True)

        elif data == 'main_menu':
            main_text = '🍓 **Your own self-management panel** \n\n'
            buttons = [
                [Button.inline('🗞 Script information', b'script_info'), Button.inline('👤 Account information', b'acc_info')],
            ]
            try:
                await event.edit(main_text, buttons=buttons)
            except:
                await safe_answer_callback(event, 'Main panel', alert=True)

        else:
            await event.answer()

    return bot, (await bot.get_me()).username