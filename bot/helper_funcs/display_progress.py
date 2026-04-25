import time

def humanbytes(size):
    if not size: return "0 B"
    for unit in ['B','KB','MB','GB','TB']:
        if size < 1024: return f"{size:.2f} {unit}"
        size /= 1024

def time_formatter(ms):
    s, ms = divmod(int(ms), 1000)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}h {m:02d}m {s:02d}s"

def make_bar(percent):
    filled = int(percent / 5)
    return "●" * filled + "○" * (20 - filled)

async def progress_bar(current, total, ud_type, message, start_time, last_update):
    if time.time() - last_update[0] > 4:
        now = time.time()
        speed = current / (now - start_time) if (now - start_time) > 0 else 0
        eta = (total - current) / speed if speed > 0 else 0
        percent = (current / total) * 100 if total > 0 else 0
 
        text = (
            f"{ud_type}\n"
            f"<code>[{make_bar(percent)}]</code> {percent:.1f}%\n\n"
            f"⚡️ <b>ꜱᴘᴇᴇᴅ:</b> {humanbytes(speed)}/s\n"
            f"⏰ <b>ᴇᴛᴀ:</b> {time_formatter(eta*1000)}\n"
            f"📦 <b>sɪᴢᴇ:</b> {humanbytes(current)} / {humanbytes(total)}"
        )
        try: 
            await message.edit(text)
            last_update[0] = now
        except: pass