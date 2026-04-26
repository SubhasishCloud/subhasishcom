import asyncio
from pyrogram import filters
from bot.__init__ import bot_app
from bot.helper_funcs.utils import AppState, queue, get_sys_stats, get_network_io
from bot.helper_funcs.display_progress import humanbytes

@bot_app.on_message(filters.command("status"))
async def status_cmd(client, message):
    # Fetch real-time hardware telemetry
    cpu, mem, disk = get_sys_stats()
    sent, recv = get_network_io()
    
    text = (
        f"📊 **System Status & Telemetry**\n\n"
        f"⚙️ **Currently Processing:** `{AppState.active_file_name}`\n"
        f"📥 **Files in Queue:** `{queue.qsize()}`\n\n"
        f"**🖥 Hardware Info:**\n"
        f"• **CPU Usage:** `{cpu}%`\n"
        f"• **RAM Usage:** `{mem}%`\n"
        f"• **Disk Usage:** `{disk}%`\n"
        f"• **Network In:** `{humanbytes(recv)}`\n"
        f"• **Network Out:** `{humanbytes(sent)}`"
    )
    
    msg = await message.reply(text)
    
    # Auto-Delete if no tasks are running to keep chat clean
    if AppState.active_file_name == "None" and queue.qsize() == 0:
        await asyncio.sleep(30)
        try:
            await msg.delete()
        except: 
            pass