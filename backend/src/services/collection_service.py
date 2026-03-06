"""CollectionService

  For each collection phase we:
    1.Backend fetches the system prompt from mcp server and sends it to an geminiagent.
    2.Geminiagent will run this system prompts, and will choose what allowed tools it sees as relevant.
    3.The agent will collect data and return to backend.
    4.Backend returns the summary to the collectionflow that will send to frontend for user approval.
"""

import json
import logging

from src.mcp_client.client import MCPClient
from src.services.gemini_agent import GeminiAgent

logger = logging.getLogger("app")


class CollectionService:

    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client

    async def generate_collection_plan(self, pir: str, modifications: str | None = None) -> str:
        """
        Method to call AI to make it generate an collection plan based on PIR and knowledge bank.

        Args:
          pir : The PIR generated in the direction phase. Serves as the context for the collection goal
          modifications: User modifications. Changes that the user wants the AI to make on the generated plan. e.g (Include OTX as a source)

        Returns:
        A string with the collection plan
        """
        #Connect to the mcp client
        async with self.mcp_client.connect():
            #Get the system prompt from the mcp server
            system_prompt = await self.mcp_client.get_prompt(
                "collection_plan",
                {
                    "pir": pir,
                    "modifications": modifications or "",
                },
            )
            #Create Agent
            agent = GeminiAgent(self.mcp_client)
            ai_output = await agent.run(
                system_prompt=system_prompt,
                task="Generate a collection plan and suggest relevant sources for the given PIRs.",
            )
        #Return the content that the AI generated
        return ai_output

    async def suggest_sources(self, plan_json: str) -> list[str]:
        # Parse suggested sources from the collection plan JSON output
        data = json.loads(plan_json)
        return data.get("suggested_sources", ["Internal Knowledge Bank"])

    async def collect(self, selected_sources: list[str], pir: str, plan: str, language: str = "en") -> dict:
        # Two-step collection:
        # Step 1: Agent calls tools and returns raw data
        # Step 2: Agent summarizes raw data (no tools needed)
        # plan may be full JSON from generate_collection_plan() — extract text if so
        try:
            plan_text = json.loads(plan).get("plan", plan)
        except (json.JSONDecodeError, TypeError):
            plan_text = plan

        async with self.mcp_client.connect():
            #Step 1: Collect raw data via tools
            collect_prompt = await self.mcp_client.get_prompt(
                "collection_collect",
                {
                    "pir": pir,
                    "selected_sources": json.dumps(selected_sources),
                    "plan": plan_text,
                },
            )
            agent = GeminiAgent(self.mcp_client)
            raw_data = await agent.run(
                system_prompt=collect_prompt,
                task="Collect raw intelligence data from the approved sources based on the PIRs.",
            )

            #Step 2: Summarize raw data (one-shot, no tools)
            summarize_prompt = await self.mcp_client.get_prompt(
                "collection_summarize",
                {
                    "pir": pir,
                    "collected_data": raw_data,
                    "language": language,
                },
            )
            agent2 = GeminiAgent(self.mcp_client)
            summary = await agent2.run(
                system_prompt=summarize_prompt,
                task="Summarize the collected intelligence data.",
            )

        return {"raw_data": raw_data, "summary": summary}

    async def modify_summary(self, collected_data: str, modifications: str) -> str:
        async with self.mcp_client.connect():
          system_prompt = await self.mcp_client.get_prompt(
              "collection_modify",
              {
                  "collected_data": collected_data,
                  "modifications": modifications,
              },
          )
          agent = GeminiAgent(self.mcp_client)
          ai_output = await agent.run(
            system_prompt=system_prompt,
            task="Apply the requested modifications to the existing intelligence summary.",
        )
        return ai_output
