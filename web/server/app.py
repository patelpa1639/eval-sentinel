"""Eval Sentinel — web backend (FastAPI).

Exposes the eval state, streams a live agent run over SSE, handles the human
approval gate, and serves the built React frontend.

This service runs the REAL ADK agent loop in-process (the same loop `src/run.py`
drives for the terminal demo) and translates each ADK event into the frozen SSE
event contract the frontend consumes.

Run locally:
    ./.venv/bin/python -m uvicorn web.server.app:app --port 8000

The src modules call load_dotenv() on import, so GOOGLE_CLOUD_PROJECT /
GEMINI_MODEL / PHOENIX_* are pulled from the project-root .env. We never print
or log the PHOENIX_API_KEY.
"""

import asyncio
import json
import logging
import os

from dotenv import load_dotenv

# Load .env from the project root before importing src modules (they also call
# load_dotenv(), but loading here keeps env resolution explicit for the server).
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from starlette.requests import Request

from src import phoenix_ops as po

logger = logging.getLogger("eval_sentinel.web")
logging.basicConfig(level=logging.INFO)

# Public Phoenix deep-link for the dataset's experiments (used by /api/state).
PHOENIX_DATASET_URL = (
    "https://app.phoenix.arize.com/s/patelpa1639/datasets/"
    "RGF0YXNldDoy/experiments"
)

APP_NAME = "eval_sentinel"
USER_ID = "operator"
TRIGGER = (
    "An eval regression was detected on the smart-home command router. "
    "Investigate, root-cause, fix, and verify."
)

app = FastAPI(title="Eval Sentinel", version="1.0.0")

# CORS: the frontend dev server runs on a different port during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── /api/state ────────────────────────────────────────────────────────────────
@app.get("/api/state")
def api_state():
    """Current eval state: baseline vs current scores + regressed categories.

    Computed via po.compare(baseline_experiment_id, current_experiment_id).
    """
    cmp = po.compare(po.baseline_experiment_id(), po.current_experiment_id())
    baseline = cmp.get("baseline", {})
    current = cmp.get("current", {})
    return {
        "dataset": po.DATASET,
        "baseline": {
            "overall": baseline.get("overall"),
            "per_category": baseline.get("per_category", {}),
        },
        "current": {
            "overall": current.get("overall"),
            "per_category": current.get("per_category", {}),
        },
        "regressed_categories": cmp.get("regressed_categories", []),
        "phoenix_url": PHOENIX_DATASET_URL,
    }


# ── SSE: the live agent run ─────────────────────────────────────────────────────
# Phase inference: which lifecycle phase a tool call / narration belongs to.
_TOOL_PHASE = {
    "detect_regression": ("detect", "Detect"),
    "get_failing_examples": ("root_cause", "Root cause"),
    "verify_fix": ("verify", "Verify"),
}


def _tool_result_kind(result: dict):
    """Infer the kind of a tool_result from the result dict shape.

    regressed_categories -> regression
    failing              -> failures
    per_category + experiment_id -> recovery
    """
    if not isinstance(result, dict):
        return None
    if "regressed_categories" in result:
        return "regression"
    if "failing" in result:
        return "failures"
    if "per_category" in result and "experiment_id" in result:
        return "recovery"
    return None


def _failures_payload(result: dict) -> dict:
    """Shape a get_failing_examples result for the SSE failures event."""
    return {
        "category": result.get("category"),
        "failing": [
            {
                "text": f.get("text"),
                "expected": f.get("expected"),
                "predicted": f.get("predicted"),
            }
            for f in (result.get("failing") or [])
        ],
        "misclassified_as": result.get("misclassified_as", {}),
    }


def _recovery_payload(result: dict) -> dict:
    """Shape a verify_fix result for the SSE recovery event (omit examples)."""
    payload = {
        "overall": result.get("overall"),
        "per_category": result.get("per_category", {}),
        "experiment_id": result.get("experiment_id"),
    }
    return {k: v for k, v in payload.items() if v is not None}


def _looks_like_plan(text: str) -> bool:
    """Heuristic: the agent's opening message that lays out a numbered PLAN."""
    low = text.lower()
    if "plan" in low and any(
        m in low for m in ("1.", "1)", "detect", "root-cause", "root cause")
    ):
        return True
    return False


def _extract_fenced_block(text: str):
    """Return the contents of the first ``` fenced code block, or None.

    The agent is instructed to show the corrected classifier prompt "in full",
    which it renders as a fenced code block — the most reliable signal for a
    proposed_prompt event (far more reliable than keyword sniffing on prose).
    """
    if "```" not in text:
        return None
    parts = text.split("```")
    if len(parts) < 3:
        return None
    block = parts[1]
    # Drop an optional language hint on the first line (e.g. ```text / ```python).
    lines = block.split("\n", 1)
    if len(lines) == 2 and " " not in lines[0].strip() and len(lines[0].strip()) < 20:
        block = lines[1]
    return block.strip() or None


