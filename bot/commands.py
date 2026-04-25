import os
import sys
import io
import time
import json
import random
import asyncio
import traceback
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.__init__ import bot_app, user_app, config_data
from bot.config import Config
from bot.localisation import Localisation
from bot.helper_funcs.utils import AppState, queue, START_TIME, get_readable_time
from bot.helper_funcs.download import get_graph_link

# --- AUTHORIZATION SETTINGS ---
SUDO_USERS = config_data["AUTH_USERS"] + [config_data["OWNER_ID"]]
UNAUTH_MSG = "<b>Opps You Need To Donate Some Amount To Use Meh...🐸👀</b>"

def is_sudo(message):
    user_id = message.from_user.id if message.from_user else 0
    return user_id in config_data["AUTH_USERS"] or user_id == config_data["OWNER_ID"]

def is_owner(message):
    user_id = message.from_user.id if message.from_user else 0
    return user_id == config_data["OWNER_ID"]

def get_uptime():
    uptime_ms = int((time.time() - START_TIME) * 1000)
    return get_readable_time(uptime_ms)


# ==========================================
# 🟢 PUBLIC COMMANDS (Open to Everyone)
# ==========================================

@bot_app.on_message(filters.command("start"))
async def start_cmd(client, message): 
    await message.reply(Localisation.START_TEXT)

@bot_app.on_message(filters.command("help"))
async def help_cmd(client, message): 
    await message.reply(Localisation.HELP_TEXT)

@bot_app.on_message(filters.command("ping"))
async def ping_cmd(client, message):
    start_t = time.time()
    msg = await message.reply("...")
    end_t = time.time()
    ping_ms = round((end_t - start_t) * 1000)
    await msg.edit(f"📶Pɪɴɢ = {ping_ms}ms\n⏰ **Uptime:** `{get_uptime()}`")

@bot_app.on_message(filters.command("clear"))
async def clear_cmd(client, message):
    if not is_sudo(message): 
        return await message.reply(UNAUTH_MSG)
    while not queue.empty():
        queue.get_nowait()
        queue.task_done()
    await message.reply(Localisation.QUEUE_CLEARED)

@bot_app.on_message(filters.command("settings"))
async def settings_cmd(client, message):
    text = (
        "⚠️ **Current Ffmpeg Code Settings**\n"
        "The current settings will be added to your video file :\n\n"
        f"**Codec :** `{config_data['CODEC']}`\n"
        f"**Crf :** `{config_data['CRF']}`\n"
        f"**Resolution :** `{config_data['RESOLUTION']}`\n"
        f"**Preset :** `{config_data['PRESET']}`\n"
        f"**Audio Bitrates :** `{config_data['AUDIO_BITRATE']}`"
    )
    await message.reply(text)


# ==========================================
# 🔴 SUDO COMMANDS (Restricted to Auth Users)
# ==========================================

async def update_setting(message, key, display_name):
    if not is_sudo(message): 
        return await message.reply(UNAUTH_MSG)
        
    if len(message.command) < 2: 
        return await message.reply(f"Current {display_name}: `{config_data[key]}`")
        
    val = message.command[1]
    
    if str(config_data[key]) == str(val): 
        return await message.reply(f"⚠️ {display_name} is already set to `{val}`")
        
    config_data[key] = val
    Config.save_config(config_data)
    await message.reply(f"✅ {display_name} successfully updated to `{val}`.")

@bot_app.on_message(filters.command("preset"))
async def preset_cmd(client, message): 
    await update_setting(message, "PRESET", "preset")

@bot_app.on_message(filters.command("crf"))
async def crf_cmd(client, message): 
    await update_setting(message, "CRF", "crf")

@bot_app.on_message(filters.command("audio"))
async def audio_cmd(client, message): 
    await update_setting(message, "AUDIO_BITRATE", "audio_bitrate")

@bot_app.on_message(filters.command("resolution"))
async def res_cmd(client, message): 
    await update_setting(message, "RESOLUTION", "resolution")

@bot_app.on_message(filters.command("codec"))
async def codec_cmd(client, message): 
    await update_setting(message, "CODEC", "codec")

@bot_app.on_message(filters.command(["cancel", "stop"]))
async def cancel_cmd(client, message):
    if not is_sudo(message): 
        return await message.reply(UNAUTH_MSG)
    if not AppState.current_process: 
        return await message.reply(Localisation.NO_ACTIVE_TASK)
        
    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("Yes✅", callback_data="confirm_cancel_yes"), 
         InlineKeyboardButton("No ❌", callback_data="confirm_cancel_no")]
    ])
    await message.reply(Localisation.CANCEL_PROMPT, reply_markup=btn, quote=True)

@bot_app.on_message(filters.command("cancelall"))
async def cancel_all_cmd(client, message):
    if not is_sudo(message): 
        return await message.reply(UNAUTH_MSG)
        
    while not queue.empty():
        queue.get_nowait()
        queue.task_done()
        
    if AppState.current_process:
        AppState.current_process.terminate()
        AppState.current_process = None
        
    await message.reply("⚠️ **ALL TASKS CANCELLED AND QUEUE CLEARED.**")

