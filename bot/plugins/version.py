import asyncio
import os
import re
import sys

from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.types import ReplyParameters

from .. import bot_app, logger
from ..helper_funcs.download import get_graph_link
from ..helper_funcs.utils import delete_message_later
from ..shared.common import spawn_temporary_task
from ..shared.localisation import Localisation

@bot_app.on_message(filters.command(["version", "v"]))
async def version_cmd(client, message) -> None:
    """Handle The Command To Display System Env, Runtime & Installed Packages."""
    if not message: return

    status_msg = await bot_app.send_message(message.chat.id, Localisation.VERSION_FETCHING, reply_parameters=ReplyParameters(message_id=message.id), parse_mode=ParseMode.HTML)

    try:
        async with asyncio.timeout(20.0):

            os_name, os_version = "Unknown OS", "Unknown Version"
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="): os_name = line.split("=")[1].strip().strip('"')
                        if line.startswith("DEBIAN_VERSION_FULL="): os_version = line.split("=")[1].strip().strip('"')

            # --- Advanced Regex: Python Version ---
            py_raw = sys.version.replace("\n", " ")
            py_match = re.search(r"^([\d\.]+)\s*\(.*?\)\s*(\[.*?\])", py_raw)
            py_ver = f"v{py_match.group(1)} {py_match.group(2)}" if py_match else py_raw

            # --- Advanced Regex: FFmpeg Version ---
            ffmpeg_ver = "Unknown"
            try:
                proc_ff = await asyncio.create_subprocess_exec("ffmpeg", "-version", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
                stdout_ff, _ = await asyncio.wait_for(proc_ff.communicate(), timeout=5)
                if stdout_ff:
                    ff_raw = stdout_ff.decode()
                    ff_match = re.search(r"ffmpeg version n?([\d\.\-a-zA-Z]+)", ff_raw)
                    ffmpeg_ver = f"v{ff_match.group(1)}" if ff_match else ff_raw.split("\n")[0].strip()
            except Exception: pass

            # --- Advanced Regex: MediaInfo Version ---
            mi_ver = "Unknown"
            try:
                proc_mi = await asyncio.create_subprocess_exec("mediainfo", "--version", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
                stdout_mi, _ = await asyncio.wait_for(proc_mi.communicate(), timeout=5)
                if stdout_mi:
                    mi_raw = stdout_mi.decode().strip()
                    mi_match = re.search(r"v([\d\.]+)", mi_raw)
                    mi_ver = f"v{mi_match.group(1)}" if mi_match else mi_raw.split("\n")[-1].split("-")[-1].strip()
            except Exception as e: logger.error(f"Failed To Generate MediaInfo Version: {e}")

            # --- Advanced Regex: MKVToolNix Version ---
            mkv_ver = "Unknown"
            try:
                proc_mkv = await asyncio.create_subprocess_exec("mkvmerge", "--version", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
                stdout_mkv, _ = await asyncio.wait_for(proc_mkv.communicate(), timeout=5)
                if stdout_mkv:
                    mkv_raw = stdout_mkv.decode().strip()
                    mkv_match = re.search(r"(v[\d\.]+)\s+\('([^']+)'\)", mkv_raw)
                    mkv_ver = f"{mkv_match.group(1)} ({mkv_match.group(2)})" if mkv_match else mkv_raw.replace("mkvmerge ", "").replace("'", "")
            except Exception as e: logger.error(f"Failed To Generate MKVToolNix Version: {e}")

            # --- Advanced Regex: Git Version ---
            git_ver = "Unknown"
            try:
                proc_git = await asyncio.create_subprocess_exec("git", "--version", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
                stdout_git, _ = await asyncio.wait_for(proc_git.communicate(), timeout=5)
                if stdout_git:
                    git_raw = stdout_git.decode().strip()
                    git_match = re.search(r"git version ([\d\.]+)", git_raw)
                    git_ver = f"v{git_match.group(1)}" if git_match else git_raw
            except Exception: pass

            g_date, g_time = "Unknown", "Unknown"
            if os.path.exists(".git"):
                try:
                    proc_log = await asyncio.create_subprocess_exec("git", "-c", "safe.directory=*", "log", "-1", "--format=%cd", "--date=format:%d/%m/%Y|%I:%M %p", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
                    stdout_log, _ = await asyncio.wait_for(proc_log.communicate(), timeout=5)
                    git_out = stdout_log.decode().strip()
                    if "|" in git_out: g_date, g_time = git_out.split("|")
                except Exception:
                    if "proc_log" in locals() and proc_log.returncode is None:
                        try: proc_log.kill(); await proc_log.wait()
                        except: pass

            # --- Pip Freeze & Direct Graph.org Upload ---
            pip_output = "No packages found."
            try:
                proc_pip = await asyncio.create_subprocess_exec("pip", "freeze", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
                stdout_pip, _ = await asyncio.wait_for(proc_pip.communicate(), timeout=5)
                if stdout_pip: pip_output = stdout_pip.decode().strip()
            except Exception: pass

            content_json = [{"tag": "pre", "children": [pip_output]}]
            graph_link = await get_graph_link(content_json, title="System Packages", author="Subhasish Encoder")
            if not graph_link: graph_link = "Upload Failed"

            final_text = (
                f"💎 <b>SYSTEM VERSIONS:</b> 💎\n"
                f"🐧 <i><b>OS ➝</b></i> <code>{os_name}</code>\n"
                f"🔖 <i><b>Full OS ➝</b></i> <code>v{os_version}</code>\n"
                f"🐍 <i><b>Python ➝</b></i> <code>{py_ver}</code>\n"
                f"🎬 <i><b>FFmpeg ➝</b></i> <code>{ffmpeg_ver}</code>\n"
                f"🔍 <i><b>MediaInfo ➝</b></i> <code>{mi_ver}</code>\n"
                f"🧩 <i><b>MKVToolNix ➝</b></i> <code>{mkv_ver}</code>\n"
                f"⚙️ <i><b>Git ➝</b></i> <code>{git_ver}</code>\n\n"
                f"🌳 <b>GITHUB REPOSITORY:</b> 🌳\n"
                f"🌟 <b><u>Last Updated:</u></b> 🌟\n"
                f"✶ <i><b>Date ➝</b></i> {g_date}\n"
                f"✶ <i><b>Time ➝</b></i> {g_time}\n\n"
                f"📚 <b>ALL INSTALLED PACKAGES:</b> 📚\n"
                f"🔗 <b>{graph_link}</b>"
            )

            await status_msg.edit_text(final_text, parse_mode=ParseMode.HTML)

    except TimeoutError:
        logger.error("⚠️ Version Command Error: Process Timed Out While Fetching Data.")
        await status_msg.edit_text("❌ <b>Error:</b> <i>Sys Info Timed Out..!!</i>", parse_mode=ParseMode.HTML)

    except Exception as e:
        logger.error(f"⚠️ Version Command Error: {e}", exc_info=True)
        await status_msg.edit_text(Localisation.VERSION_FAILED, parse_mode=ParseMode.HTML)

    finally:
        spawn_temporary_task(delete_message_later(status_msg, 1800))
        spawn_temporary_task(delete_message_later(message, 1800))
