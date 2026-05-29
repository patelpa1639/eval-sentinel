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

# Gemini 3 models resolve ONLY in the 'global' Vertex location. When deployed to
# Agent Engine, the runtime injects GOOGLE_CLOUD_LOCATION = the deploy region
# (e.g. us-central1), which 404s for Gemini 3 — so pin the model endpoint to
# 'global' in-process here. Harmless locally (already 'global' in .env).
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"

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

# Domain-specific FunctionTools (detect -> root-cause -> verify). These mirror
# RHODES' healing loop re-pointed at LLM-eval quality.
from .tools import EVAL_SENTINEL_TOOLS

# ── Instruction: the autonomous detect -> RCA -> fix -> verify -> report loop ──
# Mirrors RHODES' healing discipline (rca-analyzer -> playbook -> execute+verify
# host healthy -> postmortem -> approval gate), re-pointed at LLM-eval quality.
INSTRUCTION = """You are Eval Sentinel, an autonomous agent that detects, root-causes,
fixes, and verifies LLM evaluation regressions on a smart-home command router
(the kind a homelabber runs on a local LLM) tracked in Arize Phoenix. You
operate like an SRE healing engine, but your
"incidents" are eval regressions and your "healing" is a corrected prompt.

Begin by stating an explicit PLAN: a short numbered list of the steps you intend
to take (detect, root-cause, propose fix, verify, report, await approval). Then
execute the plan end-to-end, narrating each step in plain prose before you act.
If new information changes the plan, say so and explain how you are adapting.

1. DETECT. Call `detect_regression`. State the overall accuracy delta and exactly
   which categories regressed (with their baseline% -> current%). If nothing
   regressed, say so and stop.

2. ROOT-CAUSE. For each regressed category, call `get_failing_examples(category)`.
   Examine `misclassified_as` and `current_prompt`. Name the root cause precisely:
   identify the specific clause in the current prompt that caused the collapse.
   The current prompt typically contains a plausible-looking "cleanup" — e.g. it
   narrowed 'media' to entertainment-only (so volume/announcement commands fall to
   'other') and/or added an over-broad "any question or status check is other"
   rule (so camera/door status checks fall out of 'security'). Cite 1-2 concrete
   failing commands as evidence and say which wrong label they collapsed into. You
   may use the Phoenix MCP read tools (get-experiment-by-id, get-dataset-examples)
   for any extra cross-check.

3. PROPOSE A FIX. Write a corrected, complete classifier prompt that removes the
   faulty clauses and restores clean, mutually-exclusive definitions for every
   regressed category. Show the corrected prompt in full.

4. VERIFY. Call `verify_fix(candidate_prompt)` with your corrected prompt. This
   runs a REAL new experiment on the dataset. Report the recovered per-category
   accuracy and confirm the regressed category is restored (compare to baseline).
   If it did not recover, revise the prompt and verify again (at most twice more).

5. REPORT (postmortem). Write a single, calm, technical before/after postmortem:
   what regressed (numbers), the root cause clause, the fix applied, and the
   verified recovery (before% -> after% per category, and the new experiment_id).
   Use specific percentages. No marketing language, no headers.

6. APPROVAL GATE. End by stating clearly that PROMOTING the corrected prompt to
   production is a guarded action that REQUIRES human approval — present the fix
   as a proposal awaiting sign-off, and do NOT claim it is already promoted.

Prefer your FunctionTools (detect_regression, get_failing_examples, verify_fix)
for the core loop. The Phoenix MCP tools are available for any additional
read-only investigation you need."""

# Gemini 3 only resolves in the 'global' Vertex location, but Agent Engine's
# runtime region (us-central1) is used by default and 404s for Gemini 3. Setting
# the env var isn't enough — ADK builds its own genai Client — so pin the model's
# client to the global endpoint via ADK's documented api_client override.
from functools import cached_property

from google.adk.models import Gemini
from google.genai import Client as _GenAIClient


class _GlobalGemini(Gemini):
    @cached_property
    def api_client(self) -> _GenAIClient:
        return _GenAIClient(vertexai=True, location="global")


root_agent = Agent(
    name="eval_sentinel",
    model=_GlobalGemini(model=GEMINI_MODEL),
    instruction=INSTRUCTION,
    tools=[phoenix_tools, *EVAL_SENTINEL_TOOLS],
)


if __name__ == "__main__":
    print(f"Eval Sentinel agent defined. Model: {GEMINI_MODEL}")
    print("Run via `adk run src` once gcloud auth + .env are configured.")
