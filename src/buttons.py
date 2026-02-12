from telethon import Button

MAIN_MENU_BTN = [
    [Button.inline('📣 Channel Management', b'channel_management')],
    [Button.inline('⚡ Relay Settings', b'relay_settings'),Button.inline('📊 Stats & Maintenance', b'admin_stats')],
    [Button.inline('🗞 Script Information', b'script_info'), Button.inline('👤 Account Information', b'acc_info')],
]

BACK_MENU_BTN = [
    [Button.inline('🔙 Back to Menu', b'main_menu')]
]

CHANNEL_MANAGEMENT = [
    [Button.inline('• Channel list •', b'channel_management_list')],
    [
        Button.inline('➖ Delete Channel', b'channel_management_del'),
        Button.inline('➕ Add Channel', b'channel_management_add'),
    ],
    [Button.inline('📚 User Guide', b'channel_management_help')],
    [Button.inline('🔙 Back to Menu', b'main_menu')]
]
