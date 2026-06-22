import importlib
import time

from pathlib import Path

from .. import logger

def starter() -> None:
    """Smart Auto-Loader: Scans specified directories and dynamically loads all .py files."""
    start_time: float = time.perf_counter()
    # This gets the exact path to your root folder
    bot_dir: Path = Path(__file__).parent.parent
    # 🚀 FUTURE PROOFING: Add any new folder names to this list!
    target_folders: list[str] = ["plugins"]
    # Dynamically determine the root package name (e.g., 'bot') safely
    root_pkg: str = __name__.split(".")[0]
    loaded_count: int = 0

    for folder_name in target_folders:
        target_dir: Path = bot_dir / folder_name
        # ENTERPRISE SAFETY CHECK: Ensure the target directory actually exists!
        if not target_dir.exists() or not target_dir.is_dir():
            logger.warning("⚠️ Target directory missing or invalid: %s", target_dir)
            continue
        # sorted() ensures modules always load in the exact same alphabetical order
        for file_path in sorted(target_dir.rglob("*.py")):
            if file_path.name.startswith("__"):
                continue
            # Construct the relative module path (e.g., .plugins.commands)
            relative_path: Path = file_path.relative_to(bot_dir)
            module_path: str = "." + ".".join(relative_path.with_suffix("").parts)

            try:
                importlib.import_module(module_path, package=root_pkg)
                logger.debug("Successfully Loaded Module: %s", module_path)
                loaded_count += 1
            except Exception:
                logger.exception("FATAL: Failed to load module: %s", module_path)
                raise

    elapsed_time: float = time.perf_counter() - start_time
    logger.info("🎉 ᴀʟʟ %d ᴍᴏᴅᴜʟᴇs ʟᴏᴀᴅᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ ɪɴ %.3fs. 🎉", loaded_count, elapsed_time)
