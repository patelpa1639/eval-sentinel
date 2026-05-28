# Eval Sentinel

Autonomous LLM-evaluation agent for the **Google Cloud Rapid Agent Hackathon** (Arize track).

**Stack:** Agent Development Kit (ADK, Python) · Gemini 3 (`gemini-3.5-flash`) · Arize Phoenix MCP (27 tools) · deployed on Vertex AI Agent Engine.

## Pitch

LLM applications regress silently — a one-line prompt change can wipe out a whole
category of answers while the app keeps returning confident output and the
average accuracy barely moves. Eval Sentinel is an autonomous agent that reads
your evals and traces through the Arize Phoenix MCP server, reasons over them
with Gemini 3, and runs a closed **detect → root-cause → fix → verify** loop: it
catches the regression, explains its cause, proposes a corrected prompt, re-runs
the evaluation to prove the fix, and reports the before/after — with an approval
gate before anything is promoted to production.

## Architecture

```
                    ┌──────────────────────────┐
                    │        Gemini 3          │
                    │   (gemini-3.5-flash,     │
                    │    reasoning engine)     │
                    └────────────┬─────────────┘
                                 │
                          ┌──────┴──────┐
                          │  ADK Agent  │   detect ─▶ root-cause
                          │ Eval Sentinel│         ▲            │
                          └──────┬──────┘      verify ◀──── fix
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

A support-ticket classifier (categories: billing, account, technical, other),
evaluated in Arize Phoenix on a 24-example `support-tickets` dataset.

| Experiment            | Overall | billing | account | technical | other |
|-----------------------|:-------:|:-------:|:-------:|:---------:|:-----:|
| baseline              |  100%   |  100%   |  100%   |   100%    | 100%  |
| current (regressed)   |   75%   |  **0%** |  100%   |   100%    | 100%  |
| after Eval Sentinel   |  100%   | ~100%   |  100%   |   100%    | 100%  |

A shipped prompt change wrongly folds billing *under* account ("treat billing as
part of account"), so billing tickets get mislabeled as account. Eval Sentinel
**detects** billing dropping 100% → 0% (current vs baseline), **root-causes** it
to the prompt change, **proposes** a corrected prompt, **verifies** by re-running
the eval (billing recovers to ~100%), and **reports** the before/after. An
approval gate guards promoting the fixed prompt to production.

Phoenix experiments: https://app.phoenix.arize.com/s/patelpa1639/datasets/RGF0YXNldDox/experiments

## Setup

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
cp .env.example .env   # fill in GCP project + Phoenix MCP creds (never commit .env)
```

## Run

```bash
# 1. Plant the demo regression in Phoenix (baseline 100% + regressed 75%/billing 0%)
python -m src.seed

# 2. Watch Eval Sentinel detect, root-cause, fix, and verify it live
python -m src.run
```

`python -m src.run` streams the agent's reasoning and Phoenix tool calls live in
the terminal; the experiments are also visible in the Phoenix UI.

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