def _looks_like_proposed_prompt(text: str, verify_seen: bool) -> bool:
    """Heuristic: the agent is showing the corrected classifier prompt.

    Requires a fenced code block that itself looks like a classifier prompt
    (mentions classify/category + at least one of the smart-home labels), and
    only BEFORE verify has run (the corrected prompt is proposed, then verified).
    """
    if verify_seen:
        return False
    block = _extract_fenced_block(text)
    if not block:
        return False
    low = block.lower()
    has_intent = "classif" in low or "category" in low or "categories" in low
    has_label = any(
        lbl in low for lbl in ("lights", "climate", "media", "security", "other")
    )
    return has_intent and has_label and len(block) > 120


def _looks_like_report(text: str, verify_seen: bool) -> bool:
    """Heuristic: the final postmortem.

    The postmortem is a calm before/after technical summary written AFTER the
    fix is verified. Require verify to have completed and the text to read like a
    before→after recovery summary with concrete numbers.
    """
    if not verify_seen:
        return False
    low = text.lower()
    has_postmortem_signal = any(
        m in low
        for m in (
            "postmortem",
            "before/after",
            "before →",
            "before ->",
            "recovered",
            "restored",
            "regression was detected",
            "root cause",
            "root-cause",
        )
    )
    has_numbers = "%" in low or "baseline" in low
    return has_postmortem_signal and has_numbers


def _sse(payload: dict) -> dict:
    """Format a dict as an sse-starlette event (data field carries the JSON)."""
    return {"data": json.dumps(payload)}


async def _agent_event_stream(request):
    """Drive the real ADK agent loop and yield SSE events per the frozen contract.

    Mirrors src/run.py's event extraction (part.text / part.function_call /
    part.function_response) and maps each to the SSE event shapes.
    """
    # Import inside the handler: building the agent mounts the Phoenix MCP
    # toolset (npx stdio), which we only want to spin up on an actual run.
    from google.adk.runners import InMemoryRunner
    from google.genai import types as gtypes

    from src.agent import root_agent

    emitted_plan = False
    verify_seen = False  # flips once verify_fix has been called
    last_phase = None

    async def emit_phase(phase: str, label: str):
        return _sse({"type": "phase", "phase": phase, "label": label})

    try:
        runner = InMemoryRunner(agent=root_agent, app_name=APP_NAME)
        session = await runner.session_service.create_session(
            app_name=APP_NAME, user_id=USER_ID
        )
        message = gtypes.Content(role="user", parts=[gtypes.Part(text=TRIGGER)])

        async for event in runner.run_async(
            user_id=USER_ID, session_id=session.id, new_message=message
        ):
            if await request.is_disconnected():
                logger.info("client disconnected; aborting agent run")
                break

            content = getattr(event, "content", None)
            if content is None or not getattr(content, "parts", None):
                continue

            for part in content.parts:
                # --- text: plan / proposed prompt / report / narration ---
                text = getattr(part, "text", None)
                if text and text.strip():
                    t = text.strip()
                    if not emitted_plan and _looks_like_plan(t):
                        emitted_plan = True
                        yield _sse({"type": "plan", "text": t})
                    elif _looks_like_proposed_prompt(t, verify_seen):
                        if last_phase != "propose":
                            last_phase = "propose"
                            yield await emit_phase("propose", "Propose fix")
                        # Emit the prose as narration, then the extracted prompt
                        # block as the proposed_prompt (so the UI gets both the
                        # reasoning and a clean, copyable corrected prompt).
                        yield _sse({"type": "narration", "text": t})
                        yield _sse(
                            {
                                "type": "proposed_prompt",
                                "text": _extract_fenced_block(t) or t,
                            }
                        )
                    elif _looks_like_report(t, verify_seen):
                        if last_phase != "report":
                            last_phase = "report"
                            yield await emit_phase("report", "Report")
                        yield _sse({"type": "report", "text": t})
                    else:
                        yield _sse({"type": "narration", "text": t})

                # --- tool call ---
                fc = getattr(part, "function_call", None)
                if fc is not None:
                    name = getattr(fc, "name", "") or ""
                    args = dict(getattr(fc, "args", None) or {})
                    if name == "verify_fix":
                        verify_seen = True
                    phase_info = _TOOL_PHASE.get(name)
                    if phase_info and last_phase != phase_info[0]:
                        last_phase = phase_info[0]
                        yield await emit_phase(*phase_info)
                    yield _sse({"type": "tool_call", "name": name, "args": args})

                # --- tool result ---
                fr = getattr(part, "function_response", None)
                if fr is not None:
                    name = getattr(fr, "name", "") or ""
                    result = getattr(fr, "response", None)
                    kind = _tool_result_kind(result)
                    if kind == "regression":
                        yield _sse(
                            {
                                "type": "tool_result",
                                "name": name,
                                "kind": "regression",
                                "data": result,
                            }
                        )
                    elif kind == "failures":
                        yield _sse(
                            {
                                "type": "tool_result",
                                "name": name,
                                "kind": "failures",
                                "data": _failures_payload(result),
                            }
                        )
                    elif kind == "recovery":
                        yield _sse(
                            {
                                "type": "tool_result",
                                "name": name,
                                "kind": "recovery",
                                "data": _recovery_payload(result),
                            }
                        )
                    elif isinstance(result, dict):
                        # Unknown tool result (e.g. a Phoenix MCP read tool the
                        # agent used for cross-check); forward it without a kind.
                        yield _sse(
                            {
                                "type": "tool_result",
                                "name": name,
                                "data": result,
                            }
                        )

        # After the loop: surface the approval gate, then done.
        gate = {"type": "approval_gate"}
        proposed = _LAST_RUN.get("proposed_prompt")
        new_exp = _LAST_RUN.get("new_experiment_id")
        if proposed:
            gate["proposed_prompt"] = proposed
        if new_exp:
            gate["new_experiment_id"] = new_exp
        if last_phase != "approval":
            yield await emit_phase("approval", "Approval gate")
        yield _sse(gate)
        yield _sse({"type": "done"})

    except asyncio.CancelledError:  # client closed the stream
        raise
    except Exception as exc:  # never crash the stream — report and end cleanly
        logger.exception("agent run failed")
        yield _sse({"type": "error", "text": str(exc)})
        yield _sse({"type": "done"})


