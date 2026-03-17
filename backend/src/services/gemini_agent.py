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


def _json_schema_to_gemini(schema: dict) -> types.Schema:
    """Convert a JSON Schema dict to a Gemini types.Schema object.

    Used to pass MCP tool inputSchemas to Gemini so it knows what
    arguments each tool accepts. Called recursively for nested objects.
    """
    type_map = {
        "string": types.Type.STRING,
        "integer": types.Type.INTEGER,
        "boolean": types.Type.BOOLEAN,
        "number": types.Type.NUMBER,
        "array": types.Type.ARRAY,
        "object": types.Type.OBJECT,
    }
    schema_type = type_map.get(schema.get("type", "string"), types.Type.STRING)
    properties = {
        k: _json_schema_to_gemini(v) for k, v in schema.get("properties", {}).items()
    }
    return types.Schema(
        type=schema_type,
        description=schema.get("description"),
        properties=properties or None,
        required=schema.get("required"),
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
        model:           Gemini model ID to use.
        mcp_client:      Connected MCPClient instance for tool execution.
        max_tool_rounds: Safety limit on tool-call iterations (prevents infinite loops).
    """

    def __init__(
        self,
        mcp_client,
        model: str = "gemini-2.5-flash",
        max_tool_rounds: int = 50,
    ):
        api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.mcp_client = mcp_client
        self.max_tool_rounds = max_tool_rounds

    async def run(
        self,
        system_prompt: str,
        task: str,
        allowed_tool_names: set[str] | None = None,
    ) -> str:
        """Run the agent on a task, autonomously calling MCP tools as needed.

        Args:
            system_prompt:      Instructions that define the agent's role and behaviour.
            task:               The specific task to complete.
            allowed_tool_names: When provided, only tools in this set are exposed to
                                the model. Enforces source selection at the API level
                                rather than relying on prompt instructions alone.

        Returns:
            The agent's final text response after all tool calls are complete.
        """
        available_tools = await self._get_tool_declarations(allowed_tool_names)
        logger.info(f"[GeminiAgent] Starting run with {len(available_tools)} tools available")

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

        for round_num in range(self.max_tool_rounds):
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )

            candidate = response.candidates[0]
            tool_calls = [
                part
                for part in candidate.content.parts
                if part.function_call is not None
            ]

            if not tool_calls:
                text = "".join(
                    part.text
                    for part in candidate.content.parts
                    if part.text is not None
                )
                logger.info(f"[GeminiAgent] Completed in {round_num + 1} round(s)")
                return text

            logger.info(f"[GeminiAgent] Round {round_num + 1}: {len(tool_calls)} tool call(s)")
            contents.append(candidate.content)

            tool_results = []
            for part in tool_calls:
                fc = part.function_call
                logger.info(f"[GeminiAgent] Calling tool: {fc.name}({dict(fc.args)})")
                try:
                    result = await self.mcp_client.call_tool(fc.name, dict(fc.args))
                    result_text = (
                        result if isinstance(result, str) else json.dumps(result)
                    )
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

            contents.append(types.Content(role="tool", parts=tool_results))

        logger.warning(f"[GeminiAgent] Max tool rounds ({self.max_tool_rounds}) reached")
        last_text = "".join(
            part.text for part in candidate.content.parts if part.text is not None
        )
        return last_text or "Agent reached maximum tool iterations without completing."

    async def _get_tool_declarations(self, allowed_tool_names: set[str] | None = None) -> list:
        """Fetch available tools from the MCP server and convert to Gemini format.

        When allowed_tool_names is provided, only tools in that set are returned,
        enforcing source selection at the function-declaration level.
        """
        raw_tools = await self.mcp_client.list_tools()
        declarations = []
        for tool in raw_tools:
            if allowed_tool_names is not None and tool["name"] not in allowed_tool_names:
                continue
            input_schema = tool.get("inputSchema", {})
            parameters = (
                _json_schema_to_gemini(input_schema)
                if input_schema.get("properties")
                else None
            )
            declarations.append(
                types.Tool(
                    function_declarations=[
                        types.FunctionDeclaration(
                            name=tool["name"],
                            description=tool.get("description", ""),
                            parameters=parameters,
                        )
                    ]
                )
            )
        return declarations
