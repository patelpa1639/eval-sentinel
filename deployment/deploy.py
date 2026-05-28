#!/usr/bin/env python3
"""Deploy Eval Sentinel (ADK agent) to Vertex AI Agent Engine.

Hackathon requirement: the agent must be "built on Google Cloud Agent Builder".
Deploying the ADK agent to **Vertex AI Agent Engine** (a.k.a. Agent Engine /
reasoning engine / Gemini Enterprise Agent Platform runtime) satisfies that
requirement AND yields the hosted project URL the submission needs.

Deployment method (verified against the installed SDKs, 2026):
  - SDK: `google-cloud-aiplatform[agent_engines]` exposes the `vertexai` client.
  - Wrapper: `from vertexai.agent_engines import AdkApp` wraps the ADK agent.
  - Call: `vertexai.Client(project=..., location=...).agent_engines.create(
            agent_engine=AdkApp(agent=root_agent, enable_tracing=True),
            config=AgentEngineConfig(requirements=[...], extra_packages=["src"],
                                     staging_bucket=..., display_name=...,
                                     env_vars={...}))`
  This is the same path the `adk deploy agent_engine` CLI drives internally
  (see google/adk/cli/cli_deploy.py -> `client.agent_engines.create(config=...)`).

Docs:
  - https://adk.dev/deploy/agent-runtime/   (ADK -> Agent Runtime / Agent Engine)
  - https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/runtime/deploy-an-agent

Usage:
  # Validate config + imports + staging bucket WITHOUT a billable deploy:
  python -m deployment.deploy --dry-run

  # Real deploy (BILLABLE — run only with explicit approval):
  python -m deployment.deploy --deploy

  # Tear down (avoid lingering cost):
  python -m deployment.deploy --delete projects/.../reasoningEngines/<id>
"""

from __future__ import annotations

import argparse
import ast
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# --- Paths -------------------------------------------------------------------
DEPLOY_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = DEPLOY_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"
AGENT_FILE = SRC_DIR / "agent.py"

# Make `import src.agent` resolvable when run as a script.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

# --- Deployment configuration ------------------------------------------------
# Gemini runs in location 'global', but Agent Engine resources must live in a
# supported region. us-central1 is the safe default.
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "rapid-agent-497721")
AGENT_ENGINE_LOCATION = os.environ.get("AGENT_ENGINE_LOCATION", "us-central1")
STAGING_BUCKET = os.environ.get(
    "AGENT_ENGINE_STAGING_BUCKET", f"{PROJECT_ID}-agent-engine-staging"
)
DISPLAY_NAME = "Eval Sentinel"
DESCRIPTION = (
    "Autonomous LLM-eval agent: pulls evals/traces via Arize Phoenix MCP, "
    "reasons with Gemini, detects regressions, and files fix proposals."
)

# Runtime dependencies the Agent Engine container must install. google-adk and
# the agent_engines extra are required; the rest mirror the agent's imports.
REQUIREMENTS = [
    "google-cloud-aiplatform[agent_engines]",
    "google-adk==2.1.0",
    "mcp",
    "arize-phoenix-client",
    "google-genai",
    "python-dotenv",
]

# Ship the local `src/` package as extra source so `from src.agent import
# root_agent` resolves inside the deployed runtime. We also ship the
# `installation_scripts/` dir (build-time Node install — see below).
EXTRA_PACKAGES = ["src", "installation_scripts"]

# Build-time installation scripts (run as root during image build). The Phoenix
# MCP server launches via `npx`, which needs Node.js; install_node.sh installs
# it so the MCP integration works in the cloud runtime, not just locally.
# Contract (Vertex SDK): scripts live in the `installation_scripts/` subdir and
# their paths are listed both here and in EXTRA_PACKAGES.
INSTALLATION_SCRIPTS = ["installation_scripts/install_node.sh"]

# Env vars forwarded into the deployed runtime. Pulled from .env at deploy time.
# NOTE: PHOENIX_API_KEY is forwarded but NEVER logged by this script.
_FORWARDED_ENV_KEYS = [
    "GEMINI_MODEL",
    "GOOGLE_GENAI_USE_VERTEXAI",
    "PHOENIX_COLLECTOR_ENDPOINT",
    "PHOENIX_API_KEY",
]


