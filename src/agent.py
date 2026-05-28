"""Eval Sentinel — autonomous LLM-eval agent for the GCP Rapid Agent Hackathon.

Stack: ADK (Python) + Gemini 3 + Arize Phoenix MCP, deployed to Agent Engine.

Loop: pull evals/traces via Phoenix MCP -> reason with Gemini 3 ->
detect regressions/drift -> root-cause failing spans -> file a fix proposal.

NOTE: The ADK import surface shifts between versions. Once `google-adk` finishes
installing, we verify these imports against the installed version and adjust.
"""

import os

from dotenv import load_dotenv

load_dotenv()

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")

# --- ADK agent + Arize Phoenix MCP (google-adk 2.1.0) ---
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import (
    McpToolset,
    StdioConnectionParams,
    StdioServerParameters,
)

# Phoenix MCP server (npx stdio). Reads PHOENIX_HOST + PHOENIX_API_KEY from env.
_phoenix_env = {
    **os.environ,
    "PHOENIX_HOST": os.environ.get("PHOENIX_COLLECTOR_ENDPOINT", ""),
    "PHOENIX_API_KEY": os.environ.get("PHOENIX_API_KEY", ""),
}

phoenix_tools = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="npx",
            args=["-y", "@arizeai/phoenix-mcp@latest"],
            env=_phoenix_env,
        ),
        timeout=60,
    )
)

INSTRUCTION = """You are Eval Sentinel, an autonomous agent that safeguards the
quality of an LLM application. Using the Arize Phoenix tools available to you:
1. Pull the latest evaluation runs and traces.
2. Compare against the prior baseline to detect regressions or drift.
3. For any regression, inspect the failing spans and root-cause the issue.
4. Produce a concise, actionable fix proposal (prompt change, model param, or
   data fix) with the supporting eval evidence.
Be specific and cite the span/eval ids you relied on."""

root_agent = Agent(
    name="eval_sentinel",
    model=GEMINI_MODEL,
    instruction=INSTRUCTION,
    tools=[phoenix_tools],
)


if __name__ == "__main__":
    print(f"Eval Sentinel agent defined. Model: {GEMINI_MODEL}")
    print("Run via `adk run src` once gcloud auth + .env are configured.")
