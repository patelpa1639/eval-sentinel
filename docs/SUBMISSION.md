# Eval Sentinel — Devpost Submission

**Event:** Google Cloud Rapid Agent Hackathon · **Track:** Arize
**Stack:** Agent Development Kit (ADK, Python) · Gemini 3 (`gemini-3.5-flash`) ·
Arize Phoenix MCP server (27 tools) · deployed to Vertex AI Agent Engine.

---

## Inspiration

LLM applications fail in a way that classic software doesn't: silently. A
one-line prompt edit can wipe out an entire category of answers while the app
keeps returning confident, well-formed output. No exception fires. The overall
accuracy number barely moves, so dashboards stay green. By the time a human
spots it in the evals, it's been shipping bad answers for days.

We'd already built an autonomous agent that does this for infrastructure —
detect an incident, find the root cause, apply a fix, verify it recovered, with
an approval gate before anything irreversible. The insight was that LLM-eval
regressions are the same shape of problem. So we re-pointed that proven
detect → root-cause → fix → verify loop at AI quality, and gave it Arize Phoenix
as its senses.

## What it does

Eval Sentinel autonomously safeguards an LLM application's quality. The demo
target is a support-ticket classifier (categories: billing, account, technical,
other) evaluated in Arize Phoenix on a 24-example `support-tickets` dataset.

1. **Detect.** It pulls the current and baseline experiments through Phoenix and
   compares them category by category. In the demo, a shipped prompt change took
   overall accuracy from **100% → 75%**, with **billing collapsing from 100% →
   0%** while every other category stayed at 100%. The agent isolates that drop
   on its own — no hard-coded threshold.
2. **Root-cause.** It opens the failing billing cases, sees they're all
   mislabeled as "account," reads the prompt attached to the current experiment,
   and pins the cause: the prompt was rewritten to fold billing *under* account.
3. **Fix.** It proposes a corrected prompt that re-separates billing as its own
   category, citing the eval evidence it relied on.
4. **Verify.** It re-runs the evaluation experiment through Phoenix and confirms
   billing recovers to **~100%** and overall returns to 100% — then reports the
   before/after.

An **approval gate** guards promoting the fixed prompt to production; everything
up to that point is autonomous. It all runs from `python -m src.run`, streaming
the agent's reasoning and Phoenix tool calls live in the terminal, with the
experiments visible in the Phoenix UI.

## How we built it

- **Agent Development Kit (ADK, Python)** defines the agent, its instruction, and
  its tool surface. The detect → root-cause → fix → verify behavior is driven by
  the agent's reasoning over real eval data, not a scripted pipeline.
- **Gemini 3 (`gemini-3.5-flash`)** is the reasoning engine, accessed through
  Vertex AI. It does the comparison, the diagnosis, the prompt rewrite, and the
  before/after summary.
- **Arize Phoenix MCP server** is wired into ADK as an `McpToolset` (stdio via
  `npx @arizeai/phoenix-mcp`), exposing 27 tools for datasets, experiments,
  traces, and evals. This is the agent's entire sensory and action surface — it
  reads experiments, inspects failing examples, and re-runs evals all through
  Phoenix.
- **Vertex AI Agent Engine** is the deploy target for running the agent as a
  managed service.
- The architecture is built on a **proven autonomous-healing design** we
  developed for infrastructure incidents; Eval Sentinel is that design
  generalized to LLM-eval regressions.

A seed script (`python -m src.seed`) plants the demo: it creates the dataset and
runs two experiments — a baseline prompt (100%) and a regressed prompt that
folds billing under account (75%, billing 0%) — giving the agent a real,
explainable regression to work on.

## Challenges

- **ADK's import surface and MCP wiring move fast.** Getting the Phoenix MCP
  server mounted as an ADK toolset (stdio transport, env passthrough for the
  Phoenix host + key) took iteration against the installed `google-adk` version.
- **Making the regression real, not staged.** The planted bug had to be a
  genuine, explainable misconfiguration — folding billing under account — so the
  agent's root-cause is a true diagnosis from evidence, not a guess at a label we
  secretly handed it.
- **Verification, not just claims.** The hard part of an autonomous fix is
  proving it worked. We made the agent re-run the actual Phoenix eval experiment
  rather than trust its own edit.
- **Keeping the loop autonomous but safe.** Drawing the line at "autonomous up to
  the production-promotion approval gate" so the agent is genuinely hands-off
  where it's safe and gated where it isn't.

## Accomplishments

- A genuinely autonomous closed loop: detect, root-cause, fix, and **verify** an
  LLM-eval regression with no human in the middle until the approval gate.
- An **organic** Arize integration — the agent has no job *except* reasoning over
  Phoenix eval and trace data; the MCP server is its senses and hands, not a
  bolt-on.
- A crisp, reproducible demo with concrete numbers (100% → 75%, billing 100% →
  0% → ~100%) anyone can re-run from a seed script.
- Reuse of a battle-tested autonomous-healing architecture, generalized cleanly
  from infrastructure to AI quality.

## What's next

- Continuous mode: watch experiments on a schedule and trigger on drift, not just
  on demand.
- Richer root-cause: span-level trace analysis (latency, tool errors, retrieval
  quality) beyond prompt regressions.
- Multi-fix proposals: prompt, model-param, and dataset fixes ranked by expected
  eval gain.
- Approval workflow integrations so the production-promotion gate routes to a
  human reviewer in chat.
- Broaden beyond classification to generative-quality and RAG eval regressions.

---

## How this maps to the judging criteria

**Technological Implementation.**
A real ADK agent on Gemini 3 with the Arize Phoenix MCP server (27 tools) mounted
as its toolset, deployable to Vertex AI Agent Engine. The detect → root-cause →
fix → verify loop is driven by model reasoning over live eval data, and the fix
is verified by re-running the actual Phoenix experiment — not asserted. The
Phoenix MCP integration is the core of the system, exercising the partner stack
deeply rather than superficially.

**Design.**
A tight, legible closed loop with a clear safety boundary: fully autonomous
through detect/root-cause/fix/verify, with a single approval gate before
production promotion. The demo is reproducible from a seed script and observable
two ways — the agent streams its reasoning and tool calls in the terminal, and
the experiments are visible in the Phoenix UI.

**Potential Impact.**
Silent LLM regressions are a universal and growing problem as teams ship
prompt/model changes faster than they can manually review evals. An agent that
catches partial regressions hidden inside an average, explains them, and proves
a fix addresses a real operational pain for anyone running LLM apps in
production.

**Quality of the Idea.**
The differentiator is the *organic* Arize integration: Eval Sentinel's entire job
is reasoning over Phoenix eval/trace data, so the partner tooling is the
substance of the agent, not decoration. It targets the thinner-field **Arize
track**, and it's grounded in a proven autonomous-healing architecture rather
than a from-scratch concept — credible, not hypothetical.
