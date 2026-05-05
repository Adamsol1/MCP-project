"""Runner module for starting the FastAPI server."""

import socket
import sys
from urllib.error import URLError
from urllib.request import urlopen

import uvicorn


def _health_ok(port: int) -> bool:
    try:
        with urlopen(f"http://127.0.0.1:{port}/health", timeout=0.3) as response:
            return 200 <= response.status < 300
    except (OSError, URLError):
        return False


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def dev():
    """Run the development server with hot reload."""
    port = 8000
    url = f"http://127.0.0.1:{port}"
    if _health_ok(port):
        print(f"Backend API already running on {url}", flush=True)
        return
    if _port_in_use(port):
        print(
            f"Backend API port {port} is already in use. Stop the other process.",
            file=sys.stderr,
            flush=True,
        )
        raise SystemExit(1)

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="warning",
        access_log=False,
    )


def start():
    """Run the production server."""
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
    )