@bot_app.on_message(filters.command("log"))
async def log_cmd(client, message):
    if not is_sudo(message): 
        return await message.reply(UNAUTH_MSG)
        
    msg = await message.reply("⏳ Fetching bot logs...")
    try:
        with open("bot.log", "r") as f: 
            log_data = f.read()[-30000:] 
        if not log_data: 
            return await msg.edit("⚠️ Log file is empty.")
            
        link = await get_graph_link(log_data, "Subhasish Encoder Logs", "Subhasish Encoder")
        await msg.edit(f"📝 **Bot Logs:**\n{link}", disable_web_page_preview=True)
    except Exception as e: 
        await msg.edit(f"❌ Failed to fetch logs: {e}")

@bot_app.on_message(filters.command("mediainfo"))
async def mediainfo_cmd(client, message):
    if not is_sudo(message): 
        return await message.reply(UNAUTH_MSG)
        
    if not message.reply_to_message or not (message.reply_to_message.video or message.reply_to_message.document):
        return await message.reply("⚠️ Reply to a video or document to get its MediaInfo.")
        
    msg = await message.reply("📝 Probing MediaInfo (Downloading 2MB chunk)...")
    tid = str(message.id)
    chunk_path = f"probe_{tid}.mkv"
    
    try:
        await user_app.download_media(message.reply_to_message, file_name=chunk_path, limit=1)
        raw_info = os.popen(f"mediainfo {chunk_path}").read()
        
        formatted_info = raw_info.replace("General\n", "📄 General\n").replace("Video\n", "🎬 Video\n").replace("Audio\n", "🔊 Audio\n").replace("Text\n", "💬 Subtitle\n").replace("Menu\n", "📑 Menu\n")
        os.remove(chunk_path)
        
        link = await get_graph_link(formatted_info, "Subhasish Encoder Mediainfo", "Subhasish Encoder")
        await msg.edit(f"📊 **MediaInfo Link:**\n{link}", disable_web_page_preview=True)
    except Exception as e:
        await msg.edit(f"❌ Error: {e}")
        if os.path.exists(chunk_path): os.remove(chunk_path)

@bot_app.on_message(filters.command("setthumbnail"))
async def set_thumb(client, message):
    if not is_sudo(message): 
        return await message.reply(UNAUTH_MSG)
        
    if not message.reply_to_message or not message.reply_to_message.photo: 
        return await message.reply(Localisation.INVALID_THUMB)
        
    path = os.path.join(Config.THUMB_DIR, f"{message.from_user.id}.jpg")
    await message.reply_to_message.download(file_name=path)
    await message.reply(Localisation.THUMB_ADDED)

@bot_app.on_message(filters.command("delthumbnail"))
async def del_thumb_cmd(client, message):
    if not is_sudo(message): 
        return await message.reply(UNAUTH_MSG)
        
    path = os.path.join(Config.THUMB_DIR, f"{message.from_user.id}.jpg")
    if not os.path.exists(path): 
        return await message.reply("⚠️ You don't have a custom thumbnail set.")
        
    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("Yes✅", callback_data="delthumb_yes"), 
         InlineKeyboardButton("No ❌", callback_data="delthumb_no")]
    ])
    await message.reply(Localisation.THUMB_WARNING, reply_markup=btn)

# --- NEW HIJACKED FEATURE: RANDOM 30 SEC SAMPLE GENERATOR ---
async def generate_sample_background(client, target_message, status_msg):
    try:
        # Step 1: Download Media (Max 4GB limit handled by user_app)
        await status_msg.edit(Localisation.DOWNLOAD_START)
        file_path = await user_app.download_media(target_message)
        
        if not file_path or not os.path.exists(file_path):
            return await status_msg.edit(Localisation.FILE_NOT_FOUND)

        await status_msg.edit(Localisation.SAMPLE_GENERATING)

        # Step 2: Get Duration
        duration_cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 '{file_path}'"
        duration_output = os.popen(duration_cmd).read().strip()
        
        try:
            total_duration = float(duration_output)
        except:
            total_duration = 0
            
        if total_duration < 35:
            os.remove(file_path)
            return await status_msg.edit("⚠️ Video is too short to generate a 30-second sample.")

        # Step 3: Pick a Random Start Time (avoiding the very beginning and very end)
        start_time = random.uniform(10, total_duration - 35)
        
        # Step 4: Cut exactly 30 seconds using Fast Seek
        sample_out = f"Sample_{int(time.time())}.mkv"
        cut_cmd = [
            "ffmpeg", "-ss", str(start_time), "-i", file_path, 
            "-t", "30", "-c", "copy", "-y", sample_out
        ]
        
        process = await asyncio.create_subprocess_exec(*cut_cmd)
        await process.communicate()

        if not os.path.exists(sample_out):
            os.remove(file_path)
            return await status_msg.edit("⚠️ Failed to generate sample.")

        # Step 5: Upload the Sample
        await status_msg.edit(Localisation.UPLOAD_START)
        caption = f"🎞 **Random 30s Sample**\n⏱ Cut from: `{time.strftime('%H:%M:%S', time.gmtime(start_time))}`\n\n<b>©ᴇɴᴄᴏᴅᴇᴅ Bʏ:</b> <b>@{AppState.bot_username}</b>"
        
        await client.send_document(
            chat_id=status_msg.chat.id, 
            document=sample_out, 
            caption=caption,
            force_document=True,
            reply_to_message_id=target_message.id
        )
        
        await status_msg.delete()
        os.remove(file_path)
        os.remove(sample_out)
        
    except Exception as e:
        await status_msg.edit(f"❌ Sample Generation Error: {e}")
        if 'file_path' in locals() and os.path.exists(file_path): os.remove(file_path)
        if 'sample_out' in locals() and os.path.exists(sample_out): os.remove(sample_out)

