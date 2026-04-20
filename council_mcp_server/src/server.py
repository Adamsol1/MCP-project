import os
from sys import stderr

from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.responses import JSONResponse

from prompts import register_prompts

load_dotenv()

print("Starting MCP Council Server...", file=stderr, flush=True)

mcp = FastMCP(
    name="CouncilServer",
    instructions=(
        "MCP server providing council participant persona prompts. "
        "Each prompt defines the analytical perspective and focus area for one "
        "geopolitical participant in a council deliberation."
    ),
)

register_prompts(mcp)


@mcp.custom_route("/health", methods=["GET"])
async def health(request):
    print("Council server health check — running.", file=stderr, flush=True)
    return JSONResponse({"status": "ok", "server": "council"})


if __name__ == "__main__":
    port = int(os.getenv("COUNCIL_MCP_PORT", "8003"))
    mcp.run(transport="sse", host="127.0.0.1", port=port, show_banner=False, log_level="INFO")
