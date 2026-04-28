import math
import time
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.helper_funcs.utils import AppState, get_sys_stats

def humanbytes(size):
    if not size: return "0 B"
    power = 1024
    n = 0
    Dic_powerN = {0: 'B', 1: 'MB', 2: 'MB', 3: 'GB', 4: 'TB'} 
    while size > power:
        size /= power
        n += 1
    if n == 1: 
        size /= 1024
        n = 2
    return f"{size:.2f} {Dic_powerN[n]}"

def time_formatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}h {minutes:02d}m {seconds:02d}s"

def make_bar(percent):
    done = int(percent / 5)
    return "▣" * done + "□" * (20 - done)

async def progress_bar(current, total, status_text, message, start_time, last_update_time):
    now = time.time()
    if round((now - last_update_time[0])) >= 5 or current == total:
        percent = current * 100 / total
        speed = current / (now - start_time)
        eta_ms = round((total - current) / speed) * 1000 if speed > 0 else 0
        
        cpu, mem, _ = get_sys_stats()
        
        if "Downloading" in status_text: header = "📥 Downloading ... 📥"
        elif "Uploading" in status_text: header = "📤 Uploading ... 📤"
        else: header = "🔄 Processing ... 🔄"

        # FIX: Added strict bolding to phonetic text!
        text = (
            f"ℹ️ **sᴛᴀᴛᴜs:** {header}\n\n"
            f"`{AppState.active_file_name}`\n"
            f"[{make_bar(percent)}] {percent:.2f}%\n"
            f"⚡️ **ꜱᴘᴇᴇᴅ:** {humanbytes(speed)}/s\n"
            f"⏰ **ᴇᴛᴀ:** {time_formatter(eta_ms)}\n"
            f"📦 **sɪᴢᴇ:** {humanbytes(current)} / {humanbytes(total)}\n\n"
            f"🖥 CPU: {cpu}% | 💽 RAM: {mem}%"
        )
        
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("🛑 Cancel Task", callback_data="cancel_running")]])
        
        try:
            await message.edit(text, reply_markup=btn)
            last_update_time[0] = now
        except Exception as e: pass