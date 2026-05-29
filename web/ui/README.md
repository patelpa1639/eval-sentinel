# Eval Sentinel — Dashboard (`web/ui`)

An ops-console for the Eval Sentinel agent. It tells one story visually:
**Healthy → ⚠ Regression detected → Healing… → ✓ Healed.**

Dark, dense, sharp. Monospace for all numerals/IDs/prompts (JetBrains Mono),
Inter for prose. One restrained accent + semantic red/green/amber. No gradients,
no glow, no generic cards — a tool an SRE would actually use. Fully responsive
(single column on a phone).

## Stack

Vite + React + TypeScript + Tailwind CSS. Build output: `web/ui/dist`.

## Commands

```bash
npm install        # install deps
npm run dev        # dev server (http://localhost:5173)
npm run build      # type-check + production build -> dist/
npm run preview    # preview the built dist/
```

In **dev**, `/api/*` is proxied to the backend at `http://localhost:8000`
(see `vite.config.ts`). In **prod** the backend serves these routes same-origin.

## Mock mode (develop without the backend)

The real agent run takes ~2 min and the backend is built in parallel, so the UI
ships with a static fixture of `/api/state` and the `/api/run` SSE stream.
The fixture matches the demo numbers (baseline 100% everywhere; current media 60
/ security 60 / rest 100, overall 84; recovery all 100; regressed = media,
security; the four failing media/security commands).

Two ways to toggle it:

- **Runtime (no rebuild):** append `?mock=1` to the URL, e.g.
  `http://localhost:5173/?mock=1`. Use `?mock=0` to force-disable.
- **Build/dev-time env:** run with `VITE_MOCK=1`, e.g.
  `VITE_MOCK=1 npm run dev` or `VITE_MOCK=1 npm run build`.

In mock mode a banner reads `MOCK MODE — replaying static fixture, no backend`,
and clicking **Run Eval Sentinel** replays the incident timeline node-by-node so
you can verify the full detect → root-cause → fix → verify → report → approval
flow, including the bars animating from regressed (red) to healed (green).

## Components

- `StatusHeader` — product mark, dataset, state pill, overall % + delta.
- `CategoryBars` — per-category bars; regressed bars animate to healed.
- `RunButton` — triggers `GET /api/run`.
- `RunTimeline` — the streamed incident (plan, phases, tool calls, regression
  table, failing-command evidence, proposed prompt, verified recovery,
  postmortem). The centerpiece; nodes appear as they stream.
- `ApprovalGate` — proposed prompt + Approve / Reject → `POST /api/approve`.
- Phoenix deep-link from `state.phoenix_url`.

## API contract (frozen)

- `GET /api/state` → `{dataset, baseline, current, regressed_categories, phoenix_url}`
- `GET /api/run` → SSE stream of typed events (`plan`, `phase`, `tool_call`,
  `tool_result`, `narration`, `proposed_prompt`, `report`, `approval_gate`, `done`).
- `POST /api/approve` `{decision}` → `{ok, promoted, message}`.

See `src/lib/types.ts` for exact shapes.
