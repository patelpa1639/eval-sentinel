# Eval Sentinel

Autonomous LLM-evaluation agent for the **Google Cloud Rapid Agent Hackathon** (Arize track).

**Stack:** Agent Development Kit (ADK, Python) · Gemini 3 · Arize Phoenix MCP · deployed on Agent Engine.

## What it does
Eval Sentinel watches an LLM application's quality. It pulls evals and traces through the
Arize Phoenix MCP server, reasons over them with Gemini 3, detects regressions/drift,
root-causes the failing spans, and files an actionable fix proposal — automatically.

## Status
Day-1 scaffold. See task list for build order.

## Setup
```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
cp .env.example .env   # fill in GCP project + Phoenix MCP creds
```

## Run (local)
```bash
adk run src
```

## Hackathon
- Event: https://rapid-agent.devpost.com/  · Track: Arize · Deadline: Jun 11, 2026 2pm PDT
- License: see LICENSE (MIT)