# Track the latest proposed prompt + verified experiment id so the approval gate
# event (and a subsequent /api/approve) can reference them. Per-process, single
# concurrent run is fine for this local-first demo.
_LAST_RUN: dict = {}


@app.get("/api/run")
async def api_run(request: Request):
    """SSE stream of a live agent run (detect -> RCA -> fix -> verify -> report)."""
    _LAST_RUN.clear()

    async def gen():
        # Wrap the stream so we can sniff proposed_prompt / new_experiment_id out
        # of the events as they pass, populating the approval gate + /api/approve.
        async for event in _agent_event_stream(request):
            try:
                payload = json.loads(event["data"])
                if payload.get("type") == "proposed_prompt":
                    _LAST_RUN["proposed_prompt"] = payload.get("text")
                elif (
                    payload.get("type") == "tool_result"
                    and payload.get("kind") == "recovery"
                ):
                    exp = (payload.get("data") or {}).get("experiment_id")
                    if exp:
                        _LAST_RUN["new_experiment_id"] = exp
            except (KeyError, json.JSONDecodeError):
                pass
            yield event

    return EventSourceResponse(gen())


# ── /api/approve ────────────────────────────────────────────────────────────────
class ApproveBody(BaseModel):
    decision: str  # "approve" | "reject"


@app.post("/api/approve")
def api_approve(body: ApproveBody):
    """Record the human decision at the approval gate.

    Honest by design: we record the decision and return a message. We do NOT
    promote the corrected prompt to production — the guarded gate is the point.
    """
    decision = (body.decision or "").strip().lower()
    if decision not in ("approve", "reject"):
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "promoted": False,
                "message": "decision must be 'approve' or 'reject'",
            },
        )

    _LAST_RUN["decision"] = decision
    if decision == "approve":
        message = (
            "Approval recorded. The corrected prompt is sanctioned for promotion, "
            "but this service does not auto-promote to production — the guarded "
            "gate is intentional. Wire promotion into your deploy pipeline."
        )
    else:
        message = (
            "Rejection recorded. The corrected prompt was NOT promoted; the "
            "current (regressed) prompt remains in place pending a new fix."
        )
    return {"ok": True, "promoted": False, "message": message}


# ── Serve the built frontend ────────────────────────────────────────────────────
# Mount web/ui/dist at / if it exists. If the frontend hasn't been built yet,
# don't crash — log a note and keep serving the API.
_UI_DIST = os.path.join(os.path.dirname(__file__), "..", "ui", "dist")
_UI_DIST = os.path.abspath(_UI_DIST)
if os.path.isdir(_UI_DIST):
    app.mount("/", StaticFiles(directory=_UI_DIST, html=True), name="ui")
    logger.info("serving built frontend from %s", _UI_DIST)
else:
    logger.info(
        "frontend build not found at %s — serving API only "
        "(build the frontend separately to enable the UI)",
        _UI_DIST,
    )

    @app.get("/")
    def _root_placeholder():
        return {
            "service": "eval-sentinel",
            "ui": "not built yet (web/ui/dist missing)",
            "endpoints": ["/api/state", "/api/run", "/api/approve"],
        }
