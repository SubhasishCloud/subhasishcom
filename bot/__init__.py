import logging
from logging.handlers import RotatingFileHandler
import os
from pyrogram import Client
from bot.config import Config

config_data = Config.load_config()
os.makedirs(Config.THUMB_DIR, exist_ok=True)

# --- HIJACKED FEATURE: ROTATING LOGS ---
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    handlers=[
        RotatingFileHandler(
            "bot.log",
            maxBytes=20000000, # 20MB Max Log Size
            backupCount=5      # Keep 5 backups
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

bot_app = Client(
    "bot_session", 
    api_id=config_data["API_ID"], 
    api_hash=config_data["API_HASH"], 
    bot_token=config_data["TG_BOT_TOKEN"]
)

# Use Session String if provided, otherwise default to local file session
if config_data.get("USER_SESSION_STRING"):
    user_app = Client(
        "user_session_string",
        session_string=config_data["USER_SESSION_STRING"],
        api_id=config_data["API_ID"], 
        api_hash=config_data["API_HASH"]
    )
else:
    user_app = Client(
        "user_session", 
        api_id=config_data["API_ID"], 
        api_hash=config_data["API_HASH"]
    )