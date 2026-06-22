import asyncio

from collections import OrderedDict
from pyrogram.enums import ButtonStyle
from pyrogram.errors import FloodWait, MessageNotModified
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .. import logger
from ..helper_funcs.utils import AppState

BACKGROUND_TASKS = set()
MESSAGE_LOCKS = {}
LAST_SENT_TEXT = OrderedDict()

def get_msg_lock(msg_id):
    if len(MESSAGE_LOCKS) > 500:
        idle_locks = [k for k, v in list(MESSAGE_LOCKS.items()) if not v.locked()]
        for k in idle_locks[:50]:
            MESSAGE_LOCKS.pop(k, None)

    return MESSAGE_LOCKS.setdefault(msg_id, asyncio.Lock())

def _cleanup_task(task) -> None:
    BACKGROUND_TASKS.discard(task)
    try:
        exc = task.exception()
        if exc:
            logger.error(f"Background task failed: {exc}", exc_info=exc)
    except asyncio.CancelledError:
        pass

def spawn_temporary_task(coro, max_timeout=3600):
    async def watchdog() -> None:
        try:
            await asyncio.wait_for(coro, timeout=max_timeout)
        except TimeoutError:
            logger.warning("A background task was safely terminated after reaching the 1-hour limit.")
        except asyncio.CancelledError:
            pass

    task = asyncio.create_task(watchdog())
    BACKGROUND_TASKS.add(task)
    task.add_done_callback(_cleanup_task)
    return task

async def safe_delete(msg, log_context="Message") -> None:
    """Enterprise helper to silently delete message objects without log spam."""
    if not msg:
        return
    try: await msg.delete()
    except Exception as e: logger.debug(f"{log_context} deletion failed: {e}")

async def safe_delete_by_id(client, chat_id, msg_id, log_context="Message ID") -> None:
    """Enterprise helper to cleanly delete messages by ID without wasting API GET calls."""
    if not msg_id:
        return
    try: await client.delete_messages(chat_id=chat_id, message_ids=msg_id)
    except Exception as e: logger.debug(f"{log_context} deletion failed: {e}")

async def safe_edit(msg, text, **kwargs) -> None:
    if not msg or not getattr(msg, "id", None):
        return

    msg_id = msg.id

    markup_str = str(kwargs.get("reply_markup", ""))
    cache_key = f"{text}_{markup_str}"

    if LAST_SENT_TEXT.get(msg_id) == cache_key:
        LAST_SENT_TEXT.move_to_end(msg_id)
        return

    if len(LAST_SENT_TEXT) > 500:
        LAST_SENT_TEXT.popitem(last=False)

    lock = get_msg_lock(msg_id)

    try:
        async with lock:
            await asyncio.wait_for(msg.edit_text(text, **kwargs), timeout=10.0)
            LAST_SENT_TEXT[msg_id] = cache_key
    except MessageNotModified:
        LAST_SENT_TEXT[msg_id] = cache_key
    except asyncio.CancelledError:
        raise
    except TimeoutError:
        pass
    except FloodWait as e:
        wait_time = int(getattr(e, "value", getattr(e, "x", 5)))
        for _ in range(wait_time):
            if AppState.cancel_task:
                raise asyncio.CancelledError
            await asyncio.sleep(1)
        try:
            async with lock:
                await asyncio.wait_for(msg.edit_text(text, **kwargs), timeout=10.0)
                LAST_SENT_TEXT[msg_id] = cache_key
        except MessageNotModified:
            LAST_SENT_TEXT[msg_id] = cache_key
        except asyncio.CancelledError:
            raise
        except TimeoutError:
            pass
        except Exception as e:
            error_str = str(e).upper()
            if "MESSAGE_ID_INVALID" in error_str or "DELETED" in error_str:
                LAST_SENT_TEXT.pop(msg_id, None)
                MESSAGE_LOCKS.pop(msg_id, None)
            else:
                logger.exception(f"safe_edit recovery failed: {e}")
    except Exception as e:
        error_str = str(e).upper()
        if "MESSAGE_ID_INVALID" in error_str or "DELETED" in error_str:
            LAST_SENT_TEXT.pop(msg_id, None)
            MESSAGE_LOCKS.pop(msg_id, None)
        else:
            logger.exception(f"safe_edit initial edit failed: {e}")

async def safe_readline(stream, timeout=10):
    try:
        return await asyncio.wait_for(stream.readline(), timeout=timeout)
    except TimeoutError:
        return None

def get_bsetting_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("API_ID", callback_data="bsetting_select_API_ID", style=ButtonStyle.PRIMARY),
         InlineKeyboardButton("API_HASH", callback_data="bsetting_select_API_HASH", style=ButtonStyle.PRIMARY)],
        [InlineKeyboardButton("TG_BOT_TOKEN", callback_data="bsetting_select_TG_BOT_TOKEN", style=ButtonStyle.PRIMARY),
         InlineKeyboardButton("OWNER_ID", callback_data="bsetting_select_OWNER_ID", style=ButtonStyle.PRIMARY)],
        [InlineKeyboardButton("LOG_CHANNEL", callback_data="bsetting_select_LOG_CHANNEL", style=ButtonStyle.PRIMARY),
         InlineKeyboardButton("AUTH_USERS", callback_data="bsetting_select_AUTH_USERS", style=ButtonStyle.PRIMARY)],
        [InlineKeyboardButton("USER_SESSION_STRING", callback_data="bsetting_select_USER_SESSION_STRING", style=ButtonStyle.PRIMARY)],
        [InlineKeyboardButton("CRF", callback_data="bsetting_select_CRF", style=ButtonStyle.PRIMARY),
         InlineKeyboardButton("PRESET", callback_data="bsetting_select_PRESET", style=ButtonStyle.PRIMARY)],
        [InlineKeyboardButton("RESOLUTION", callback_data="bsetting_select_RESOLUTION", style=ButtonStyle.PRIMARY),
         InlineKeyboardButton("AUDIO_BITRATE", callback_data="bsetting_select_AUDIO_BITRATE", style=ButtonStyle.PRIMARY)],
        [InlineKeyboardButton("CODEC", callback_data="bsetting_select_CODEC", style=ButtonStyle.PRIMARY),
         InlineKeyboardButton("WATERMARK", callback_data="bsetting_select_WATERMARK_TEXT", style=ButtonStyle.PRIMARY)],
        [InlineKeyboardButton("AS_DOCUMENT", callback_data="bsetting_toggle_AS_DOCUMENT", style=ButtonStyle.PRIMARY)],
        [InlineKeyboardButton("❌ Close", callback_data="bsetting_close", style=ButtonStyle.DANGER)]
    ])
