"""Development process management for the local council MCP server."""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse, urlunparse
from urllib.request import urlopen

logger = logging.getLogger("app")

_FALSE_VALUES = {"0", "false", "no", "off"}
_DEFAULT_STARTUP_WAIT_SECONDS = 8.0


def _autostart_enabled() -> bool:
    value = os.getenv("COUNCIL_MCP_AUTOSTART", "1").strip().lower()
    return value not in _FALSE_VALUES


def _startup_wait_seconds() -> float:
    value = os.getenv(
        "COUNCIL_MCP_STARTUP_WAIT_SECONDS", str(_DEFAULT_STARTUP_WAIT_SECONDS)
    )
    try:
        return max(0.0, float(value))
    except ValueError:
        logger.warning(
            "[Council MCP] Invalid COUNCIL_MCP_STARTUP_WAIT_SECONDS=%r; using %.1fs",
            value,
            _DEFAULT_STARTUP_WAIT_SECONDS,
        )
        return _DEFAULT_STARTUP_WAIT_SECONDS


def _is_local_url(server_url: str) -> bool:
    parsed = urlparse(server_url)
    return parsed.hostname in {"127.0.0.1", "localhost"}


def _health_url(server_url: str) -> str:
    parsed = urlparse(server_url)
    return urlunparse(parsed._replace(path="/health", params="", query="", fragment=""))


def _port_in_use(server_url: str) -> bool:
    parsed = urlparse(server_url)
    if parsed.hostname is None or parsed.port is None:
        return False

    try:
        with socket.create_connection((parsed.hostname, parsed.port), timeout=0.3):
            return True
    except OSError:
        return False


def _health_ok(server_url: str, timeout_seconds: float = 0.5) -> bool:
    try:
        with urlopen(_health_url(server_url), timeout=timeout_seconds) as response:
            return 200 <= response.status < 300  # type: ignore[no-any-return]
    except (OSError, URLError):
        return False


async def _wait_for_health(server_url: str, timeout_seconds: float = 15.0) -> bool:
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while asyncio.get_running_loop().time() < deadline:
        if _health_ok(server_url):
            return True
        await asyncio.sleep(0.25)
    return False


async def maybe_start_council_mcp(server_url: str) -> subprocess.Popen[bytes] | None:
    """Start the local council MCP server for development if needed.

    Production or externally hosted MCP setups should set COUNCIL_MCP_URL to a
    non-local URL, or set COUNCIL_MCP_AUTOSTART=0.
    """
    if not _autostart_enabled():
        logger.info("[Council MCP] Autostart disabled")
        return None

    if not _is_local_url(server_url):
        logger.info("[Council MCP] Autostart skipped for non-local URL %s", server_url)
        return None

    if _health_ok(server_url):
        logger.info("[Council MCP] Already running at %s", server_url)
        return None

    startup_wait_seconds = _startup_wait_seconds()
    if startup_wait_seconds > 0:
        logger.info(
            "[Council MCP] Waiting up to %.1fs for an existing local server at %s",
            startup_wait_seconds,
            server_url,
        )
        if await _wait_for_health(server_url, startup_wait_seconds):
            logger.info("[Council MCP] Already running at %s", server_url)
            return None

    if _port_in_use(server_url):
        logger.warning(
            "[Council MCP] Port is in use at %s, but health check did not become ready; "
            "not starting a duplicate server",
            server_url,
        )
        return None

    project_root = Path(__file__).resolve().parents[4]
    council_dir = project_root / "council_mcp_server"
    server_file = council_dir / "server_http.py"
    if not server_file.exists():
        logger.warning("[Council MCP] Cannot autostart; missing %s", server_file)
        return None

    poetry = shutil.which("poetry")
    command = (
        [poetry, "run", "python", "server_http.py"]
        if poetry
        else [sys.executable, "server_http.py"]
    )
    logger.info("[Council MCP] Starting local server for %s", server_url)
    try:
        process = subprocess.Popen(
            command,
            cwd=str(council_dir),
        )
    except OSError as e:
        logger.warning("[Council MCP] Cannot autostart; failed to launch: %s", e)
        return None

    if await _wait_for_health(server_url):
        logger.info("[Council MCP] Local server is ready")
    elif (exit_code := process.poll()) is not None:
        logger.error(
            "[Council MCP] Server exited during startup with code %s", exit_code
        )
        return None
    else:
        logger.warning(
            "[Council MCP] Server started but health check did not become ready"
        )

    return process


async def stop_council_mcp(process: subprocess.Popen[bytes] | None) -> None:
    if process is None or process.poll() is not None:
        return

    logger.info("[Council MCP] Stopping local server")
    if sys.platform == "win32":
        await asyncio.to_thread(
            subprocess.run,
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        await asyncio.to_thread(process.wait)
        return

    process.terminate()
    try:
        await asyncio.wait_for(asyncio.to_thread(process.wait), timeout=5)
    except TimeoutError:
        logger.warning("[Council MCP] Local server did not stop cleanly; killing")
        process.kill()
        await asyncio.to_thread(process.wait)
