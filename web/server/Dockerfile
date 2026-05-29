# Eval Sentinel — web backend image for Cloud Run.
#
# Build context = the REPO ROOT (so we can COPY src/ and web/). Build with:
#   docker build -f web/server/Dockerfile -t eval-sentinel-web .
#
# This image bundles BOTH:
#   - the Python service (FastAPI + the in-process ADK agent loop), and
#   - Node.js, because the agent launches the Arize Phoenix MCP server via
#     `npx @arizeai/phoenix-mcp` at RUNTIME (not just build time). The Node
#     install mirrors installation_scripts/install_node.sh (NodeSource 22.x).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

# --- Node.js (NodeSource 22.x), same approach as installation_scripts/install_node.sh ---
# Needed at runtime so `npx @arizeai/phoenix-mcp` runs inside the container.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && node --version && npx --version \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Python deps: project-root requirements + web backend requirements ---
COPY requirements.txt ./requirements.txt
COPY web/server/requirements.txt ./web/server/requirements.txt
RUN pip install -r requirements.txt -r web/server/requirements.txt

# --- App code: the src package, the server, and the built frontend (if present) ---
COPY src ./src
COPY web/server ./web/server
# Frontend: copy source and build it in-image (dist is gitignored, so it won't
# exist in a fresh clone). Node is already installed above for the runtime MCP.
COPY web/ui ./web/ui
RUN cd web/ui && npm ci && npm run build

# Cloud Run injects $PORT; bind to it. The Phoenix MCP server is launched
# on-demand by the agent via npx at runtime.
EXPOSE 8080
CMD ["sh", "-c", "python -m uvicorn web.server.app:app --host 0.0.0.0 --port ${PORT}"]
