from telethon import TelegramClient, events, Button
from src.utilities import is_owner, safe_answer_callback
from src.orm import SimpleORM
from src.config import VERSION, load_settings
from src.controllers import ChannelManager,UserManager

settings = load_settings()
orm      = SimpleORM.from_settings(settings)

# USE CONTROLLERS
user_manager    = UserManager(orm)
channel_manager = ChannelManager(orm)

# MAIN MENU
MAIN_MENU_BTN = [
    [Button.inline('📣 Channel management', b'channel_management')],
    [Button.inline('🗞 Script information', b'script_info'), Button.inline('👤 Account information', b'acc_info')],
]

# BOT HELPER
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
                title       = '🔮 Self-adhesive panel',
                description = 'Admin Panel — For Admins Only',
                text        = '🍓 **Welcome to the Self Admin Panel** \n\n👇 Use the buttons:',
                buttons     = MAIN_MENU_BTN
            )
            await event.answer([result], cache_time=0)



    # ======================================== [ CallbackQuery ]
    @bot.on(events.CallbackQuery)
    async def callback_handler(event: events.CallbackQuery.Event):
        sender  = event.sender_id   
        data    = event.data.decode() if event.data else ''

        if not is_owner(sender):
            return

        # get user form database
        user = user_manager.ensure_user(sender, "none")

        # ---------------- ACC INFO ----------------
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

        # ---------------- SCRIPT INFO ----------------
        elif data == 'script_info':
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

        # ---------------- CHANNEL MANAGEMENT [menu] ----------------
        elif data == 'channel_management':
            text = "📣 You can manage your channels in this section\n\n⌨️ Use the menu below to manage"

            buttons = [
                [Button.inline('• Channel list •', b'channel_management_list')],
                [
                    Button.inline('📚 User Guide', b'channel_management_help'),
                    Button.inline('➕ Add channel', b'channel_management_add'),
                ],
                [Button.inline('🔙 Return to main menu', b'main_menu')]
            ]
            try:
                await event.edit(text, buttons=buttons)
            except:
                await safe_answer_callback(event, info_text, alert=True)

        # ---------------- CHANNEL MANAGEMENT [add] ----------------
        elif data == 'channel_management_add':
            pass


        # ---------------- CHANNEL MANAGEMENT [list] ----------------
        elif data == 'channel_management_list':
            pass

        # ---------------- MAIN MENU ----------------
        elif data == 'main_menu':
            main_text = '🍓 **Your own self-management panel** \n\n'
            buttons   = MAIN_MENU_BTN
            try:
                if user['step'] in ('none', 'channel_management'):
                    user_manager.update_user(sender, step="none")
                    await event.edit(main_text, buttons=buttons)
                else:
                    await event.edit(main_text, buttons=buttons)
            except:
                await safe_answer_callback(event, 'Main panel', alert=True)
        
        # else for not found data
        else:
            await event.answer()

    return bot, (await bot.get_me()).username