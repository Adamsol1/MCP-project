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
import re
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
        status_tracker=None,
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
            try:
                response = await self.client.aio.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=config,
                )
            except BaseException as e:
                if isinstance(e, ExceptionGroup):
                    logger.error(f"[GeminiAgent] ExceptionGroup unwrapped: {e.exceptions[0]}")
                    raise e.exceptions[0] from e
                raise

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
                _args_safe = repr(dict(fc.args)).encode("ascii", errors="backslashreplace").decode("ascii")
                logger.info(f"[GeminiAgent] Calling tool: {fc.name}({_args_safe})")
                if status_tracker is not None:
                    status_tracker.record_tool_call(fc.name, dict(fc.args))
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

    # Phrases that indicate Gemini could not access the page.
    _INACCESSIBLE_PHRASES: tuple[str, ...] = (
        "not accessible", "unable to access", "cannot access", "could not access",
        "access denied", "access is denied", "403", "404 not found",
        "page not found", "could not fetch", "failed to fetch", "error fetching",
        "blocked", "paywall", "subscription required", "behind a paywall",
        "login required", "sign in required", "no content available",
    )

    async def fetch_url_summaries(
        self,
        urls: list[str],
        pir: str,
        perspectives: list[str],
        batch_size: int = 15,
    ) -> list[dict]:
        """Second-pass: fetch and summarise web pages using Gemini url_context.

        Makes a separate Gemini call with the url_context built-in tool — no MCP
        tools, no scraping. Gemini fetches each URL server-side through Google's
        infrastructure.

        Pages that are inaccessible (paywalled, 403/404, blocked) are silently
        skipped so they don't pollute the collected data or the source count.

        Returns a list of collected_data-compatible dicts with source="fetch_page".
        """
        if not urls:
            return []

        results: list[dict] = []
        perspectives_str = ", ".join(perspectives) if perspectives else "neutral"

        for i in range(0, len(urls), batch_size):
            batch = urls[i : i + batch_size]
            url_list = "\n".join(f"- {url}" for url in batch)

            prompt = (
                f"PIR (Priority Intelligence Requirement): {pir}\n"
                f"Analysis perspectives: {perspectives_str}\n\n"
                f"Fetch and read each URL listed below. For EACH page that is accessible:\n"
                f"1. Extract the article title, author name(s), publication date, and publisher/website name.\n"
                f"2. Write a concise intelligence-focused summary (3-5 sentences) highlighting facts "
                f"and analysis directly relevant to the PIR.\n"
                f"3. Construct a correctly formatted APA 7th edition citation.\n\n"
                f"IMPORTANT: If a page is inaccessible, blocked, paywalled, returns a 403/404 error, "
                f"or has no readable content, OMIT it entirely from the response — do not include it.\n\n"
                f"Source authority hierarchy — prioritise pages in this order:\n"
                f"1. Government & official sources (.gov, .mil, official agency/ministry sites)\n"
                f"2. Established research institutions & think tanks (CSIS, RAND, Chatham House, RUSI, CFR, etc.)\n"
                f"3. Trusted international news outlets (Reuters, BBC, AP News, Financial Times, etc.)\n"
                f"4. Other credible sources\n\n"
                f"APA format: Author, A. A. (Year, Month Day). Title of article. Publisher. URL\n"
                f"- If author is unknown use the publisher/website name as author.\n"
                f"- If date is unknown omit it.\n"
                f"- Dates must use the format: YYYY, Month DD (e.g. 2026, March 15).\n\n"
                f"URLs to fetch:\n{url_list}\n\n"
                f"Respond ONLY with valid JSON — no markdown fences, no explanation.\n"
                f"Only include accessible pages. Omit inaccessible ones entirely:\n"
                f'{{"page_summaries": ['
                f'{{"url": "...", "title": "...", "author": "Last, F. M. or null", '
                f'"date": "YYYY-MM-DD or null", "publisher": "...", '
                f'"apa_citation": "...", "summary": "..."}}'
                f']}}'
            )

            try:
                try:
                    response = await self.client.aio.models.generate_content(
                        model=self.model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            tools=[{"url_context": {}}],
                        ),
                    )
                except BaseException as e:
                    if isinstance(e, ExceptionGroup):
                        logger.error(f"[GeminiAgent] ExceptionGroup unwrapped: {e.exceptions[0]}")
                        raise e.exceptions[0] from e
                    raise
                # Gemini can return a response with no candidates or with a candidate
                # whose content is None — this happens when the response is blocked by
                # safety filters, hits a rate limit, or the model declines to answer.
                # Accessing .content.parts on a None candidate raises AttributeError,
                # so we guard here and skip the batch rather than crashing the whole pass.
                candidate = response.candidates[0] if response.candidates else None
                if candidate is None or candidate.content is None:
                    logger.warning(
                        f"[GeminiAgent] url_context batch {i // batch_size + 1}: "
                        f"empty or blocked response (finish_reason={getattr(candidate, 'finish_reason', 'N/A')}), skipping"
                    )
                    continue
                text = "".join(
                    part.text
                    for part in candidate.content.parts
                    if part.text is not None
                )
                fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
                text = fence.group(1).strip() if fence else text.strip()
                parsed = json.loads(text)
                batch_results = 0
                batch_skipped = 0
                for item in parsed.get("page_summaries", []):
                    if not item.get("url") or not item.get("summary"):
                        batch_skipped += 1
                        continue
                    # Skip pages Gemini flagged as inaccessible
                    summary_lower = item["summary"].lower()
                    if any(phrase in summary_lower for phrase in self._INACCESSIBLE_PHRASES):
                        logger.info(f"[GeminiAgent] Skipping inaccessible URL: {item['url']}")
                        batch_skipped += 1
                        continue
                    citation = item.get("apa_citation", "")
                    content = (
                        f"[{item.get('title', 'Article')}]\n"
                        f"{item['summary']}"
                    )
                    if citation:
                        content += f"\n\nCitation: {citation}"
                    results.append({
                        "source": "fetch_page",
                        "resource_id": item["url"],
                        "content": content,
                        "apa_citation": citation,
                        "author": item.get("author"),
                        "date": item.get("date"),
                        "publisher": item.get("publisher"),
                        "title": item.get("title"),
                    })
                    batch_results += 1
                logger.info(
                    f"[GeminiAgent] url_context batch {i // batch_size + 1}: "
                    f"{batch_results} accessible, {batch_skipped} skipped"
                )
            except Exception as e:
                logger.error(f"[GeminiAgent] url_context batch failed: {e}")

        return results

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
