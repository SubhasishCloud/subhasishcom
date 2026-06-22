import logging
import os

from logging.handlers import RotatingFileHandler
from pyrogram import Client

from .core.config import Config

config_data = Config.load_config()
os.makedirs(Config.THUMB_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    handlers=[
        RotatingFileHandler(
            os.path.join(Config.ENV_DIR, "bot.log"),
            maxBytes=20000000,
            backupCount=5
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
# ===================================================================== #
# Suppress Pyrogram's Internal System Logs (Connection, Ping etc).      #
# ===================================================================== #
logging.getLogger("pyrogram").setLevel(logging.WARNING)
# ===================================================================== #
# Comment Out The Line Above To Re-Enable Detailed Pyrogram logs.       #
# ===================================================================== #
bot_app = Client(
    os.path.join(Config.ENV_DIR, "encoder_bot"),
    api_id=config_data["API_ID"],
    api_hash=config_data["API_HASH"],
    bot_token=config_data["TG_BOT_TOKEN"]
)

if config_data.get("USER_SESSION_STRING"):
    logger.info("✅ User Session detected. Evaluating Account Tier limits...")
    user_app = Client(
        os.path.join(Config.ENV_DIR, "encoder_user"),
        session_string=config_data["USER_SESSION_STRING"],
        api_id=config_data["API_ID"],
        api_hash=config_data["API_HASH"]
    )
else:
    logger.info("ℹ️ No USER_SESSION_STRING. Running on Bot Token (2GB limit).")
    user_app = bot_app  # ← CRITICAL: fallback to bot_app, never None
