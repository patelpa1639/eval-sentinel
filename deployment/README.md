# Deploying Eval Sentinel to Vertex AI Agent Engine

This is the **deployment path** for the GCP Rapid Agent Hackathon. Deploying the
ADK agent to **Vertex AI Agent Engine** (a.k.a. Agent Engine / reasoning engine /
Gemini Enterprise Agent Platform *Agent Runtime*) does two things at once:

1. Satisfies the hackathon's "built on Google Cloud Agent Builder" requirement.
2. Produces the **hosted project resource/URL** the submission needs.

## Deploy method (verified, 2026)

The deploy uses the modern `vertexai` client shipped inside
`google-cloud-aiplatform[agent_engines]`:

```python
import vertexai
from vertexai.agent_engines import AdkApp
from vertexai._genai.types import AgentEngineConfig
from src.agent import root_agent

client = vertexai.Client(project=PROJECT_ID, location="us-central1")
agent_engine = client.agent_engines.create(
    agent_engine=AdkApp(agent=root_agent, enable_tracing=True),
    config=AgentEngineConfig(
        display_name="Eval Sentinel",
        requirements=[...],            # installed in the cloud container
        extra_packages=["src"],        # ships the local src/ package
        staging_bucket="gs://<bucket>",# GCS staging for the build artifacts
        env_vars={...},                # GEMINI_MODEL, PHOENIX_*, etc.
    ),
)
```

This is the same call the `adk deploy agent_engine` CLI drives internally
(`google/adk/cli/cli_deploy.py` -> `client.agent_engines.create(config=...)`).
`deployment/deploy.py` wraps it with a safe `--dry-run` and a `--delete` path.

Docs:
- ADK -> Agent Runtime: <https://adk.dev/deploy/agent-runtime/>
- Deploy an ADK agent: <https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/runtime/deploy-an-agent>

## Why us-central1 (not 'global')

The **Gemini model** is served from location `global` (kept in the runtime env
as `GOOGLE_CLOUD_LOCATION=global`). But **Agent Engine resources must live in a
supported region** — we use `us-central1`. The deploy client is pinned to
`us-central1`; the model call still resolves to `global` at runtime.

## Prerequisites

- gcloud SDK authenticated as the project owner, ADC set
  (already done: `patelpa1639@gmail.com`, project `rapid-agent-497721`).
- Required APIs enabled (already done): Vertex AI / `aiplatform.googleapis.com`,
  Cloud Storage.
- Deploy SDK installed (already in `requirements.txt`):
  ```bash
  ./.venv/bin/pip install 'google-cloud-aiplatform[agent_engines]'
  ```
  > Do NOT install the `[adk]` extra — it downgrades `google-adk` from 2.1.0 to
  > 1.34.1. The `[agent_engines]` extra alone is sufficient.
- **Create the GCS staging bucket** (one time). `gsutil` lives in the gcloud SDK
  at `~/google-cloud-sdk/bin/gsutil`:
  ```bash
  ~/google-cloud-sdk/bin/gsutil mb -p rapid-agent-497721 -l us-central1 \
      gs://rapid-agent-497721-agent-engine-staging
  ```
  (Override the bucket name via the `AGENT_ENGINE_STAGING_BUCKET` env var if
  desired; `deploy.py --deploy` will also create it automatically if missing.)

## 1. Validate first (no cost)

```bash
cd /home/pranav/eval-sentinel
./.venv/bin/python -m deployment.deploy --dry-run
```

This validates the agent source statically (it does **not** spawn the Phoenix
`npx` MCP subprocess), checks the deploy SDK imports, prints the full config
(with `PHOENIX_API_KEY` redacted), and reports whether the staging bucket
exists. No billable resources are created.

## 2. Real deploy (BILLABLE — explicit approval only)

```bash
cd /home/pranav/eval-sentinel
./.venv/bin/python -m deployment.deploy --deploy
```

Takes several minutes (the service builds a container and starts the runtime).
On success it prints:
- **Resource name**: `projects/rapid-agent-497721/locations/us-central1/reasoningEngines/<ID>`
  — this is the hosted resource for the submission.
- **Console URL**: a `console.cloud.google.com/vertex-ai/agents/agent-engines/...`
  link for the deployed agent.

## 3. Test the deployed agent

```python
import vertexai
client = vertexai.Client(project="rapid-agent-497721", location="us-central1")
agent_engine = client.agent_engines.get(
    name="projects/rapid-agent-497721/locations/us-central1/reasoningEngines/<ID>"
)
session = agent_engine.create_session(user_id="tester")
for event in agent_engine.stream_query(
    user_id="tester",
    session_id=session["id"],
    message="Pull the latest evals and report any regressions.",
):
    print(event)
```

## 4. Delete (avoid lingering cost)

```bash
./.venv/bin/python -m deployment.deploy --delete \
    projects/rapid-agent-497721/locations/us-central1/reasoningEngines/<ID>
```

(`--delete` uses `force=True` to also remove child sessions.) Delete the
deployment once the demo/submission recording is captured so it does not keep
billing.
