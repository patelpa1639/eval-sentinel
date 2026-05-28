"""Eval Sentinel — demo entrypoint.

Builds an InMemoryRunner over root_agent and fires the regression trigger,
streaming the agent's reasoning, tool calls, tool results, and final
postmortem to stdout. THIS RUN IS THE DEMO.

Run:  ./.venv/bin/python -m src.run

Mirrors RHODES' incident-coordinator entry: a single trigger kicks off the
detect -> root-cause -> fix -> verify -> report loop, with an approval gate
guarding promotion of the fix.
"""

import asyncio
import os

from dotenv import load_dotenv

load_dotenv()

from google.adk.runners import InMemoryRunner
from google.genai import types as gtypes

from .agent import root_agent

APP_NAME = "eval_sentinel"
USER_ID = "operator"

TRIGGER = (
    "An eval regression was detected on the support-tickets classifier. "
    "Investigate, root-cause, fix, and verify."
)


def _fmt_args(args: dict) -> str:
    """Render tool-call args compactly; truncate long prompt bodies."""
    parts = []
    for k, v in (args or {}).items():
        s = str(v)
        if len(s) > 200:
            s = s[:200] + f"... ({len(str(v))} chars)"
        parts.append(f"{k}={s}")
    return ", ".join(parts)


def _print_tool_result(name: str, result) -> None:
    """Summarize a tool result so the stream stays readable but informative."""
    if not isinstance(result, dict):
        print(f"  <- {name}: {str(result)[:300]}")
        return

    if "regressed_categories" in result:
        b = result.get("baseline", {}).get("per_category", {})
        c = result.get("current", {}).get("per_category", {})
        print(f"  <- {name}: overall_delta={result.get('overall_delta')} "
              f"regressed={result.get('regressed_categories')}")
        print(f"       baseline per_category: {b}")
        print(f"       current  per_category: {c}")
    elif "failing" in result:
        print(f"  <- {name}: category={result.get('category')} "
              f"failures={len(result.get('failing', []))} "
              f"misclassified_as={result.get('misclassified_as')}")
    elif "per_category" in result:
        print(f"  <- {name}: overall={result.get('overall')} "
              f"per_category={result.get('per_category')} "
              f"experiment_id={result.get('experiment_id')}")
    else:
        keys = list(result.keys())
        print(f"  <- {name}: dict keys={keys}")


async def main() -> None:
    print("=" * 70)
    print("EVAL SENTINEL — autonomous LLM-eval healing agent")
    print("=" * 70)
    print(f"Trigger: {TRIGGER}\n")

    runner = InMemoryRunner(agent=root_agent, app_name=APP_NAME)
    session = await runner.session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID
    )

    message = gtypes.Content(role="user", parts=[gtypes.Part(text=TRIGGER)])

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session.id,
        new_message=message,
    ):
        content = getattr(event, "content", None)
        if content is None or not getattr(content, "parts", None):
            continue

        for part in content.parts:
            # Agent reasoning / final report text.
            text = getattr(part, "text", None)
            if text and text.strip():
                print(text.strip())
                print()

            # Tool calls.
            fc = getattr(part, "function_call", None)
            if fc is not None:
                print(f"  -> tool call: {fc.name}({_fmt_args(dict(fc.args or {}))})")

            # Tool results.
            fr = getattr(part, "function_response", None)
            if fr is not None:
                _print_tool_result(fr.name, fr.response)

    print("=" * 70)
    print("Eval Sentinel run complete. Fix is a PROPOSAL — promotion requires")
    print("human approval (approval gate).")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