# --- Helpers -----------------------------------------------------------------
def _redact(key: str, value: str) -> str:
    """Mask secret-shaped values so they never hit logs."""
    if "KEY" in key or "TOKEN" in key or "SECRET" in key:
        return "<redacted>"
    return value


def _collect_env_vars() -> dict[str, str]:
    env_vars = {
        # Agent Engine needs Vertex AI mode on for Gemini calls.
        "GOOGLE_GENAI_USE_VERTEXAI": os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "TRUE"),
        # Gemini model itself runs in 'global'; keep that explicit at runtime.
        "GOOGLE_CLOUD_LOCATION": os.environ.get("GOOGLE_CLOUD_LOCATION", "global"),
        "GOOGLE_CLOUD_PROJECT": PROJECT_ID,
    }
    for key in _FORWARDED_ENV_KEYS:
        val = os.environ.get(key)
        if val:
            env_vars[key] = val
    return env_vars


def _validate_agent_static() -> None:
    """Confirm `src/agent.py` parses and defines `root_agent` WITHOUT importing.

    Importing src.agent eagerly constructs the Phoenix McpToolset, which spawns
    an `npx @arizeai/phoenix-mcp` subprocess. In --dry-run we avoid that side
    effect by validating statically (parse + assignment check).
    """
    if not AGENT_FILE.exists():
        raise SystemExit(f"FAIL: agent file not found: {AGENT_FILE}")
    tree = ast.parse(AGENT_FILE.read_text(), filename=str(AGENT_FILE))
    defines_root_agent = any(
        isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "root_agent" for t in node.targets)
        for node in ast.walk(tree)
    )
    if not defines_root_agent:
        raise SystemExit("FAIL: src/agent.py does not define `root_agent`.")
    print(f"  [ok] {AGENT_FILE.relative_to(PROJECT_ROOT)} parses and defines root_agent")


def _check_bucket(create: bool = False) -> bool:
    """Check the GCS staging bucket exists. Optionally create it (real deploy)."""
    from google.cloud import storage

    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(STAGING_BUCKET)
    if bucket.exists():
        print(f"  [ok] staging bucket gs://{STAGING_BUCKET} exists")
        return True
    if not create:
        print(
            f"  [WARN] staging bucket gs://{STAGING_BUCKET} does NOT exist.\n"
            f"         Create it before the real deploy:\n"
            f"         gsutil mb -p {PROJECT_ID} -l {AGENT_ENGINE_LOCATION} "
            f"gs://{STAGING_BUCKET}"
        )
        return False
    print(f"  [..] creating staging bucket gs://{STAGING_BUCKET} ...")
    client.create_bucket(bucket, location=AGENT_ENGINE_LOCATION)
    print(f"  [ok] created gs://{STAGING_BUCKET}")
    return True


def _print_config() -> None:
    env_vars = _collect_env_vars()
    print("Agent Engine deployment config:")
    print(f"  project          : {PROJECT_ID}")
    print(f"  region           : {AGENT_ENGINE_LOCATION}  (Gemini model runs in 'global')")
    print(f"  staging bucket   : gs://{STAGING_BUCKET}")
    print(f"  display_name     : {DISPLAY_NAME}")
    print(f"  extra_packages   : {EXTRA_PACKAGES}")
    print(f"  install scripts  : {INSTALLATION_SCRIPTS}  (Node for the Phoenix MCP)")
    print(f"  requirements     : {REQUIREMENTS}")
    print("  env_vars         :")
    for k, v in env_vars.items():
        print(f"      {k} = {_redact(k, v)}")


