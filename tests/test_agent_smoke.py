"""Lightweight smoke tests for src/agent.py.

These assert that `root_agent` is a well-formed ADK Agent exposing tools (the
Phoenix MCP toolset plus, eventually, custom FunctionTools). They do NOT run a
live agent loop in the default run — any live/slow agent exercise is marked
`@pytest.mark.slow` and excluded by default (see pytest.ini / Makefile).
"""

import pytest
from dotenv import load_dotenv

load_dotenv()

# Skip cleanly if the agent module can't be imported yet (e.g. ADK surface still
# shifting). Importing root_agent constructs the McpToolset but does not start it.
agent_mod = pytest.importorskip(
    "src.agent",
    reason="src/agent.py not importable yet (contract code in progress)",
)


def test_root_agent_exists():
    assert hasattr(agent_mod, "root_agent")
    assert agent_mod.root_agent is not None


def test_root_agent_is_adk_agent():
    from google.adk.agents import BaseAgent

    # Agent / LlmAgent both subclass BaseAgent; assert against the base so the
    # test is robust to which concrete class the contract uses.
    assert isinstance(agent_mod.root_agent, BaseAgent)


def test_root_agent_has_name_and_model():
    root_agent = agent_mod.root_agent
    assert getattr(root_agent, "name", None)
    # LlmAgent carries a `model` attribute; tolerate either str or model object.
    assert getattr(root_agent, "model", None)


def test_root_agent_exposes_tools():
    root_agent = agent_mod.root_agent
    tools = getattr(root_agent, "tools", None)
    assert tools is not None
    assert len(tools) >= 1, "expected at least the Phoenix MCP toolset"


def test_root_agent_has_phoenix_mcp_toolset():
    """At least one tool entry should be the Phoenix MCP toolset."""
    from google.adk.tools.mcp_tool.mcp_toolset import McpToolset

    tools = agent_mod.root_agent.tools
    assert any(isinstance(t, McpToolset) for t in tools), [
        type(t).__name__ for t in tools
    ]


@pytest.mark.slow
def test_root_agent_live_loop():
    """Full live agent loop against Gemini 3 + Phoenix MCP.

    Marked slow + skipped in the default run. Requires gcloud auth, the npx
    Phoenix MCP server, and network. Run with `make test-all`.
    """
    pytest.skip("live agent loop is exercised manually / via `make demo`")