@bot_app.on_message(filters.command("samplegen"))
async def samplegen_cmd(client, message):
    if not is_sudo(message): 
        return await message.reply(UNAUTH_MSG)
        
    if AppState.current_process or not queue.empty():
        return await message.reply(Localisation.SAMPLE_BUSY)
        
    if not message.reply_to_message or not (message.reply_to_message.video or message.reply_to_message.document):
        return await message.reply("⚠️ Please reply to a video or document to generate a sample.")
        
    msg = await message.reply("⏳ **Initializing Random Sample Generator...**")
    
    # Run the generation process in the background so it doesn't freeze the bot
    asyncio.create_task(generate_sample_background(client, message.reply_to_message, msg))


# ==========================================
# 👑 OWNER ONLY COMMANDS (Strict Restriction)
# ==========================================

@bot_app.on_message(filters.command("setvar"))
async def setvar_cmd(client, message):
    if not is_owner(message): 
        return await message.reply(UNAUTH_MSG)
    
    help_text = (
        "**⚙️ How to use /setvar**\n"
        "Use this to instantly change bot settings without Putty.\n\n"
        "**Usage:** `/setvar <VARIABLE_NAME> <VALUE>`\n\n"
        "**Available Variables:**\n"
        "• `LOG_CHANNEL` : Target group for logs (e.g., `-100123456789`)\n"
        "• `AUTH_USERS` : Array of IDs (e.g., `[123456, 987654]`)\n"
        "• `USER_SESSION_STRING` : Your Pyrogram Session String\n"
        "• `CRF` : (e.g., `28`)\n"
        "• `PRESET` : (e.g., `fast`)\n"
        "• `RESOLUTION` : (e.g., `820x480`)\n"
        "• `AUDIO_BITRATE` : (e.g., `96k`)\n"
        "• `CODEC` : (e.g., `libx265`)\n\n"
        "*After changing a variable, type /restart to apply!*"
    )
    
    try:
        if len(message.command) < 3:
            return await message.reply(help_text)
            
        _, k, v = message.text.split(maxsplit=2)
        
        if k in ["AUTH_USERS"]: 
            v = json.loads(v) 
        elif v.isdigit() and k not in ["USER_SESSION_STRING"]: 
            v = int(v)
        
        config_data[k] = v
        Config.save_config(config_data)
        await message.reply(f"✅ `{k}` updated to `{v}`.\n⚠️ **Type /restart to apply.**")
    except Exception as e: 
        await message.reply(f"❌ **Error formatting variable:**\n{e}\n\n{help_text}")

async def aexec(code, client, message):
    exec(f"async def __aexec(client, message): " + "".join(f"\n {l}" for l in code.split("\n")))
    return await locals()["__aexec"](client, message)

@bot_app.on_message(filters.command(["eval", "exec"]))
async def eval_handler(client, message):
    if not is_owner(message): 
        return await message.reply(UNAUTH_MSG)
        
    if len(message.text.split()) < 2: return
    
    cmd = message.text.split(maxsplit=1)[1]
    msg = await message.reply("Processing...")
    
    old_stderr = sys.stderr
    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()
    redirected_error = sys.stderr = io.StringIO()
    stdout, stderr, exc = None, None, None

    try:
        await aexec(cmd, client, message)
    except Exception:
        exc = traceback.format_exc()

    stdout = redirected_output.getvalue()
    stderr = redirected_error.getvalue()
    sys.stdout = old_stdout
    sys.stderr = old_stderr

    evaluation = exc or stderr or stdout or "Success"
    
    final_output = f"<b>EVAL</b>: <code>{cmd}</code>\n\n<b>OUTPUT</b>:\n<code>{evaluation.strip()}</code>\n"

    if len(final_output) > 4000:
        with open("eval.txt", "w+", encoding="utf8") as out_file:
            out_file.write(str(final_output))
        await message.reply_document(
            document="eval.txt",
            caption=cmd[:100],
            disable_notification=True
        )
        os.remove("eval.txt")
        await msg.delete()
    else:
        await msg.edit(final_output)

@bot_app.on_message(filters.command("restart"))
async def restart_cmd(client, message):
    if not is_owner(message): 
        return await message.reply(UNAUTH_MSG)
        
    msg = await message.reply("🔄 **Restarting the server now...**")
    
    with open("restart.json", "w") as f:
        json.dump({"chat_id": msg.chat.id, "message_id": msg.id}, f)
        
    os.execl(sys.executable, sys.executable, *sys.argv)