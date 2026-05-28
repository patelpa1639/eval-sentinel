# Eval Sentinel — Devpost Submission

**Event:** Google Cloud Rapid Agent Hackathon · **Track:** Arize
**Stack:** Agent Development Kit (ADK, Python) · Gemini 3 (`gemini-3.5-flash`) ·
Arize Phoenix MCP server (27 tools) · deployed to Vertex AI Agent Engine.

---

## Inspiration

A growing number of homelabbers and hobbyists run **local LLMs** — Gemma via
Ollama and the like — as the brain of their smart home, routing commands like
"dim the bedroom lamp to 30%" or "set the thermostat to 68" to the right
subsystem. It works great until you swap the model or edit the routing prompt.
Then a whole category of commands can quietly start misfiring while the assistant
keeps answering with confidence and the overall accuracy barely moves. Classic
software fails loudly; LLM apps fail silently. And unlike production teams,
self-hosters have **no tooling** to catch a quality regression when they change a
model or a prompt.

We'd already built an autonomous agent that solves this shape of problem for
infrastructure — detect an incident, find the root cause, apply a fix, verify it
recovered, with an approval gate before anything irreversible. LLM-eval
regressions are the same shape. So we re-pointed that proven detect → root-cause
→ fix → verify loop at AI quality and gave it Arize Phoenix as its senses,
aiming it squarely at the self-hosted / local-LLM crowd that has nothing today.

## What it does

Eval Sentinel autonomously safeguards an LLM application's quality. It's a
quality watchdog for self-hosted LLMs: the *agent* is cloud Gemini 3, but the
*watched* model can be your local one. A Gemini-3 agent that keeps your local LLM
healthy.

The demo target is a **smart-home command router** (categories: lights, climate,
media, security, other) evaluated in Arize Phoenix on a 25-example
`smart-home-commands` dataset.

1. **Plan + detect.** The agent first states an explicit plan, then pulls the
   current and baseline experiments through Phoenix and compares them category by
   category. In the demo, a shipped prompt edit took overall accuracy from
   **100% → 80%**, with **climate collapsing from 100% → 0%** while every other
   category stayed at 100%. The agent isolates that drop on its own — no
   hard-coded threshold.
2. **Root-cause.** It opens the failing climate commands, sees they're all
   mislabeled as "lights," reads the prompt attached to the current experiment,
   and pins the cause: the prompt was rewritten to fold climate control *under*
   lights, restricting `climate` to whole-home HVAC installation requests only.
   It cites concrete failing commands (e.g. "set the thermostat to 68 degrees").
3. **Fix.** It proposes a corrected prompt that re-separates climate as its own
   mutually-exclusive category, citing the eval evidence it relied on.
4. **Verify.** It runs a real new evaluation experiment through Phoenix and
   confirms climate recovers to **~100%** and overall returns to 100% — then
   reports the before/after.

A **postmortem** summarizes the recovery, and an **approval gate** guards
promoting the fixed prompt to production; everything up to that point is
autonomous. It all runs from `python -m src.run`, which streams the agent's
reasoning and Phoenix tool calls live in a polished terminal view (rendered with
`rich`): colored panels, a red "Regression detected" table, a green recovery
table, a red→green **Before → After** table, and an approval-gate panel. The
experiments are also visible in the Phoenix UI.

## How we built it

- **Agent Development Kit (ADK, Python)** defines the agent, its instruction, and
  its tool surface. The plan → detect → root-cause → fix → verify → report
  behavior is driven by the agent's reasoning over real eval data, not a scripted
  pipeline.
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
  generalized to LLM-eval quality.

A seed script (`python -m src.seed`) plants the demo: it creates the dataset and
runs two experiments — a baseline prompt (100%) and a regressed prompt that folds
climate under lights (80%, climate 0%) — giving the agent a real, explainable
regression to work on.

## Challenges

- **ADK's import surface and MCP wiring move fast.** Getting the Phoenix MCP
  server mounted as an ADK toolset (stdio transport, env passthrough for the
  Phoenix host + key) took iteration against the installed `google-adk` version.
- **Making the regression real, not staged.** The planted bug had to be a
  genuine, explainable misconfiguration — folding climate control under lights —
  so the agent's root-cause is a true diagnosis from evidence, not a guess at a
  label we secretly handed it.
- **Verification, not just claims.** The hard part of an autonomous fix is
  proving it worked. We made the agent run an actual new Phoenix eval experiment
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
- A real, underserved audience: self-hosters running local LLMs have no quality
  tooling today, and this gives them an autonomous watchdog for free.
- A crisp, reproducible demo with concrete numbers (100% → 80%, climate 100% →
  0% → ~100%) anyone can re-run from a seed script, rendered in a polished
  `rich` terminal UI.
- Reuse of a battle-tested autonomous-healing architecture, generalized cleanly
  from infrastructure to AI quality.

## What's next

- Continuous mode: watch experiments on a schedule and trigger on drift, not just
  on demand — ideal for a homelab assistant that gets re-tuned often.
- Local-model adapters: point the watched model at an Ollama/Gemma endpoint so
  self-hosters can wire their own assistant in directly.
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
is verified by running an actual new Phoenix experiment — not asserted. The
Phoenix MCP integration is the core of the system, exercising the partner stack
deeply rather than superficially.

**Design.**
A tight, legible closed loop with a clear safety boundary: fully autonomous
through detect/root-cause/fix/verify, with a single approval gate before
production promotion. The demo is reproducible from a seed script and observable
two ways — the agent streams its reasoning and tool calls in a polished `rich`
terminal view (colored regression/recovery/before-after tables and an
approval-gate panel), and the experiments are visible in the Phoenix UI.

**Potential Impact.**
Silent LLM regressions are a universal problem, and one corner of it is wide
open: the homelab / self-hosted-LLM crowd running local models as home-assistant
brains has no tooling to catch a regression when they swap a model or edit a
prompt. An agent that catches partial regressions hidden inside an average,
explains them, and proves a fix addresses a real, unmet operational pain — and
the same loop scales straight to production LLM teams.

**Quality of the Idea.**
The differentiator is the *organic* Arize integration: Eval Sentinel's entire job
is reasoning over Phoenix eval/trace data, so the partner tooling is the
substance of the agent, not decoration. The local-LLM framing — a Gemini-3 agent
that keeps your local LLM healthy — gives it a sharp, underserved audience. It
targets the thinner-field **Arize track**, and it's grounded in a proven
autonomous-healing architecture rather than a from-scratch concept — credible,
not hypothetical.
