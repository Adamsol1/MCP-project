"""MCP Threat Intelligence Server.

This server provides tools, resources, and prompts for the
Threat Intelligence workflow (Direction, Collection, Processing phases).
"""

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

""" print("Starting MCP Threat Intelligence Server...", flush=True)

api_key = os.getenv("GEMINI_API_KEY")


print(f"API KEY FOUND: {bool(api_key)}", flush=True)

client = genai.Client(api_key=api_key) """


mcp = FastMCP(
    name="ThreatIntelligence",
    instructions="MCP server for Threat Intelligence workflow assistance.",
)

LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
MODEL = "zai-org/glm-4.7-flash"


def query_local_llm(prompt: str) -> str:
    response = httpx.post(
        LM_STUDIO_URL,
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "stream": False,
        },
        timeout=120.0,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


@mcp.tool
def greet() -> str:
    """Test tool to verify the server is running."""
    prompt = """You are a senior threat intelligence analyst. Generate a formal Priority Intelligence Requirement (PIR) document based on the following context.

        For this task look at Russia's attack against nordic countries' energy infrastructure in the last 6 months. If you are missing information to complete the PIR, make reasonable assumptions based on your knowledge of the world and the context provided. Be specific and actionable in your PIR.

        INVESTIGATION CONTEXT:
        - Scope:
        - Timeframe:
        - Target Entities:
        - Analytical Perspectives:

        For

        PIR DOCUMENT STRUCTURE (use these exact section headers):
        1. PIR Statement: One clear sentence stating the core intelligence need
        2. Essential Elements of Information (EEIs): 3-5 specific questions the collection phase must answer
        4. Priority Level: HIGH / MEDIUM / LOW with a one-sentence justification
        5. Success Criteria: How we will know when the PIR is satisfied

        Generate a professional, actionable PIR document. Be specific — avoid vague language.

        Follow the exact structure below and ensure all sections are completed.
        Return JSON:
        {
            "result":"human readable result",
            "pir":"list of all pirs",
            "reasoning":"explain the logic used"
        }

        in the result field, provide a human-readable summary of the PIR. In the pir field, list all the PIRs generated. In the reasoning field, explain the logic and assumptions you used to create the PIR document.
        for pir, make multiple max 3 PIRs if possible, and make sure they are specific and actionable.
        Respond ONLY in valid JSON.
        No markdown.
        No commentary.
        """

    result = query_local_llm(prompt)

    return f"Local LLM Response: {result}"


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
