from telethon import TelegramClient, events, Button

MAIN_MENU_BTN = [
    [Button.inline('📣 Channel management', b'channel_management')],
    [Button.inline('🗞 Script information', b'script_info'), Button.inline('👤 Account information', b'acc_info')],
]
BACK_MENU_BTN = [
    [Button.inline('🔙 Return to main menu', b'main_menu')]
]
CHANNEL_MANAGEMENT = [
    [Button.inline('• Channel list •', b'channel_management_list')],
    [
        Button.inline('➖ Delete channel', b'channel_management_del'),
        Button.inline('➕ Add channel', b'channel_management_add'),
    ],
    [Button.inline('📚 User Guide', b'channel_management_help')],
    [Button.inline('🔙 Return to main menu', b'main_menu')]
]