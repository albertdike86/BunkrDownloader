"""Batch downloader with optional machine-local Python configuration.

This module manages the entire download process by leveraging asynchronous operations,
allowing for efficient handling of multiple URLs.

When ``local_config.py`` exists it supplies private URLs and settings. The file is
ignored by Git. Without it, the existing URLs.txt and command-line behavior is used.
"""

import asyncio
import importlib
import sys
from argparse import Namespace
from pathlib import Path
from urllib.parse import urlparse

from downloader import parse_arguments, validate_and_download
from src.bunkr_utils import get_bunkr_status
from src.config import SESSION_LOG, URLS_FILE
from src.file_utils import read_file, write_file
from src.general_utils import check_python_version, clear_terminal
from src.managers.live_manager import initialize_managers


def load_local_config() -> object | None:
    """Load ignored per-machine settings when present."""
    try:
        return importlib.import_module("local_config")
    except ModuleNotFoundError as exc:
        if exc.name != "local_config":
            raise
        return None


def apply_local_config(args: Namespace, config: object | None) -> None:
    """Apply optional settings without embedding personal values in tracked code."""
    if config is None:
        return

    setting_map = {
        "CUSTOM_PATH": "custom_path",
        "DISABLE_UI": "disable_ui",
        "DISABLE_DISK_CHECK": "disable_disk_check",
        "MAX_RETRIES": "max_retries",
        "IGNORE": "ignore",
        "INCLUDE": "include",
    }
    for setting, argument in setting_map.items():
        if hasattr(config, setting):
            setattr(args, argument, getattr(config, setting))


def show_vpn_reminder(config: object | None, urls: list[str]) -> None:
    """Show the exact downloader process for optional VPN split tunneling."""
    if not getattr(config, "VPN_SPLIT_TUNNEL_REMINDER", False):
        return

    executable = Path(sys.executable).resolve()
    hosts = sorted({urlparse(url).hostname for url in urls if urlparse(url).hostname})
    print(
        "VPN / split-tunnel reminder:\n"
        "  Turn on the VPN before downloading provider-blocked domains.\n"
        f"  Add this executable to the split-tunnel configuration:\n  {executable}\n"
        f"  Configured domains: {', '.join(hosts)}",
    )


async def process_urls(
    urls: list[str], args: Namespace, *, check_server_status: bool = True,
) -> None:
    """Validate and downloads items for a list of URLs."""
    bunkr_status = get_bunkr_status() if check_server_status else {}
    live_manager = initialize_managers(disable_ui=args.disable_ui)

    with live_manager.live:
        for url in urls:
            await validate_and_download(bunkr_status, url, live_manager, args=args)

        live_manager.stop()


async def main() -> None:
    """Run the script and process URLs."""
    # Clear the terminal and session log file
    clear_terminal()
    write_file(SESSION_LOG)

    # Check Python version and parse arguments
    check_python_version()
    args = parse_arguments(common_only=True)
    local_config = load_local_config()
    apply_local_config(args, local_config)

    configured_urls = getattr(local_config, "URLS", None)
    source_urls = configured_urls if configured_urls is not None else read_file(URLS_FILE)
    urls = [url.strip() for url in source_urls if url.strip()]
    show_vpn_reminder(local_config, urls)

    check_server_status = getattr(local_config, "CHECK_SERVER_STATUS", True)
    await process_urls(urls, args, check_server_status=check_server_status)

    # Preserve private local configuration; retain legacy one-shot URLs.txt behavior.
    if configured_urls is None:
        write_file(URLS_FILE)


if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        sys.exit(1)
