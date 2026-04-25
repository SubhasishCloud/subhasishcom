import os
import asyncio
import time
import re
from datetime import datetime, timezone, timedelta
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.__init__ import bot_app, user_app, logger, config_data
from bot.config import Config
from bot.localisation import Localisation
from bot.helper_funcs.utils import queue, AppState
from bot.helper_funcs.display_progress import progress_bar, humanbytes, time_formatter, make_bar

# --- IST TIME GENERATOR ---
def get_ist():
    tz = timezone(timedelta(hours=5, minutes=30))
    return f"\n`{datetime.now(tz).strftime('%Y-%m-%d %I:%M:%S %p')} (GMT+05:30)`\n"

# --- LOG SENDER ---
async def send_log(msg_text):
    log_channel = config_data.get("LOG_CHANNEL")
    if log_channel:
        try:
            await bot_app.send_message(log_channel, msg_text)
        except Exception as e:
            logger.error(f"Failed to send log: {e}")

# --- HIJACKED FEATURE: AUTO THUMBNAIL GENERATOR ---
async def take_screen_shot(video_file, output_directory, ttl):
    out_put_file_name = os.path.join(output_directory, f"{time.time()}_thumb.jpg")
    
    file_genertor_command = [
        "ffmpeg", "-ss", str(ttl), "-i", video_file, "-vframes", "1", out_put_file_name
    ]
    try:
        process = await asyncio.create_subprocess_exec(
            *file_genertor_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.communicate()
        if os.path.lexists(out_put_file_name):
            return out_put_file_name
    except Exception as e:
        logger.error(f"Failed to generate auto-thumbnail: {e}")
    return None

async def worker():
    while True:
        msg, name, map_args, status_msg = await queue.get()
        AppState.active_file_name = name
        start_time = time.time()
        last_up = [time.time()]
        file_path = None
        out = None
        auto_thumb_path = None
        
        try:
            # =====================================
            # 1. DOWNLOAD PHASE
            # =====================================
            now_time = get_ist()
            await send_log(f"**Bot Become Busy Now !!** \n\nDownload Started at {now_time}")
            
            try:
                file_path = await user_app.download_media(
                    msg, 
                    progress=progress_bar, 
                    progress_args=(Localisation.DOWNLOAD_START, status_msg, start_time, last_up)
                )
                
                if not file_path or not os.path.exists(file_path):
                    await status_msg.edit(Localisation.FILE_NOT_FOUND)
                    now_time = get_ist()
                    await send_log(f"**Download Error, Bot is Free Now !!** \n\nProcess Done at {now_time}\nReason: Path not exist")
                    continue
                    
            except Exception as e:
                await status_msg.edit(Localisation.DOWNLOAD_FAILED)
                now_time = get_ist()
                await send_log(f"**Download Failed, Bot is Free Now !!** \n\nProcess Done at {now_time}\nError: {e}")
                continue
                
            dl_time = int(time.time() - start_time)
            await status_msg.edit(Localisation.DOWNLOADED_SUCCESS.format(time_formatter(dl_time * 1000)))
            
            now_time = get_ist()
            await send_log(f"**Download Stopped, Bot is Free Now !!** \n\nProcess Done at {now_time}")
            await asyncio.sleep(2.5) 
            
            # =====================================
            # 2. COMPRESSION PHASE
            # =====================================
            base = name.replace(" ", ".").rsplit(".", 1)[0]
            out = f"{base}.Compressed.mkv"
            
            await status_msg.edit(Localisation.COMPRESS_START)
            now_time = get_ist()
            await send_log(f"**Compressing Video ...** \n\nProcess Started at {now_time}")
            
            res = config_data['RESOLUTION'].lower().replace("x", ":")
            cmd = ["ffmpeg", "-i", file_path] + map_args + [
                "-c:v", config_data["CODEC"], "-crf", str(config_data["CRF"]), "-preset", config_data["PRESET"],
                "-vf", f"scale={res}", "-c:a", "libopus", "-b:a", config_data["AUDIO_BITRATE"],
                "-y", out
            ]
            
            try:
                process = await asyncio.create_subprocess_exec(*cmd, stderr=asyncio.subprocess.PIPE)
                AppState.current_process = process
                
                last_update_time = time.time()
                duration_sec = 0
                btn = InlineKeyboardMarkup([[InlineKeyboardButton("🛑 Cancel Task", callback_data="cancel_running")]])

                while True:
                    line = await process.stderr.readline()
                    if not line: break
                    line_str = line.decode('utf-8', errors='ignore').strip()
                    
                    if not duration_sec and "Duration:" in line_str:
                        match = re.search(r"Duration:\s*(\d{2}):(\d{2}):(\d{2})", line_str)
                        if match: 
                            duration_sec = int(match.group(1))*3600 + int(match.group(2))*60 + int(match.group(3))
                        else:
                            await status_msg.edit(Localisation.METADATA_FAILED)
                            await send_log(f"**Getting Video Meta Data Failed** \n\nProcess Done at {get_ist()}")

                    if "time=" in line_str:
                        time_match = re.search(r"time=(\d{2}):(\d{2}):(\d{2})", line_str)
                        if time_match and (time.time() - last_update_time > 5):
                            curr_sec = int(time_match.group(1))*3600 + int(time_match.group(2))*60 + int(time_match.group(3))
                            if duration_sec > 0:
                                percent = (curr_sec / duration_sec) * 100
                                elapsed = time.time() - start_time
                                speed = curr_sec / elapsed if elapsed > 0 else 0
                                eta = (duration_sec - curr_sec) / speed if speed > 0 else 0
                                
                                text = (
                                    f"ℹ️ <b>ɴᴏᴡ:</b> <b>💡 ENCODING... 💡</b>\n\n"
                                    f"⏱️ <b>ᴇᴛᴀ:</b> {time_formatter(eta*1000)}\n\n"
                                    f"<code>[{make_bar(percent)}]</code> {percent:.1f}%\n"
                                )
                            else:
                                text = f"ℹ️ <b>ɴᴏᴡ:</b> <b>💡 ENCODING... 💡</b>\n\n⏱ `{time_match.group(1)}`"
                            try:
                                await status_msg.edit(text, reply_markup=btn)
                                last_update_time = time.time()
                            except: pass

                await process.wait()
                if AppState.current_process == process: AppState.current_process = None

                if process.returncode != 0:
                    raise Exception("FFmpeg Process Crashed or Cancelled")
                    
            except Exception as e:
                await status_msg.edit(Localisation.COMPRESS_FAILED)
                now_time = get_ist()
                await send_log(f"**Compression Failed, Bot is Free Now !!** \n\nProcess Done at {now_time}\nError: {e}")
                if file_path and os.path.exists(file_path): os.remove(file_path)
                if out and os.path.exists(out): os.remove(out)
                continue

            # =====================================
            # 3. THUMBNAIL LOGIC & API CHECK
            # =====================================
            final_size = os.path.getsize(out)
            if final_size > 4294967296: 
                await status_msg.edit(Localisation.FILE_SIZE_LIMIT.format(humanbytes(final_size)))
                if file_path and os.path.exists(file_path): os.remove(file_path)
                if out and os.path.exists(out): os.remove(out)
                now_time = get_ist()
                await send_log(f"**Upload Stopped, Bot is Free Now !!** \n\nProcess Done at {now_time}\nReason: Exceeded 4GB API Limit")
                continue

            now_time = get_ist()
            await send_log(f"**Uploading Video ...** \n\nProcess Started at {now_time}")

            # Smart Thumbnail Selection
            custom_thumb = os.path.join(Config.THUMB_DIR, f"{msg.from_user.id}.jpg")
            if os.path.exists(custom_thumb):
                actual_thumb = custom_thumb
            else:
                # Generate a thumbnail from the 5-second mark of the compressed video
                auto_thumb_path = await take_screen_shot(out, Config.THUMB_DIR, 5)
                actual_thumb = auto_thumb_path

            final_caption = f"✅ <b>{out}</b>\n\n<b>©ᴇɴᴄᴏᴅᴇᴅ Bʏ:</b> <b>@{AppState.bot_username}</b>"

            try:
                upload_start = time.time()
                last_up_time = [time.time()]
                await user_app.send_document(
                    chat_id=msg.chat.id, document=out, thumb=actual_thumb,
                    caption=final_caption, force_document=True,
                    progress=progress_bar, progress_args=(Localisation.UPLOAD_START, status_msg, upload_start, last_up_time)
                )
            except Exception as e:
                await status_msg.edit(Localisation.UPLOAD_FAILED)
                now_time = get_ist()
                await send_log(f"**Upload Stopped, Bot is Free Now !!** \n\nProcess Done at {now_time}\nError: {e}")
            finally:
                await status_msg.edit("✅ Process Complete!")
                if file_path and os.path.exists(file_path): os.remove(file_path)
                if out and os.path.exists(out): os.remove(out)
                if auto_thumb_path and os.path.exists(auto_thumb_path): os.remove(auto_thumb_path)
            
            now_time = get_ist()
            await send_log(f"**Upload Done, Bot is Free Now !!** \n\nProcess Done at {now_time}")
            
        except Exception as e: 
            logger.error(f"Fatal Worker Error: {e}")
        finally: 
            AppState.active_file_name = "None"
            queue.task_done()