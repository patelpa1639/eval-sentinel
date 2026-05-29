# Eval Sentinel — web backend

A FastAPI service that exposes the current eval state, streams a live agent run
over Server-Sent Events, handles the human approval gate, and serves the built
React frontend (`web/ui/dist`).

The agent loop runs **in-process** — this is the same `detect → root-cause →
propose → verify → report` loop that `src/run.py` drives for the terminal demo,
re-emitted as SSE events.

## Run locally

From the project root (so the `src` package is importable and `.env` resolves):

```bash
# deps are installed into the project venv:
./.venv/bin/pip install -r web/server/requirements.txt

# start the server:
./.venv/bin/python -m uvicorn web.server.app:app --port 8000
```

Then:

```bash
curl localhost:8000/api/state            # baseline vs current scores
curl -N localhost:8000/api/run           # SSE stream of a live agent run
```

> `GET /api/run` runs the **real** agent (incl. a real `verify_fix` experiment),
> so a full run takes ~2 minutes. The stream begins emitting `plan` / `phase` /
> `detect` events within seconds.

The frontend (built separately to `web/ui/dist`) is served at `/`. If that
directory doesn't exist yet, the server still serves the API and returns a small
JSON placeholder at `/`.

## Endpoints

### `GET /api/state`
```json
{
  "dataset": "smart-home-commands",
  "baseline": {"overall": 100.0, "per_category": {"...": 100.0}},
  "current":  {"overall": 84.0,  "per_category": {"media": 60.0, "security": 60.0}},
  "regressed_categories": ["media", "security"],
  "phoenix_url": "https://app.phoenix.arize.com/s/.../experiments"
}
```

### `GET /api/run` — SSE (`text/event-stream`)
Each message is `data: {json}\n\n`. Event `type`s, in order:

| type | fields |
| --- | --- |
| `plan` | `text` |
| `phase` | `phase` (detect\|root_cause\|propose\|verify\|report\|approval), `label` |
| `tool_call` | `name`, `args` |
| `tool_result` | `name`, `kind` (regression\|failures\|recovery), `data` |
| `narration` | `text` (markdown) |
| `proposed_prompt` | `text` |
| `report` | `text` (postmortem markdown) |
| `approval_gate` | `proposed_prompt`, `new_experiment_id` |
| `done` | — |

`kind` is inferred from the tool-result dict shape:
`regressed_categories → regression`, `failing → failures`,
`per_category + experiment_id → recovery`. Unknown tool results (e.g. Phoenix
MCP read tools the agent uses for cross-checks) are forwarded without a `kind`.

### `POST /api/approve`
Body: `{"decision": "approve" | "reject"}` →
`{"ok": true, "promoted": false, "message": "..."}`.
Records the decision and returns a message. It deliberately does **not** promote
the corrected prompt to production — the guarded gate is the point.

## Notes
- The `PHOENIX_API_KEY` is read from `.env` and is never printed or logged.
- CORS allows `localhost`/`127.0.0.1` on any port (the Vite dev server runs on a
  different port during development).
