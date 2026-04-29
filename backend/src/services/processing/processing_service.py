import json
import logging

from src.mcp_client.client import MCPClient
from src.services.ai.gemini_agent import GeminiAgent

logger = logging.getLogger("app")

_PROCESSING_TOOLS = [
    "list_knowledge_base",
    "read_knowledge_base",
    "google_search",
]


class ProcessingService:
    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client

    async def process(
        self,
        collected_data: str,
        pir: str,
        feedback: str | None = None,
        previous_result: str | None = None,
        language: str = "en",
    ) -> str:
        async with self.mcp_client.connect():
            system_prompt = await self.mcp_client.get_prompt(
                "processing_process",
                {
                    "pir": pir,
                    "collected_data": collected_data,
                    "feedback": feedback or "",
                    "previous_result": previous_result or "",
                    "language": language,
                },
            )
            agent = GeminiAgent(self.mcp_client)
            raw = await agent.run(
                system_prompt=system_prompt,
                task="Process the collected intelligence data into structured PMESII entities.",
                allowed_tool_names=set(_PROCESSING_TOOLS),
            )

        # Inject reasoning from Gemini thinking tokens if not already in the JSON.
        if agent.last_thought_text:
            try:
                parsed = json.loads(raw)
                if not parsed.get("reasoning"):
                    parsed["reasoning"] = agent.last_thought_text
                return json.dumps(parsed, ensure_ascii=False)
            except (json.JSONDecodeError, AttributeError):
                pass
        return raw

    async def modify_processing(
        self,
        existing_result: str,
        modifications: str,
        language: str = "en",
    ) -> str:
        async with self.mcp_client.connect():
            system_prompt = await self.mcp_client.get_prompt(
                "processing_modify",
                {
                    "existing_result": existing_result,
                    "modifications": modifications,
                    "language": language,
                },
            )
            agent = GeminiAgent(self.mcp_client)
            return await agent.run(
                system_prompt=system_prompt,
                task="Apply the requested modifications to the existing processing result.",
            )
