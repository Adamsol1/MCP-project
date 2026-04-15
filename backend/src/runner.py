"""Runner module for starting the FastAPI server."""

import os

import uvicorn

_BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8003"))


def dev():
    """Run the development server with hot reload."""
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=_BACKEND_PORT,
        reload=True,
    )


def start():
    """Run the production server."""
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=_BACKEND_PORT,
    )
