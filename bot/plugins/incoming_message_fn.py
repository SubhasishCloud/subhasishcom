from pyrogram import filters
from pyrogram.enums import ChatType
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.__init__ import bot_app, user_app, config_data
from bot.helper_funcs.utils import AppState, queue

UNAUTH_MSG = "<b>Opps You Need To Donate Some Amount To Use Meh...🐸👀</b>"
QUEUE_MSG = "<b>Added To Queue... 🚦</b>\n<b>Please Be Patient, Your Compression Will Start Soon... 😊</b>"

def is_sudo(user_id):
    return user_id in config_data["AUTH_USERS"] or user_id == config_data["OWNER_ID"]

@user_app.on_message((filters.video | filters.document))
async def incoming_file(client, message):
    user_id = message.from_user.id if message.from_user else 0
    
    # Check Authorization
    if not is_sudo(user_id):
        if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
            return await bot_app.send_message(message.chat.id, UNAUTH_MSG, reply_to_message_id=message.id)
        else:
            return await message.reply(UNAUTH_MSG)

    # --- MIME-TYPE ARMOR ---
    if message.document:
        mime = message.document.mime_type or ""
        if not mime.startswith("video/"):
            ext = (message.document.file_name or "").split(".")[-1].lower()
            if ext not in ["mp4", "mkv", "avi", "webm", "flv", "mov"]:
                return await message.reply("⚠️ **Invalid File:** Please send a valid video file.", quote=True)

    tid = str(message.id)
    name = (message.video or message.document).file_name or "video.mp4"
    AppState.pending_tasks[tid] = {"msg": message, "name": name}
    
    # --- UX UPGRADE: Renamed Compress All to Compress (Default) ---
    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 MediaInfo", callback_data=f"panel_info_{tid}"), InlineKeyboardButton("✂️ Stream Select", callback_data=f"panel_select_{tid}")],
        [InlineKeyboardButton("▶️ Compress (Default)", callback_data=f"panel_all_{tid}")]
    ])
    
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await bot_app.send_message(message.chat.id, f"📥 **File Received:** `{name}`\nChoose an action:", reply_to_message_id=message.id, reply_markup=btn)
    else:
        await message.reply(f"📥 **File Received:** `{name}`\nChoose an action:", reply_markup=btn)


@bot_app.on_message(filters.reply)
async def index_receiver(client, message):
    user_id = message.from_user.id if message.from_user else 0
    if not is_sudo(user_id): return
    
    tid = AppState.awaiting_index.pop(message.chat.id, None)
    if tid and tid in AppState.pending_tasks:
        task = AppState.pending_tasks.pop(tid)
        map_args = []
        for idx in message.text.split(','): map_args.extend(["-map", f"0:{idx.strip()}"])
        
        await queue.put((task['msg'], task['name'], map_args, message))
        await message.reply(QUEUE_MSG)