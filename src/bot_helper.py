import json
import os

from telethon import TelegramClient, events, Button

from src.buttons import BACK_MENU_BTN, CHANNEL_MANAGEMENT, MAIN_MENU_BTN
from src.config import VERSION, load_settings
from src.controllers import ChannelManager, ConfigManager, RelaySettingsManager, UserManager
from src.orm import SimpleORM
from src.utilities import is_owner, safe_answer_callback

settings = load_settings()
orm      = SimpleORM.from_settings(settings)

user_manager            = UserManager(orm)
channel_manager         = ChannelManager(orm)
config_manager          = ConfigManager(orm)
relay_settings_manager  = RelaySettingsManager(orm)


async def resolve_channel_title(client: TelegramClient, channel_id: int) -> str:
    """Return a readable title for the source ID or fall back to the numeric ID."""
    try:
        entity = await client.get_entity(channel_id)
    except Exception:
        return str(channel_id)

    title = getattr(entity, "title", None)
    if title:
        return title

    first_name = getattr(entity, "first_name", None)
    last_name = getattr(entity, "last_name", None)
    if first_name or last_name:
        return " ".join(part for part in (first_name, last_name) if part)

    return str(channel_id)


def build_relay_settings_text() -> str:
    runtime = relay_settings_manager.get_runtime_settings()
    relay_state = "ON" if bool(runtime["relay_enabled"]) else "OFF"
    dedup_state = "ON" if bool(runtime["dedup_enabled"]) else "OFF"
    return (
        "⚡ **Relay Runtime Settings** ⚡\n\n"
        f"• **Relay Status:** {relay_state}\n"
        f"• **Duplicate Filter:** {dedup_state}\n"
        f"• **Caption:** {runtime['caption']}\n"
        f"• **Rate Limit:** Every {runtime['send_interval_seconds']} sec ⏱️\n"
        f"• **File Prefix:** {runtime['filename_prefix']}\n"
        f"• **Source Refresh:** Every {runtime['source_cache_seconds']} sec 🔄\n\n"
        "💡 *Captions support multi-line text and are fully multilingual (Persian/English)*"
    )


def build_relay_settings_buttons() -> list[list[Button]]:
    runtime = relay_settings_manager.get_runtime_settings()
    relay_state = "🔴 Disable Relay" if bool(runtime["relay_enabled"]) else "🟢 Enable Relay"
    dedup_state = "🔴 Disable Duplicate Filter" if bool(runtime["dedup_enabled"]) else "🟢 Enable Duplicate Filter"
    return [
        [Button.inline("✏️ Set Caption", b"relay_set_caption")],
        [Button.inline("⏱️ Set Rate Limit", b"relay_set_rate_limit"),Button.inline("📁 Set File Prefix", b"relay_set_file_prefix"),Button.inline("🔄 Set Source Refresh", b"relay_set_source_refresh")],
        [Button.inline(relay_state, b"relay_toggle_enabled"),Button.inline(dedup_state, b"relay_toggle_dedup")],
        [Button.inline("🔙 Back to Menu", b"main_menu")],
    ]


def build_admin_stats_text() -> str:
    stats = config_manager.get_stats()
    channels_count = channel_manager.count_channels()
    dedup_cache_size = int(stats["unique_file_hashes"] or 0)

    return (
        "📊 **Stats & Maintenance**\n\n"
        f"• **Channel Mappings:** {channels_count}\n"
        f"• **Total Relayed Files:** {stats['total_transfers']}\n"
        f"• **Unique Source Chats:** {stats['unique_source_chats']}\n"
        f"• **Unique Destination Chats:** {stats['unique_destination_chats']}\n"
        f"• **Unique File IDs:** {stats['unique_file_ids']}\n"
        f"• **Unique File Hashes (Dedup Cache):** {dedup_cache_size}\n"
        f"• **Latest Transfer:** {stats['latest_transfer_date']}\n\n"
        "⚠️ *Note: Resetting configs will clear transfer history and duplicate cache.*"
    )


def build_admin_stats_buttons() -> list[list[Button]]:
    return [
        [Button.inline("🔄 Refresh Stats", b"admin_stats_refresh"),Button.inline("⚠️ Reset Configs Table", b"admin_reset_configs")],
        [Button.inline("🔙 Back to Menu", b"main_menu")],
    ]


