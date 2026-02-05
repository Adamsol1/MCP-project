"""Runner module for starting the FastAPI server."""

import uvicorn


def dev():
    """Run the development server with hot reload."""
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


def start():
    """Run the production server."""
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
    )