# --- Commands ----------------------------------------------------------------
def dry_run() -> int:
    print("=== Eval Sentinel -> Agent Engine : DRY RUN (no billable resources) ===\n")
    print("[1/3] Validating agent source (static, no MCP subprocess) ...")
    _validate_agent_static()

    print("\n[2/3] Validating deploy-time imports (SDK availability) ...")
    try:
        import vertexai  # noqa: F401
        from vertexai import Client  # noqa: F401
        from vertexai.agent_engines import AdkApp  # noqa: F401
        from vertexai._genai.types import AgentEngineConfig  # noqa: F401

        print(f"  [ok] vertexai {vertexai.__version__} + AdkApp + AgentEngineConfig import OK")
    except Exception as exc:  # pragma: no cover
        raise SystemExit(
            "FAIL: deploy SDK not importable. Install with:\n"
            "  pip install 'google-cloud-aiplatform[agent_engines]'\n"
            f"  ({exc})"
        )

    print("\n[3/3] Checking config + staging bucket ...")
    _print_config()
    # Validate the build-time install scripts exist (shipped via extra_packages).
    for rel in INSTALLATION_SCRIPTS:
        p = PROJECT_ROOT / rel
        if p.exists():
            print(f"  [ok] install script present: {rel}")
        else:
            print(f"  [WARN] install script MISSING: {rel} (Phoenix MCP won't run in-cloud)")
    print()
    bucket_ok = _check_bucket(create=False)

    print("\n=== DRY RUN COMPLETE ===")
    if bucket_ok:
        print("All checks passed. Ready for real deploy: python -m deployment.deploy --deploy")
    else:
        print("Config + imports OK. Create the staging bucket (above) before --deploy.")
    return 0


def deploy() -> int:
    """REAL, BILLABLE deploy. Imports root_agent (spawns Phoenix MCP) and creates
    the Agent Engine resource."""
    print("=== Eval Sentinel -> Agent Engine : REAL DEPLOY (BILLABLE) ===\n")
    _print_config()
    print()
    if not _check_bucket(create=True):
        return 1

    import vertexai
    from vertexai.agent_engines import AdkApp
    from vertexai._genai.types import AgentEngineConfig

    # Full import — constructs the Phoenix McpToolset (spawns npx) so the live
    # agent is wired exactly as it will run in the cloud.
    from src.agent import root_agent

    client = vertexai.Client(project=PROJECT_ID, location=AGENT_ENGINE_LOCATION)
    app = AdkApp(agent=root_agent, enable_tracing=True)

    print("Deploying to Agent Engine (this takes several minutes) ...")
    agent_engine = client.agent_engines.create(
        agent_engine=app,
        config=AgentEngineConfig(
            display_name=DISPLAY_NAME,
            description=DESCRIPTION,
            requirements=REQUIREMENTS,
            extra_packages=EXTRA_PACKAGES,
            staging_bucket=f"gs://{STAGING_BUCKET}",
            env_vars=_collect_env_vars(),
            # Install Node at build time so the Phoenix MCP (npx) runs in-cloud.
            build_options={"installation_scripts": INSTALLATION_SCRIPTS},
        ),
    )
    name = agent_engine.api_resource.name
    print("\n=== DEPLOYED ===")
    print(f"Resource name : {name}")
    print(
        "Console URL   : "
        f"https://console.cloud.google.com/vertex-ai/agents/agent-engines/"
        f"locations/{AGENT_ENGINE_LOCATION}/agent-engines/{name.split('/')[-1]}"
        f"?project={PROJECT_ID}"
    )
    print("\nDelete when done to avoid cost:")
    print(f"  python -m deployment.deploy --delete {name}")
    return 0


def delete(resource_name: str) -> int:
    import vertexai

    client = vertexai.Client(project=PROJECT_ID, location=AGENT_ENGINE_LOCATION)
    print(f"Deleting Agent Engine: {resource_name} (force=True) ...")
    client.agent_engines.delete(name=resource_name, force=True)
    print("Deleted.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy Eval Sentinel to Agent Engine.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate imports + config + staging bucket. No billable resources.",
    )
    group.add_argument(
        "--deploy",
        action="store_true",
        help="REAL billable deploy to Agent Engine.",
    )
    group.add_argument(
        "--delete",
        metavar="RESOURCE_NAME",
        help="Delete a deployed Agent Engine by full resource name.",
    )
    args = parser.parse_args()

    if args.deploy:
        return deploy()
    if args.delete:
        return delete(args.delete)
    # Default to dry-run for safety.
    return dry_run()


if __name__ == "__main__":
    raise SystemExit(main())