async def start_helper_bot(
    user_client: TelegramClient,
    BOT_SESSION: str,
    API_ID: int,
    API_HASH: str,
    BOT_TOKEN: str,
    SELF_USER_ID: int,
):
    self_client = user_client
    bot         = TelegramClient(BOT_SESSION, API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)

    @self_client.on(events.NewMessage)
    async def message_handler(event):
        sender = event.sender_id
        if not is_owner(sender):
            return

        user = user_manager.ensure_user(sender, "none")
        text = (event.text or "").strip()
        lower_text = text.lower()

        if lower_text in {".panel", "/panel"}:
            user_manager.update_user(sender, step="none", data=json.dumps({}))
            return

        if user["step"] == "reset_configs_confirm":
            if lower_text == "cancel":
                user_manager.update_user(sender, step="none", data=json.dumps({}))
                await event.reply("📍 Configs reset cancelled.")
                return

            if text != "RESET CONFIGS":
                await event.reply("❓ Confirmation mismatch. Send exactly: RESET CONFIGS\nOr send: cancel")
                return

            removed = config_manager.reset_all_transfers()
            user_manager.update_user(sender, step="reset_configs_confirm", data=json.dumps({}))
            await event.reply(
                f"✅ Configs table reset successfully.\n"
                f"• Removed rows: {removed}\n"
                "Duplicate cache is now cleared."
            )
            return

        if user["step"] == "relay_caption":
            if lower_text == "cancel":
                user_manager.update_user(sender, step="none", data=json.dumps({}))
                await event.reply("• Relay caption update cancelled.")
                return

            caption_text = text.replace("\\n", "\n")
            caption_text = caption_text.replace("\r\n", "\n").replace("\r", "\n")
            if len(caption_text.strip()) > 1000:
                await event.reply("• Caption too long. Telegram allows max 1024 characters.")
                return

            relay_settings_manager.set_caption(caption_text)
            user_manager.update_user(sender, step="relay_caption", data=json.dumps({}))
            await event.reply("• Relay caption updated successfully.")
            return

        if user["step"] == "relay_rate_limit":
            if lower_text == "cancel":
                user_manager.update_user(sender, step="none", data=json.dumps({}))
                await event.reply("• Rate limit update cancelled.")
                return

            try:
                seconds = float(text)
                if seconds < 1:
                    raise ValueError
            except ValueError:
                await event.reply("• Invalid value. Send a number >= 1 (example: 6)")
                return

            relay_settings_manager.set_send_interval_seconds(seconds)
            user_manager.update_user(sender, step="relay_rate_limit", data=json.dumps({}))
            await event.reply("• Rate limit updated successfully.")
            return

        if user["step"] == "relay_file_prefix":
            if lower_text == "cancel":
                user_manager.update_user(sender, step="none", data=json.dumps({}))
                await event.reply("• File prefix update cancelled.")
                return

            normalized_prefix = relay_settings_manager.normalize_filename_prefix(text)
            relay_settings_manager.set_filename_prefix(normalized_prefix)
            user_manager.update_user(sender, step="relay_file_prefix", data=json.dumps({}))
            await event.reply(f"✅ File prefix updated successfully.\nCurrent prefix: {normalized_prefix}")
            return

        if user["step"] == "relay_source_refresh":
            if lower_text == "cancel":
                user_manager.update_user(sender, step="none", data=json.dumps({}))
                await event.reply("• Source refresh update cancelled.")
                return

            try:
                seconds = int(text)
                if seconds < 5:
                    raise ValueError
            except ValueError:
                await event.reply("• Invalid value. Send an integer >= 5 (example: 20)")
                return

            relay_settings_manager.set_source_cache_seconds(seconds)
            user_manager.update_user(sender, step="relay_source_refresh", data=json.dumps({}))
            await event.reply("✅ Source refresh updated successfully.")
            return

        if user["step"] == "panel2":
            try:
                if text.startswith("-100") and text[4:].isdigit():
                    source_id = int(text)
                else:
                    entity = await self_client.get_entity(text)
                    source_id = int(getattr(entity, "id"))
                    if source_id > 0:
                        source_id = int(f"-100{source_id}")

                if not str(source_id).startswith("-100"):
                    raise ValueError("• Source ID must start with -100")
            except Exception:
                await event.reply("• Invalid source channel/group. Make sure self account has access.")
                return

            raw_data = user.get("data")
            data_dict = json.loads(raw_data) if raw_data else {}
            data_dict["source"] = source_id

            user_manager.update_user(sender, step="panel2_dest", data=json.dumps(data_dict))
            await event.reply("✅ Now send destination numeric ID (must start with -100)")
            return

        if user["step"] == "panel2_dest":
            if not (text.startswith("-100") and text[4:].isdigit()):
                await event.reply("❌ Destination must start with -100")
                return

            raw_data = user.get("data")
            data_dict = json.loads(raw_data) if raw_data else {}
            data_dict["destination"] = int(text)

            user_manager.update_user(sender, step="panel2_confirm", data=json.dumps(data_dict))
            await event.reply(
                "Confirm registration:\n\n"
                f"Source: {data_dict['source']}\n"
                f"Destination: {data_dict['destination']}\n\n"
                "Type: yes / no"
            )
            return

        if user["step"] == "panel2_confirm":
            if lower_text == "yes":
                raw_data = user.get("data")
                data_dict = json.loads(raw_data) if raw_data else {}

                channel_manager.add_channel(
                    source_id=data_dict["source"],
                    dest_id=data_dict["destination"],
                )

                user_manager.update_user(sender, step="none", data=json.dumps({}))
                await event.reply("✅ Channel mapping registered successfully.")
                return

            if lower_text in {"no", ".panel", "/panel"}:
                user_manager.update_user(sender, step="none", data=json.dumps({}))
                await event.reply("💔 Registration cancelled.")
                return

            await event.reply("📍 Type yes or no")
            return

        if user["step"] == "panel4":
            if text.startswith("-100") and text[4:].isdigit():
                source_lookup = int(text)
            elif text.isdigit():
                source_lookup = int(f"-{text}")
            else:
                await event.reply("📍 Source ID must be numeric.")
                return

            existing = channel_manager.get_by_source(source_lookup)
            if existing:
                user_manager.update_user(sender, step="panel4_confirm", data=str(existing["id"]))
                await event.reply(
                    "⚠️ **Warning:** Are you sure you want to delete this mapping?\n\n"
                     f"• **Record ID:** {existing['id']}\n"
                     f"• **Source Channel:** {existing['source_channel_id']}\n"
                     f"• **Destination Channel:** {existing['destination_channel_id']}\n\n"
                     "✅ Type `yes` to confirm / ❌ Type `no` to cancel"
                )
                return

            await event.reply("❌ No mapping found for this source ID.")
            return

        if user["step"] == "panel4_confirm":
            if lower_text == "yes":
                channel_manager.delete_channel(int(user["data"]))
                user_manager.update_user(sender, step="none", data=json.dumps({}))
                await event.reply("✅ Mapping deleted successfully.")
                return

            if lower_text in {"no", ".panel", "/panel"}:
                user_manager.update_user(sender, step="none", data=json.dumps({}))
                await event.reply("• Operation cancelled.")
                return

            await event.reply("📍 Type yes or no")
            return

    @bot.on(events.InlineQuery)
    async def inline_handler(event: events.InlineQuery.Event):
        if event.sender_id != SELF_USER_ID:
            await event.answer([], cache_time=0)
            return

        q = (event.text or "").strip().lower()
        if q in ("panel", ""):
            user_manager.update_user(event.sender_id, step="none")
            result = event.builder.article(
                title="Self Admin Panel",
                description="Admin panel for owner only",
                text="🍓 **Welcome to the NPVT(AUTOPOST) Admin Panel!**\n\nTap the buttons below to manage everything like a pro",
                buttons=MAIN_MENU_BTN,
            )
            await event.answer([result], cache_time=0)

    @bot.on(events.CallbackQuery)
    async def callback_handler(event: events.CallbackQuery.Event):
        sender = event.sender_id
        data = event.data.decode() if event.data else ""

        if not is_owner(sender):
            return

        user = user_manager.ensure_user(sender, "none")

        if data == "acc_info":
            me = await user_client.get_me()
            info_text = (
                "👤 **Self Account Information**\n\n"
                f"• **Name:** {me.first_name}\n"
                f"• **ID:** `{me.id}`\n"
                f"• **Username:** @{me.username if me.username else 'Not set'}"
            )
            buttons = [[Button.inline("🔙 Back to Menu", b"main_menu")]]
            try:
                await event.edit(info_text, buttons=buttons)
            except Exception:
                await safe_answer_callback(event, info_text, alert=True)

        elif data == "script_info":
            developers = [
                {"name": "Hojjat Jahanpour", "github": "https://github.com/hojjatjh"},
                {"name": "Anita Bagheri", "github": "https://github.com/anitabg00"},
            ]

            dev_text  = "\n".join([f"👤 {dev['name']} — [GitHub]({dev['github']})" for dev in developers])
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

        elif data == "channel_management":
            text = "📣 You can manage your channels in this section\n\n⌨️ Use the menu below to manage"
            try:
                await event.edit(text, buttons=CHANNEL_MANAGEMENT)
            except Exception:
                await safe_answer_callback(event, text, alert=True)

        elif data == "admin_stats":
            user_manager.update_user(sender, step="none", data=json.dumps({}))
            text = build_admin_stats_text()
            try:
                await event.edit(text, buttons=build_admin_stats_buttons())
            except Exception:
                await safe_answer_callback(event, text, alert=True)

        elif data == "admin_stats_refresh":
            text = build_admin_stats_text()
            try:
                await event.edit(text, buttons=build_admin_stats_buttons())
            except Exception:
                await safe_answer_callback(event, text, alert=True)

        elif data == "admin_reset_configs":
            user_manager.update_user(sender, step="reset_configs_confirm", data=json.dumps({}))
            await event.edit(
                "💣 **DANGER ZONE: Reset Configs Table** ⚠️\n\n"
                "This action will **permanently remove ALL transfer history** and **clear the duplicate cache**.\n\n"
                "📝 To confirm, type exactly in your self chat:\n"
                "`RESET CONFIGS`\n\n"
                "❌ Send `cancel` to abort this operation safely.",
                buttons=BACK_MENU_BTN,
            )

        elif data == "relay_settings":
            user_manager.update_user(sender, step="none", data=json.dumps({}))
            text = build_relay_settings_text()
            try:
                await event.edit(text, buttons=build_relay_settings_buttons())
            except Exception:
                await safe_answer_callback(event, text, alert=True)

        elif data == "relay_settings_show":
            text = build_relay_settings_text()
            try:
                await event.edit(text, buttons=build_relay_settings_buttons())
            except Exception:
                await safe_answer_callback(event, text, alert=True)

        elif data == "relay_set_caption":
            user_manager.update_user(sender, step="relay_caption", data=json.dumps({}))
            await event.edit(
                "✏️ **Send New Caption for Relayed Files**\n\n"
                "• Supports **Persian / English** and **multi-line text**.\n\n"
                "📌 Example:\n"
                "`سلام این کپشن هست\\n@hojjat_jh`\n\n"
                "❌ Type `cancel` to abort this action.",
                buttons=BACK_MENU_BTN,
            )

        elif data == "relay_set_rate_limit":
            user_manager.update_user(sender, step="relay_rate_limit", data=json.dumps({}))
            await event.edit(
                "• Send the new rate limit in **seconds** (number ≥ 1)",
                buttons=BACK_MENU_BTN,
            )

        elif data == "relay_set_file_prefix":
            user_manager.update_user(sender, step="relay_file_prefix", data=json.dumps({}))
            await event.edit(
                "📁 **Set New File Prefix**\n\n"
                "• Supports **Persian / English** characters.\n"
                "📌 Example:\n"
                "`Myfilename`\n"
                "➡ Resulting filename: `Myfilename (123).npvt`\n\n"
                "❌ Type `cancel` to abort this action.",
                buttons=BACK_MENU_BTN,
            )

        elif data == "relay_set_source_refresh":
            user_manager.update_user(sender, step="relay_source_refresh", data=json.dumps({}))
            await event.edit(
                "• Send source mapping refresh in seconds (integer >= 5).\n\nExample: 20\nType 'cancel' to abort.",
                buttons=BACK_MENU_BTN,
            )

        elif data == "relay_toggle_enabled":
            runtime = relay_settings_manager.get_runtime_settings()
            new_state = not bool(runtime["relay_enabled"])
            relay_settings_manager.set_relay_enabled(new_state)
            text = build_relay_settings_text()
            try:
                await event.edit(text, buttons=build_relay_settings_buttons())
            except Exception:
                await safe_answer_callback(event, text, alert=True)

        elif data == "relay_toggle_dedup":
            runtime = relay_settings_manager.get_runtime_settings()
            new_state = not bool(runtime["dedup_enabled"])
            relay_settings_manager.set_dedup_enabled(new_state)
            text = build_relay_settings_text()
            try:
                await event.edit(text, buttons=build_relay_settings_buttons())
            except Exception:
                await safe_answer_callback(event, text, alert=True)

        elif data == "channel_management_add":
            user_manager.update_user(sender, step="panel2", data=json.dumps({}))
            await event.edit(
                 "🔗 **Send Source Channel / Group**\n\n"
                "You can provide the source in one of the following formats:\n"
                "• `@username`\n"
                "• Public link\n"
                "• Numeric ID starting with `-100`\n\n"
                "💡 Make sure the bot has access to the source channel/group.",
                buttons=BACK_MENU_BTN,
            )

        elif data == "channel_management_del":
            user_manager.update_user(sender, step="panel4", data="")
            await event.edit(
                "🗑️ **Delete Source Channel Mapping**\n\n"
                "Send the **numeric ID** of the source channel you want to delete.\n\n"
                "❌ Type `cancel` to abort this action.",
                buttons=BACK_MENU_BTN,
            )

        elif data == "channel_management_help":
            help_text = (
                "📚 **Channel Management Guide**\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "➕ **Add Channel**\n"
                "──────────────────────\n"
                "🎯 **Purpose:**\n"
                "Register a source channel/group and link it to a destination channel for automatic operations.\n\n"
                "⚙️ **How It Works:**\n"
                "1️⃣ Send source channel/group:\n"
                "   • `@username`\n"
                "   • `https://t.me/...`\n"
                "   • Numeric ID starting with `-100`\n\n"
                "2️⃣ Send destination numeric ID\n"
                "   • Must start with `-100`\n\n"
                "3️⃣ Confirm information\n"
                "   • Type: `yes` or `no`\n\n"
                "✅ After Confirmation:\n"
                "• Numeric ID will be resolved automatically\n"
                "• Data securely saved in database\n"
                "• Channel pair becomes active\n\n"
                "⚠️ **Important Notes:**\n"
                "• You must have proper access to channels\n"
                "• Destination must always be numeric ID\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "📋 **Channel List**\n"
                "──────────────────────\n"
                "🎯 **Purpose:**\n"
                "View all registered channel pairs.\n\n"
                "📌 **Features:**\n"
                "• Preview first channels inside panel\n"
                "• Download full list as `.txt` file\n\n"
                "📊 **Displays:**\n"
                "• Record ID\n"
                "• Source Channel ID\n"
                "• Destination Channel ID\n\n"
                "🔒 **Security:**\n"
                "• Owner access only\n"
                "• Temporary files auto-deleted after sending\n"
            )
            await event.edit(help_text, buttons=BACK_MENU_BTN)

        elif data == "channel_management_list":
            user_manager.update_user(sender, step="panel1")
            channels = channel_manager.get_all_channels()

            if not channels:
                await event.edit("🔴 No source or destination registered.", buttons=BACK_MENU_BTN)
                return

            preview_channels = channels[:13]
            text = "📋 List of channels (first 13):\n\n"
            for ch in preview_channels:
                source_title = await resolve_channel_title(user_client, ch["source_channel_id"])
                text += f"• {source_title} ->\n {ch['destination_channel_id']}\n\n"

            buttons = [
                [Button.inline("📄 Show all (txt)", b"channel_list_all")],
                [Button.inline("🔙 Back to Menu", b"main_menu")],
            ]
            await event.edit(text, buttons=buttons)

        elif data == "channel_list_all":
            user_manager.update_user(sender, step="panel1")
            channels = channel_manager.get_all_channels()
            await event.edit("⏳ Processing... Please wait...")

            if not channels:
                await event.respond("🔴 No source/destination mappings registered.")
                return

            content = "NPVT channel mappings:\n\n"
            for ch in channels:
                content += f"ID: {ch['id']}\n"
                content += f"source_channel_id: {ch['source_channel_id']}\n"
                content += f"destination_channel_id: {ch['destination_channel_id']}\n"
                content += "-" * 32 + "\n"

            file_path = "channels_list.txt"
            try:
                with open(file_path, "w", encoding="utf-8") as file_obj:
                    file_obj.write(content)
                await bot.send_file(sender, file_path, caption="🤝 Complete list of channels")
            except Exception:
                await event.edit("Error sending file. Make sure self-bot chat is active.")
                return
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)

            await event.edit("✅ Channel list sent successfully.", buttons=BACK_MENU_BTN)

        elif data == "main_menu":
            main_text = "🍓 NPVT Helper Panel\n\nUse the buttons below."
            try:
                if user['step'] in ('none', 'not_set'):
                    await event.edit(main_text, buttons=MAIN_MENU_BTN)
                elif user['step'] in ('relay_caption', 'relay_rate_limit', 'relay_file_prefix', 'relay_source_refresh'):
                    user_manager.update_user(sender, step="none", data=json.dumps({}))
                    await event.edit(build_relay_settings_text(), buttons=build_relay_settings_buttons())
                elif user['step'] in ('reset_configs_confirm'):
                    user_manager.update_user(sender, step="none", data=json.dumps({}))
                    await event.edit(build_admin_stats_text(), buttons=build_admin_stats_buttons())
                else:
                    await event.edit(main_text, buttons=MAIN_MENU_BTN)
            except Exception:
                await safe_answer_callback(event, "Main panel", alert=True)

        else:
            await event.answer()

    return bot, (await bot.get_me()).username
