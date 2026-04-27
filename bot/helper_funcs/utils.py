import asyncio
import time
from datetime import datetime, timezone, timedelta
from bot.__init__ import bot_app, logger, config_data

queue = asyncio.Queue()
START_TIME = time.time()

class AppState:
    current_process = None
    active_file_name = "None"
    pending_tasks = {}
    awaiting_index = {}
    bot_username = "Bot" 
    bsetting_state = {}  
    is_premium = False 

def get_readable_time(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = (
        ((str(days) + "d, ") if days else "")
        + ((str(hours) + "h, ") if hours else "")
        + ((str(minutes) + "m, ") if minutes else "")
        + ((str(seconds) + "s") if seconds else "")
    )
    return tmp

def get_ist():
    tz = timezone(timedelta(hours=5, minutes=30))
    return f"\n`{datetime.now(tz).strftime('%Y-%m-%d %I:%M:%S %p')} (GMT+05:30)`\n"

async def send_log(msg_text: str):
    log_channel = config_data.get("LOG_CHANNEL")
    if log_channel:
        try:
            await bot_app.send_message(log_channel, msg_text)
        except Exception as e:
            logger.error(f"Failed to send log: {e}")

def get_sys_stats():
    import psutil
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    return cpu, mem, disk

def get_network_io():
    import psutil
    net = psutil.net_io_counters()
    sent = net.bytes_sent
    recv = net.bytes_recv
    return sent, recv

# --- NEW: DATA CENTER & SIZE EXTRACTOR ---
def get_file_info(message):
    media = message.video or message.document
    if not media: return "Unknown", "Unknown"
    
    # Calculate Size
    size_bytes = media.file_size
    if not size_bytes: size_str = "0 B"
    else:
        for unit in ['B','KB','MB','GB','TB']:
            if size_bytes < 1024:
                size_str = f"{size_bytes:.2f}{unit}"
                break
            size_bytes /= 1024
            
    # Extract DC ID
    # Pyrogram stores file references in string format. The DC ID is usually embedded.
    try:
        file_id = media.file_id
        import base64
        import struct
        decoded = base64.urlsafe_b64decode(file_id + '=' * (-len(file_id) % 4))
        dc_id = struct.unpack('<q', decoded[0:8])[0] & 0xFF
        dc_name = f"DC{dc_id}"
        # Optional Map for aesthetics based on standard Telegram DCs
        dc_map = {1: "Miami, USA - DC1", 2: "Amsterdam, NL - DC2", 3: "Miami, USA - DC3", 4: "Amsterdam, NL - DC4", 5: "Singapore, SG - DC5"}
        dc_str = dc_map.get(dc_id, dc_name)
    except:
        dc_str = "Unknown DC"
        
    return size_str, dc_str