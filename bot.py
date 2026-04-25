import os
import sys
import asyncio
import logging
import time
import re
import json
import traceback
import io
import shlex
import httpx
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from pyrogram.errors import MessageNotModified
import yt_dlp

# --- GLOBALS ---
START_TIME = time.time()
current_process = None  
active_file_name = "None"
CONFIG_FILE = "config.json"
pending_tasks = {}    # Stores file info for the pre-download panel
awaiting_index = {}   # Tracks ForceReply for stream indexes

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
logger = logging.getLogger(__name__)

# --- DYNAMIC CONFIG ---
def load_config():
    if not os.path.exists(CONFIG_FILE):
        default = {
            "API_ID": 123456, "API_HASH": "hash", "BOT_TOKEN": "token",
            "OWNER_ID": 12345, "LOG_GROUP_ID": -100, "AUTHORIZED_USERS": [12345],
            "CRF": 28, "RESOLUTION": "720", "AUDIO_BITRATE": "128k", "PRESET": "medium"
        }
        with open(CONFIG_FILE, "w") as f: json.dump(default, f, indent=4)
        return default
    with open(CONFIG_FILE, "r") as f: return json.load(f)

config = load_config()

# --- CLIENTS ---
bot_app = Client("bot_session", api_id=config["API_ID"], api_hash=config["API_HASH"], bot_token=config["BOT_TOKEN"])
user_app = Client("user_session", api_id=config["API_ID"], api_hash=config["API_HASH"])
queue = asyncio.Queue()

# --- UTILS ---
def humanbytes(size):
    if not size: return "0 B"
    for unit in ['B','KB','MB','GB','TB']:
        if size < 1024: return f"{size:.2f} {unit}"
        size /= 1024

def time_formatter(ms):
    s, ms = divmod(int(ms), 1000)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def make_bar(percent):
    filled = int(percent / 5)
    return "●" * filled + "○" * (20 - filled)

async def progress_bar(current, total, ud_type, message, start_time, last_update):
    if time.time() - last_update[0] > 4:
        now = time.time()
        speed = current / (now - start_time) if (now - start_time) > 0 else 0
        eta = (total - current) / speed if speed > 0 else 0
        percent = (current / total) * 100
        text = f"**{ud_type}**\n`[{make_bar(percent)}] {percent:.1f}%`\n\n🚀 Speed: `{humanbytes(speed)}/s` | ETA: `{time_formatter(eta*1000)}`"
        try: await message.edit(text); last_update[0] = now
        except: pass

async def get_graph_link(text):
    # Posts MediaInfo to Graph.org (Telegraph)
    async with httpx.AsyncClient() as client:
        payload = {
            "title": "MediaInfo Details", "author_name": "Gemini Compressor",
            "content": [{"tag": "pre", "children": [text]}], "return_content": True
        }
        r = await client.post("https://api.telegra.ph/createPage", json=payload)
        return r.json().get("result", {}).get("url", "Failed to generate link")

# --- COMMANDS ---
@bot_app.on_message(filters.command("eval") & filters.user(config["OWNER_ID"]))
async def eval_handler(client, message):
    if len(message.text.split()) < 2: return
    cmd = message.text.split(maxsplit=1)[1]
    msg = await message.reply("Running...")
    try:
        # Simple dynamic execution logic
        exec(f"async def __ex(client, message): " + "".join(f"\n {l}" for l in cmd.split("\n")))
        result = await locals()["__ex"](client, message)
        await msg.edit(f"**Result:**\n`{result or 'Success'}`")
    except Exception as e: await msg.edit(f"**Error:**\n`{e}`")

@bot_app.on_message(filters.command("setvar") & filters.user(config["OWNER_ID"]))
async def setvar_cmd(client, message):
    try:
        _, k, v = message.text.split(maxsplit=2)
        config[k] = int(v) if v.isdigit() else v
        with open(CONFIG_FILE, "w") as f: json.dump(config, f, indent=4)
        await message.reply(f"✅ `{k}` updated. Restart to apply.")
    except: await message.reply("Usage: `/setvar CRF 26`")

@bot_app.on_message(filters.command("restart") & filters.user(config["OWNER_ID"]))
async def restart_cmd(client, message):
    await message.reply("🔄 Restarting..."); os.execl(sys.executable, sys.executable, *sys.argv)

