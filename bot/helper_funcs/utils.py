import asyncio
import time

queue = asyncio.Queue()
START_TIME = time.time()

class AppState:
    current_process = None
    active_file_name = "None"
    pending_tasks = {}
    awaiting_index = {}
    bot_username = "Bot" 

# --- HIJACKED FEATURE: SUPERIOR UPTIME FORMATTER ---
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