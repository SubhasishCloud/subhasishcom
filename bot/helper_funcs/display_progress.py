import time
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.helper_funcs.utils import AppState, get_sys_stats, queue, get_network_io, get_readable_time

def humanbytes(size):
    if not size: return "0 B"
    power = 1024
    n = 0
    Dic_powerN = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while size > power:
        size /= power
        n += 1
    # Formatting trick: Force KB to display as MB for UI consistency
    if n == 1: 
        size /= 1024
        n = 2
    return f"{size:.2f} {Dic_powerN[n]}"

def time_formatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0: return f"{hours}h{minutes}m{seconds}s"
    if minutes > 0: return f"{minutes}m{seconds}s"
    return f"{seconds}s"

# FIX: Permanently locked the bar length to 15 characters to prevent mobile line-breaking!
def make_bar(percent):
    done = int(percent / (100 / 15))
    return "▣" * done + "□" * (15 - done)

async def progress_bar(current, total, status_text, message, start_time, last_update_time):
    now = time.time()
    if round((now - last_update_time[0])) >= 5 or current == total:
        percent = current * 100 / total
        speed = current / (now - start_time)
        eta_ms = round((total - current) / speed) * 1000 if speed > 0 else 0
        
        cpu, mem, disk = get_sys_stats()
        sent, recv = get_network_io()
        import psutil
        free_disk_gb = round(psutil.disk_usage('/').free / (1024**3), 2)
        uptime_str = get_readable_time((time.time() - getattr(AppState, 'boot_time', time.time()))*1000)
        
        if "Downloading" in status_text: current_status = "Downloading"
        elif "Uploading" in status_text: current_status = "Uploading"
        else: current_status = "Processing"

        # FIX: Exact UI Layout with Bold tags!
        text = (
            f"**🌐 Bᴏᴛ Sᴛᴀᴛɪsᴛɪᴄs 🌐**\n\n"
            f"`{AppState.active_file_name}`\n"
            f"[{make_bar(percent)}] {percent:.2f}%\n"
            f"**Processed:** {humanbytes(current)} **of** {humanbytes(total)}\n"
            f"**Status:** {current_status} | **ETA:** {time_formatter(eta_ms)}\n"
            f"**Speed:** {humanbytes(speed)}/s | **Elapsed:** {time_formatter((now - start_time)*1000)}\n\n"
            f"**📥 Files in Queue:** {queue.qsize()}\n\n"
            f"**🖥 Hardware Info:**\n"
            f"**CPU:** {cpu}% | **Free:** {free_disk_gb}GB ({100-disk}%)\n"
            f"**In:** {humanbytes(recv)} | **Out:** {humanbytes(sent)}\n"
            f"**Ram:** {mem}% | **Uptime:** {uptime_str}\n\n"
            f"**🏷Maintained By: @Subhasish_bot**"
        )
        
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("🛑 Cancel Task", callback_data="cancel_running")]])
        
        try:
            await message.edit(text, reply_markup=btn)
            last_update_time[0] = now
        except Exception as e: pass