import asyncio
import httpx
import importlib
import json
import os
from bot import bot_app, logger, user_app
from bot.config import Config
from bot.helper_funcs.ffmpeg import worker
from bot.helper_funcs.utils import AppState, cpu_monitor
from contextlib import suppress
from pyrogram import idle
# ===================================================================== #
# IMPORTANT: Handles registering all Pyrogram handlers for Telegram     #
# ===================================================================== #
def load_all_plugins() -> None:
    plugins = (
        "bot.plugins.call_back_button_handler",
        "bot.plugins.commands",
        "bot.plugins.incoming_message_fn",
        "bot.plugins.merge_handler",
        "bot.plugins.status_message_fn"
    )

    logger.debug("Loading %d Plugins...", len(plugins))

    for p in plugins:
        try:
            importlib.import_module(p); logger.debug("Successfully Loaded Plugin: %s", p)
        except Exception: logger.exception("FATAL: Failed to load plugin: %s", p); raise

    logger.info("🎉 ᴀʟʟ %d ᴘʟᴜɢɪɴs ʟᴏᴀᴅᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ. 🎉", len(plugins))

async def fetch_default_thumbnail() -> None:
    thumb_url = "https://telegra.ph/file/5c4635e173e7407694a63.jpg"
    thumb_path = os.path.join(Config.ENV_DIR, "thumb.jpg")

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20), follow_redirects=True) as client:
            resp = await client.get(thumb_url)
            resp.raise_for_status()
        with open(thumb_path, "wb") as f:
            f.write(resp.content)
        logger.info("Default universal thumbnail saved to %s", thumb_path)
    except Exception as e:
        logger.warning("Default thumbnail download skipped: %s", e)

async def main() -> None:
    worker_task = None
    cpu_task = None
    try:
        p1 = await asyncio.create_subprocess_exec("pkill", "-9", "-f", "ffmpeg", stderr=asyncio.subprocess.DEVNULL)
        await p1.wait()
        p2 = await asyncio.create_subprocess_exec("pkill", "-9", "-f", "ffprobe", stderr=asyncio.subprocess.DEVNULL)
        await p2.wait()
    except Exception:
        pass

    try:
        logger.info("Fetching Default Universal Thumbnail...")
        await fetch_default_thumbnail()

        await bot_app.start()
        logger.info("Bot Username Detected: @%s", bot_app.me.username)

        AppState.bot_username = bot_app.me.username

        if user_app != bot_app:
            logger.info("Booting Upload Client...")
            if not user_app.is_connected:
                await user_app.start()
            AppState.is_premium = True
            logger.info("✅ Upload Client (Userbot) Verified | Limit Status: Premium (4GB Uploads)")
        else:
            logger.info("✅ Running In Bot-Only Mode (2GB Limit)")

        logger.info("Bot Started! 🤖")

        # Start the worker and the CPU monitor as concurrent background tasks & save them as a task reference.
        worker_task = asyncio.create_task(worker())
        cpu_task = asyncio.create_task(cpu_monitor())   # ← keeps _cpu_cache fresh

        restart_path = os.path.join(Config.ENV_DIR, "restart.json")
        if os.path.exists(restart_path):
            try:
                with open(restart_path) as f:
                    data = json.load(f)
                    chat_id = data.get("chat_id")
                    msg_id = data.get("message_id")
                    if chat_id and msg_id:
                        await bot_app.edit_message_text(
                            chat_id,
                            msg_id,
                            "**Restarted Successfully!** ✅"
                        )
            except Exception:
                logger.exception("Failed to edit restart msg")
            finally:
                if os.path.exists(restart_path): os.remove(restart_path)

        await idle()

    except Exception:
        logger.exception("Fatal error in main loop")
        raise
    finally:
        if worker_task: worker_task.cancel()
        if cpu_task: cpu_task.cancel()
        if worker_task:
            try:
                await asyncio.wait_for(worker_task, timeout=5.0)
            except asyncio.CancelledError: pass
            except TimeoutError: logger.warning("⚠️ Worker Task Shutdown Timed Out!")

        if cpu_task:
            try:
                await asyncio.wait_for(cpu_task, timeout=5.0)
            except asyncio.CancelledError: pass
            except TimeoutError: logger.warning("⚠️ CPU Monitor Shutdown Timed Out!")

        if bot_app:
            with suppress(Exception): await bot_app.stop()

        if user_app and user_app != bot_app:
            with suppress(Exception): await user_app.stop()

if __name__ == "__main__":
    try:
        load_all_plugins()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except KeyboardInterrupt: logger.info("Bot stopped by user.")
