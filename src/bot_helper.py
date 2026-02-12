import os
import json
from telethon import TelegramClient, events, Button
from src.utilities import is_owner, safe_answer_callback
from src.orm import SimpleORM
from src.config import VERSION, load_settings
from src.controllers import ChannelManager,UserManager
from src.buttons import *

settings = load_settings()
orm      = SimpleORM.from_settings(settings)

# USE CONTROLLERS
user_manager    = UserManager(orm)
channel_manager = ChannelManager(orm)

# BOT HELPER
async def start_helper_bot(user_client: TelegramClient, BOT_SESSION: str, API_ID: int, API_HASH: str, BOT_TOKEN: str, SELF_USER_ID: int):
    self = user_client
    bot  = TelegramClient(BOT_SESSION, API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)

    # ======================================== [ NewMessage ]
    @self.on(events.NewMessage)
    async def message_handler(event):
        sender = event.sender_id
    
        if not is_owner(sender):
            return
    
        user = user_manager.ensure_user(sender, "none")
        text = (event.text or "").strip()

        if text == '.panel':
            user_manager.update_user(sender, step="none")
            return
    
        # ================= STEP 1 : panel2 =================
        if user["step"] == "panel2":
            try:
                entity = await self.get_entity(text)
                source_id = entity.id

                if hasattr(entity, "megagroup") or hasattr(entity, "broadcast"):
                    source_id = int(f"-100{source_id}")

            except Exception as e:
                await event.reply("❌ Invalid channel/group. Make sure the self account is a member.")
                return

            raw_data  = user.get("data")
            data_dict = json.loads(raw_data) if raw_data else {}

            data_dict["source"] = source_id

            user_manager.update_user(
                sender,
                step="panel2_dest",
                data=json.dumps(data_dict)
            )

            await event.reply("📤 Now send destination channel numeric ID (must start with -100)")
            return
    
        # ================= STEP 2 : panel2 =================
        if user["step"] == "panel2_dest":
        
            if not text.startswith("-100"):
                await event.reply("❌ Destination must start with -100")
                return
    
            raw_data = user.get("data")
            if raw_data:
                data_dict = json.loads(raw_data)
            else:
                data_dict = {}

            data_dict["destination"] = text
    
            user_manager.update_user(sender, step="panel2_confirm", data=json.dumps(data_dict))
    
            await event.reply(
                f"⚠️ Confirm registration:\n\n"
                f"Source: {data_dict['source']}\n"
                f"Destination: {data_dict['destination']}\n\n"
                f"Type: yes / no"
            )
            return
    
        # ================= STEP 3 : panel2 =================
        if user["step"] == "panel2_confirm":    
            if text.lower() == "yes":     
                raw_data = user.get("data")
                if raw_data:
                    data_dict = json.loads(raw_data)
                else:
                    data_dict = {}

                channel_manager.add_channel(
                    source_id=data_dict["source"],
                    dest_id=data_dict["destination"]
                )
    
                user_manager.update_user(sender, step="none", data=json.dumps({}))
                await event.reply("✅ Channel registered successfully.")
                return
    
            elif text.lower() == "no":
                user_manager.update_user(sender, step="none", data=json.dumps({}))
                await event.reply("❌ Registration cancelled.")
                return
    
            elif text.lower() == ".panel" or  text.lower() == "/panel":
                user_manager.update_user(sender, step="none", data=json.dumps({}))
                await event.reply("❌ Registration cancelled.")
                return

            else:
                await event.reply("Type yes or no")
                return

        # ================= STEP 1 : panel4 =================
        if user["step"] == "panel4":
            if not text.isdigit():
                await event.reply("💩 The channel ID sent for deletion must be a numeric ID.")
                return
            
            existing = channel_manager.get_by_source(f"-{text}")
            if existing:
                user_manager.update_user(sender, step="panel4_confirm", data=f"{existing['id']}")
                await event.reply(f"🚨 Important Warning\n\nDo you want to completely delete the destination channel with numeric ID ( {existing['id']} )?\nWrite: Yes or No")
                return
            else:
                await event.reply(f"📍 No destination channel with the same ID was found.")
                return

        # ================= STEP 2 : panel4 =================
        if user["step"] == "panel4_confirm":
            if text.lower() == "yes":     
                channel_manager.delete_channel(user["data"])
                user_manager.update_user(sender, step="none", data=json.dumps({}))
                await event.reply("✅ Relationship with success removed")
                return
    
            elif text.lower() == "no":
                user_manager.update_user(sender, step="none", data=json.dumps({}))
                await event.reply("❌ Operation successfully canceled.")
                return
    
            elif text.lower() == ".panel" or  text.lower() == "/panel":
                user_manager.update_user(sender, step="none", data=json.dumps({}))
                await event.reply("❌ Operation successfully canceled.")
                return

            else:
                await event.reply("× Type yes or no")
                return

    # ======================================== [ InlineQuery ]
    @bot.on(events.InlineQuery)
    async def inline_handler(event: events.InlineQuery.Event):
        if event.sender_id != SELF_USER_ID:
            await event.answer([], cache_time=0)
            return

        q = (event.text or '').strip().lower()
        if q in ('panel', ''):
            user_manager.update_user(event.sender_id, step="none")
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

            try:
                await event.edit(text, buttons=CHANNEL_MANAGEMENT)
            except:
                await safe_answer_callback(event, info_text, alert=True)

        # ---------------- CHANNEL MANAGEMENT [add] ----------------
        elif data == 'channel_management_add':
            user_manager.update_user(sender, step="panel2", data=json.dumps({}))
            await event.edit(
                "📥 Send source channel/group:\n\n"
                "• Username: @example\n"
                "• Or numeric ID starting with -100\n"
                "• Or public link",
                buttons=BACK_MENU_BTN
            )

        # ---------------- CHANNEL MANAGEMENT [del] ----------------
        elif data == 'channel_management_del':
            user_manager.update_user(sender, step="panel4", data='')
            await event.edit(
                "• To delete a channel connection (source and destination)\n\nPlease enter the source channel's numeric ID without the -",
                buttons=BACK_MENU_BTN
            )

        # ---------------- CHANNEL MANAGEMENT [help] ----------------
        elif data == 'channel_management_help':
            user_manager.update_user(sender, step="panel2", data=json.dumps({}))
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

        # ---------------- CHANNEL MANAGEMENT [list] ----------------
        elif data == 'channel_management_list':
            user_manager.update_user(sender, step="panel1")
            channels = channel_manager.get_all_channels()

            if not channels:
                await event.edit("🔴 No source or destination registered.", buttons=BACK_MENU_BTN)
                return
        
            preview_channels = channels[:13]
            text             = "📋 List of channels (first 13):\n\n"
        
            for ch in preview_channels:
                text += f"• {ch['source_channel_id']}\n"
                text += f"  ➜ To: {ch['destination_channel_id']}\n\n"

            buttons = [
                [Button.inline("📄 Show all (txt)", b"channel_list_all")],
                [Button.inline('🔙 Return to main menu', b'main_menu')]
            ]

            await event.edit(text, buttons=buttons)

        # ---------------- CHANNEL MANAGEMENT [list (txt)] ----------------
        elif data == 'channel_list_all':
            user_manager.update_user(sender, step="panel1")
            channels = channel_manager.get_all_channels()
            await event.edit("⏳ Processing... Please wait...")

            if not channels:
                await event.respond("🔴 No source or destination registered.")
                return

            content = "🍓Powerful Strawberry Script \n📋 Full list of channels: \n\n"

            for ch in channels:
                content += f"ID: {ch['id']}\n"
                content += f"source_channel_id: {ch['source_channel_id']}\n"
                content += f"destination_channel_id: {ch['destination_channel_id']}\n"
                content += "-"*30 + "\n"

            file_path = "channels_list.txt"

            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                await bot.send_file(sender, file_path, caption="🍓 Complete list of channels:")
            except:
                await event.edit("❌ Error communicating with user (please start the self-bot to send the file)")
                return
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)

            await event.edit(
                "📋 Channel list sent successfully.",
                buttons=BACK_MENU_BTN
            )

        # ---------------- MAIN MENU ----------------
        elif data == 'main_menu':
            main_text = '🍓 **Your own self-management panel** \n\n'
            buttons   = MAIN_MENU_BTN
            try:
                if user['step'] in ('none', 'not_set'):
                    user_manager.update_user(sender, step="none")
                    await event.edit(main_text, buttons=buttons)
                elif user['step'] in ('panel1', 'panel2', 'panel3', 'panel4'):
                    user_manager.update_user(sender, step="none")
                    await event.edit(main_text, buttons=CHANNEL_MANAGEMENT)
                else:
                    await event.edit(main_text, buttons=buttons)
            except:
                await safe_answer_callback(event, 'Main panel', alert=True)
        
        # else for not found data
        else:
            await event.answer()

    return bot, (await bot.get_me()).username