# --- PANEL CALLBACKS ---
@bot_app.on_callback_query(filters.regex(r"^panel_(.*)"))
async def panel_handler(client, cb):
    action, tid = cb.data.split("_")[1:3]
    task = pending_tasks.get(tid)
    if not task: return await cb.answer("Task Expired", show_alert=True)

    if action == "info":
        await cb.message.edit("📝 Probing MediaInfo (No download)...")
        # Fast Probe: Download 2MB to temp
        chunk_path = f"probe_{tid}.mkv"
        await user_app.download_media(task['msg'], file_name=chunk_path, limit=1) # 1 chunk = ~1-2MB
        info = os.popen(f"mediainfo {chunk_path}").read()
        os.remove(chunk_path)
        link = await get_graph_link(info)
        await cb.message.edit(f"📊 **MediaInfo Link:** {link}", disable_web_page_preview=True)

    elif action == "all":
        await queue.put((task['msg'], task['name'], ["-map", "0"], cb.message))
        await cb.message.edit(f"✅ Added to Queue (All Tracks).\n`{task['name']}`")

    elif action == "select":
        await cb.message.edit("⏳ Fetching Stream List...")
        chunk_path = f"probe_{tid}.mkv"
        await user_app.download_media(task['msg'], file_name=chunk_path, limit=1)
        streams = os.popen(f"ffprobe -v error -show_entries stream=index,codec_type,codec_name:stream_tags=language -of json {chunk_path}").read()
        os.remove(chunk_path)
        data = json.loads(streams).get("streams", [])
        txt = "**Available Streams:**\n"
        for s in data:
            txt += f"Index `{s['index']}`: {s['codec_type'].upper()} ({s.get('tags',{}).get('language','und')})\n"
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("✍️ Input Indexes", callback_data=f"panel_input_{tid}")]])
        await cb.message.edit(txt, reply_markup=btn)

    elif action == "input":
        await awaiting_index.update({cb.message.chat.id: tid})
        await cb.message.delete()
        await bot_app.send_message(cb.message.chat.id, "Reply with indexes (e.g. 0,2,4):", reply_markup=ForceReply(selective=True))

# --- INDEX REPLY HANDLER ---
@bot_app.on_message(filters.reply & filters.user(config["AUTHORIZED_USERS"]))
async def index_receiver(client, message):
    tid = awaiting_index.pop(message.chat.id, None)
    if tid and tid in pending_tasks:
        task = pending_tasks.pop(tid)
        map_args = []
        for idx in message.text.split(','): map_args.extend(["-map", f"0:{idx.strip()}"])
        await queue.put((task['msg'], task['name'], map_args, message))
        await message.reply(f"✅ Success! `{task['name']}` queued with custom streams.")

# --- FFMPEG WORKER ---
async def worker():
    while True:
        msg, name, map_args, status_msg = await queue.get()
        try:
            # Step 1: Full Download (User Session)
            start_time = time.time()
            last_up = [time.time()]
            await status_msg.edit("📥 **Downloading Full File...**")
            file_path = await user_app.download_media(msg, progress=progress_bar, progress_args=("Downloading", status_msg, start_time, last_up))
            
            # Step 2: Compress
            base = name.replace(" ", ".").rsplit(".", 1)[0]
            out = f"{base}.Compressed.mkv"
            await status_msg.edit(f"⚙️ **Compressing:** `{name}`")
            
            cmd = ["ffmpeg", "-i", file_path] + map_args + [
                "-c:v", "libx265", "-crf", str(config["CRF"]), "-preset", config["PRESET"],
                "-vf", f"scale=-2:{config['RESOLUTION']}", "-c:a", "libopus", "-b:a", config["AUDIO_BITRATE"],
                "-y", out
            ]
            process = await asyncio.create_subprocess_exec(*cmd, stderr=asyncio.subprocess.PIPE)
            await process.wait()
            
            # Step 3: Upload Document
            await user_app.send_document(msg.chat.id, out, caption=f"✅ {out}", force_document=True)
            await status_msg.edit("✅ Done!")
            os.remove(file_path); os.remove(out)
        except Exception as e: logger.error(e)
        finally: queue.task_done()

# --- MAIN HANDLER ---
@user_app.on_message((filters.video | filters.document) & filters.user(config["AUTHORIZED_USERS"]))
async def incoming_file(client, message):
    tid = str(message.id)
    name = (message.video or message.document).file_name or "video.mp4"
    pending_tasks[tid] = {"msg": message, "name": name}
    
    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 MediaInfo", callback_data=f"panel_info_{tid}"), InlineKeyboardButton("✂️ Stream Select", callback_data=f"panel_select_{tid}")],
        [InlineKeyboardButton("▶️ Compress All", callback_data=f"panel_all_{tid}")]
    ])
    await bot_app.send_message(message.chat.id, f"📥 **File Received:** `{name}`\nChoose an action:", reply_markup=btn)

# --- START ---
async def start_hybrid():
    await bot_app.start(); await user_app.start()
    asyncio.create_task(worker())
    await idle()

if __name__ == "__main__":
    loop = asyncio.get_event_loop(); loop.run_until_complete(start_hybrid())