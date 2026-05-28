"""Eval Sentinel — demo entrypoint (pretty terminal UI via `rich`).

Builds an InMemoryRunner over root_agent and fires the regression trigger,
streaming the agent's plan, reasoning, tool calls, tool results, and final
postmortem as a polished terminal view. THIS RUN IS THE DEMO.

Run:  ./.venv/bin/python -m src.run

Mirrors RHODES' incident-coordinator entry: a single trigger kicks off the
detect -> root-cause -> fix -> verify -> report loop, with an approval gate
guarding promotion of the fix.
"""

import asyncio

from dotenv import load_dotenv

load_dotenv()

from google.adk.runners import InMemoryRunner
from google.genai import types as gtypes
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from .agent import root_agent

APP_NAME = "eval_sentinel"
USER_ID = "operator"

TRIGGER = (
    "An eval regression was detected on the support-tickets classifier. "
    "Investigate, root-cause, fix, and verify."
)

console = Console()
# Remember per-category scores across the run to render a final before/after.
STATE: dict = {}


def _score_cell(value) -> Text:
    """Color a 0-100 accuracy: green if high, red if zero/low, yellow mid."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return Text(str(value))
    color = "green" if v >= 90 else ("red" if v < 50 else "yellow")
    return Text(f"{v:.0f}%", style=f"bold {color}")


def _fmt_args(args: dict) -> str:
    parts = []
    for k, v in (args or {}).items():
        s = str(v)
        if len(s) > 120:
            s = s[:120] + f"… ({len(str(v))} chars)"
        parts.append(f"{k}={s}")
    return ", ".join(parts)


def _render_tool_call(name: str, args: dict) -> None:
    console.print(Text(f"  → calling {name}({_fmt_args(args)})", style="dim italic yellow"))


def _render_tool_result(name: str, result) -> None:
    if not isinstance(result, dict):
        console.print(Text(f"  ← {name}: {str(result)[:300]}", style="dim"))
        return

    # detect_regression -> before/after comparison table
    if "regressed_categories" in result:
        base = result.get("baseline", {}).get("per_category", {})
        cur = result.get("current", {}).get("per_category", {})
        STATE["baseline"] = base
        STATE["current"] = cur
        t = Table(title="Regression detected", title_style="bold red",
                  border_style="red", show_lines=False)
        t.add_column("Category"); t.add_column("Baseline", justify="center")
        t.add_column("Current", justify="center"); t.add_column("", justify="center")
        for cat in base:
            flag = Text("▼ regressed", style="bold red") if cat in result.get("regressed_categories", []) else Text("ok", style="green")
            t.add_row(cat, _score_cell(base.get(cat)), _score_cell(cur.get(cat)), flag)
        console.print(t)
        console.print(Text(f"  overall accuracy delta: {result.get('overall_delta')} points", style="bold red"))

    elif "failing" in result:
        n = len(result.get("failing", []))
        console.print(Text(
            f"  ← root-cause evidence: {n} '{result.get('category')}' tickets failed, "
            f"all misclassified as {result.get('misclassified_as')}", style="dim"))

    # verify_fix -> recovery table
    elif "per_category" in result:
        fix = result.get("per_category", {})
        STATE["fix"] = fix
        STATE["fix_experiment_id"] = result.get("experiment_id")
        t = Table(title="Fix verified (live re-evaluation)", title_style="bold green",
                  border_style="green")
        t.add_column("Category"); t.add_column("After fix", justify="center")
        for cat, val in fix.items():
            t.add_row(cat, _score_cell(val))
        console.print(t)
        console.print(Text(f"  overall after fix: {result.get('overall')}%  "
                           f"(new experiment: {result.get('experiment_id')})", style="green"))
    else:
        console.print(Text(f"  ← {name}: {list(result.keys())}", style="dim"))


def _render_final_summary() -> None:
    base, cur, fix = STATE.get("baseline"), STATE.get("current"), STATE.get("fix")
    if base and cur and fix:
        t = Table(title="Before → After", title_style="bold cyan", border_style="cyan")
        t.add_column("Category")
        t.add_column("Baseline", justify="center")
        t.add_column("Regressed", justify="center")
        t.add_column("Healed", justify="center")
        for cat in base:
            t.add_row(cat, _score_cell(base.get(cat)), _score_cell(cur.get(cat)), _score_cell(fix.get(cat)))
        console.print(t)
    console.print(Panel(
        Text.assemble(
            ("Fix is a PROPOSAL — not yet live.\n", "bold yellow"),
            ("Promoting the corrected prompt to production requires human approval.", "yellow"),
        ),
        title="⚖  Approval gate", border_style="yellow"))


async def main() -> None:
    console.print(Panel(
        Text.assemble(
            ("EVAL SENTINEL\n", "bold cyan"),
            ("autonomous LLM-eval healing agent — Gemini 3 · Arize Phoenix MCP", "dim"),
        ), border_style="cyan"))
    console.print(Text(f"Trigger: {TRIGGER}", style="italic dim"))
    console.print(Rule(style="cyan"))

    runner = InMemoryRunner(agent=root_agent, app_name=APP_NAME)
    session = await runner.session_service.create_session(app_name=APP_NAME, user_id=USER_ID)
    message = gtypes.Content(role="user", parts=[gtypes.Part(text=TRIGGER)])

    async for event in runner.run_async(user_id=USER_ID, session_id=session.id, new_message=message):
        content = getattr(event, "content", None)
        if content is None or not getattr(content, "parts", None):
            continue
        for part in content.parts:
            text = getattr(part, "text", None)
            if text and text.strip():
                console.print(Markdown(text.strip()))
            fc = getattr(part, "function_call", None)
            if fc is not None:
                _render_tool_call(fc.name, dict(fc.args or {}))
            fr = getattr(part, "function_response", None)
            if fr is not None:
                _render_tool_result(fr.name, fr.response)

    console.print(Rule(style="cyan"))
    _render_final_summary()


if __name__ == "__main__":
    asyncio.run(main())
