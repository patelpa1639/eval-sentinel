# Eval Sentinel

Autonomous LLM-evaluation agent for the **Google Cloud Rapid Agent Hackathon** (Arize track).

**Stack:** Agent Development Kit (ADK, Python) · Gemini 3 (`gemini-3.5-flash`) · Arize Phoenix MCP (27 tools) · deployed on Vertex AI Agent Engine.

## Pitch

Homelabbers and hobbyists increasingly run **local LLMs** — Gemma via Ollama and
the like — as the brain of their home assistant: routing "dim the bedroom lamp"
or "set the thermostat to 68" to the right subsystem. But swap the model or edit
the routing prompt and a whole category of commands can silently start
misfiring, while the average accuracy barely moves and the assistant keeps
answering with confidence. There's no tooling to catch that.

Eval Sentinel is the autonomous **quality watchdog for self-hosted LLMs**. It
reads your evals and traces through the Arize Phoenix MCP server, reasons over
them with Gemini 3, and runs a closed **detect → root-cause → fix → verify**
loop: it catches the regression, explains its cause, proposes a corrected
prompt, re-runs a real evaluation to prove the fix, and reports the
before/after — with an approval gate before anything is promoted to production.
The agent itself is cloud Gemini 3; the *watched* model can be your local one.
A Gemini-3 agent that keeps your local LLM healthy.

## Architecture

```
                    ┌──────────────────────────┐
                    │        Gemini 3          │
                    │   (gemini-3.5-flash,     │
                    │    reasoning engine)     │
                    └────────────┬─────────────┘
                                 │
                          ┌──────┴───────┐
                          │  ADK Agent   │   detect ─▶ root-cause
                          │ Eval Sentinel│         ▲            │
                          └──────┬───────┘      verify ◀──── fix
                                 │                  │
                    ┌────────────┴─────────────┐    │ approval gate
                    │  Arize Phoenix MCP server │    ▼ before prod
                    │  (27 tools: datasets,     │  promote fix
                    │  experiments, traces,     │
                    │  evals)                   │
                    └───────────────────────────┘

            Deploy target: Vertex AI Agent Engine
```

The agent's entire sensory and action surface is the Arize Phoenix MCP server —
reading experiments, inspecting failing examples, and re-running evals all go
through Phoenix. The integration is organic, not bolted on.

## Demo arc

A smart-home command router — the kind a homelabber runs on a local LLM to route
voice/text commands — with five categories (lights, climate, media, security,
other), evaluated in Arize Phoenix on a 25-example `smart-home-commands` dataset.

| Experiment            | Overall | lights | climate  | media | security | other |
|-----------------------|:-------:|:------:|:--------:|:-----:|:--------:|:-----:|
| baseline              |  100%   |  100%  |  100%    | 100%  |  100%    | 100%  |
| current (regressed)   |   80%   |  100%  | **0%**   | 100%  |  100%    | 100%  |
| after Eval Sentinel   |  100%   |  100%  | ~100%    | 100%  |  100%    | 100%  |

A bad prompt edit folds **climate control under lights** ("treat climate as part
of lights"), restricting `climate` to whole-home HVAC installation requests
only — so thermostat and AC commands get mislabeled `lights`. Eval Sentinel
**detects** climate dropping 100% → 0% (current vs baseline), **root-causes** it
to the offending clause (citing failing commands like "set the thermostat to 68
degrees"), **proposes** a corrected prompt, **verifies** by running a real new
Phoenix experiment (climate recovers to ~100%, overall back to 100%), and
**reports** a before/after postmortem. An approval gate guards promoting the
fixed prompt to production.

Phoenix experiments: https://app.phoenix.arize.com/s/patelpa1639/datasets/RGF0YXNldDoy/experiments
(navigate via Datasets & Experiments → `smart-home-commands`).

## Setup

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
cp .env.example .env   # fill in GCP project + Phoenix MCP creds (never commit .env)
```

## Run

```bash
# 1. Plant the demo regression in Phoenix (baseline 100% + regressed 80%/climate 0%)
python -m src.seed

# 2. Watch Eval Sentinel detect, root-cause, fix, and verify it live
python -m src.run
```

`python -m src.run` streams the agent's reasoning and Phoenix tool calls live in
the terminal — a `rich`-rendered view with colored panels, a red→green
**Before → After** table, and an approval-gate panel. The experiments are also
visible in the Phoenix UI.

## Lineage

Eval Sentinel is built on a proven autonomous-healing architecture (our
infrastructure agent, Rhodes), re-pointed from infra incidents to LLM-eval
regressions.

## Docs

- [`docs/DEMO.md`](docs/DEMO.md) — ≤3-minute video storyboard, shot list, recording tips.
- [`docs/SUBMISSION.md`](docs/SUBMISSION.md) — Devpost writeup + judging-criteria mapping.

## Hackathon

- Event: https://rapid-agent.devpost.com/  · Track: Arize · Deadline: Jun 11, 2026 2pm PDT
- License: see LICENSE (MIT)
