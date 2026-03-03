"""GeminiAgent — AI agent with MCP tool-loop for Collection and Processing phases.

This is the core of the "true MCP" architecture. GeminiAgent sends Gemini a
system prompt + task, then autonomously calls MCP tools (OSINT sources,
knowledge bank, data processing) until it has enough information to return
a final answer.

The backend only manages human approval checkpoints — all AI decisions about
which tools to call and when are made by the agent itself.
"""

import json
import logging
import os
from pathlib import Path

from google import genai
from google.genai import types

logger = logging.getLogger("app")

_SERVER_PATH = str(
    Path(__file__).parent.parent.parent.parent / "mcp_server" / "src" / "server.py"
)


class GeminiAgent:
    """Gemini AI agent that autonomously calls MCP tools to complete tasks.

    The agent runs a tool-use loop:
      1. Send system prompt + task to Gemini with available MCP tools
      2. Gemini decides which tools to call
      3. Execute tool calls via MCPClient
      4. Feed results back to Gemini
      5. Repeat until Gemini returns a final text response (no more tool calls)

    Args:
        model: Gemini model ID to use.
        mcp_client: Connected MCPClient instance for tool execution.
        max_tool_rounds: Safety limit on tool-call iterations (prevents infinite loops).
    """

    def __init__(
        self,
        mcp_client,
        model: str = "gemini-2.5-flash",
        max_tool_rounds: int = 10,
    ):
        api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.mcp_client = mcp_client
        self.max_tool_rounds = max_tool_rounds

    async def run(self, system_prompt: str, task: str) -> str:
        """Run the agent on a task, autonomously calling MCP tools as needed.

        Args:
            system_prompt: Instructions that define the agent's role and behaviour.
            task: The specific task to complete (e.g. "Collect data for these PIRs: ...").

        Returns:
            The agent's final text response after all tool calls are complete.
        """
        # Discover available tools from the MCP server
        available_tools = await self._get_tool_declarations()
        logger.info(f"[GeminiAgent] Starting run with {len(available_tools)} tools available")

        # Build initial message history
        contents = [
            types.Content(
                role="user",
                parts=[types.Part(text=task)],
            )
        ]

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=available_tools,
        )

        # Tool-use loop
        for round_num in range(self.max_tool_rounds):
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )

            candidate = response.candidates[0]

            # Check if the model wants to call tools
            tool_calls = [
                part for part in candidate.content.parts
                if part.function_call is not None
            ]

            if not tool_calls:
                # No tool calls — agent is done, return final text
                text = "".join(
                    part.text for part in candidate.content.parts
                    if part.text is not None
                )
                logger.info(f"[GeminiAgent] Completed in {round_num + 1} round(s)")
                return text

            # Execute all requested tool calls
            logger.info(f"[GeminiAgent] Round {round_num + 1}: {len(tool_calls)} tool call(s)")
            contents.append(candidate.content)

            tool_results = []
            for part in tool_calls:
                fc = part.function_call
                logger.info(f"[GeminiAgent] Calling tool: {fc.name}({dict(fc.args)})")
                try:
                    result = await self.mcp_client.call_tool(fc.name, dict(fc.args))
                    result_text = result if isinstance(result, str) else json.dumps(result)
                except Exception as e:
                    result_text = f"Tool error: {type(e).__name__}: {e}"
                    logger.error(f"[GeminiAgent] Tool {fc.name} failed: {e}")

                tool_results.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=fc.name,
                            response={"result": result_text},
                        )
                    )
                )

            contents.append(
                types.Content(role="tool", parts=tool_results)
            )

        # Safety: max rounds reached — return whatever the model last said
        logger.warning(f"[GeminiAgent] Max tool rounds ({self.max_tool_rounds}) reached")
        last_text = "".join(
            part.text for part in candidate.content.parts
            if part.text is not None
        )
        return last_text or "Agent reached maximum tool iterations without completing."

    async def _get_tool_declarations(self) -> list:
        """Fetch available tools from the MCP server and convert to Gemini format."""
        raw_tools = await self.mcp_client.list_tools()
        declarations = []
        for tool in raw_tools:
            declarations.append(
                types.Tool(
                    function_declarations=[
                        types.FunctionDeclaration(
                            name=tool["name"],
                            description=tool.get("description", ""),
                        )
                    ]
                )
            )
        return declarations
