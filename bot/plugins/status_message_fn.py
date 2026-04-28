import time
import asyncio
from pyrogram import filters
from bot.__init__ import bot_app
from bot.helper_funcs.utils import AppState, queue, get_sys_stats, get_network_io, get_readable_time
from bot.helper_funcs.display_progress import humanbytes

@bot_app.on_message(filters.command("status"))
async def status_cmd(client, message):
    cpu, mem, disk = get_sys_stats()
    sent, recv = get_network_io()
    import psutil
    free_disk_bytes = psutil.disk_usage('/').free
    free_disk_gb = round(free_disk_bytes / (1024**3), 2)
    uptime_str = get_readable_time((time.time() - getattr(AppState, 'boot_time', time.time()))*1000)
    
    text = (
        f"⚙️ **Currently Processing:**\n"
        f"`{AppState.active_file_name}`\n"
        f"[□□□□□□□□□□□□□□□□□□□□] 0.00%\n"
        f"Processed: 0 B of 0 B\n"
        f"Status: Idle | ETA: 0s\n"
        f"Speed: 0 B/s | Elapsed: 0s\n\n"
        f"📥 **Files in Queue:** `{queue.qsize()}`\n\n"
        f"**🖥 Hardware Info:**\n"
        f"Cpu: {cpu}% | Free: {free_disk_gb}GB ({100-disk}%)\n"
        f"In: {humanbytes(recv)} | Out: {humanbytes(sent)}\n"
        f"Ram: {mem}% | Uptime: {uptime_str}\n\n"
        f"🏷**Maintained By: @Subhasish_bot**"
    )
    
    msg = await message.reply(text)
    
    # SMART AUTO-DELETE: Always deletes original command. Deletes bot reply ONLY if idle.
    await asyncio.sleep(30)
    try: await message.delete()
    except: pass
    
    if AppState.active_file_name == "None" and queue.qsize() == 0:
        try: await msg.delete()
        except: pass