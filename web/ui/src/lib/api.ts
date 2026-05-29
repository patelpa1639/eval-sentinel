// API client. Talks to the same-origin backend (/api/*) in prod, proxied to
// http://localhost:8000 in dev. In mock mode it replays a static fixture so the
// UI works with no backend.

import type { SentinelEvent, StateResponse, ApproveResponse } from './types';
import { MOCK_STATE, MOCK_EVENTS, MOCK_APPROVE } from './mock';

export function isMockMode(): boolean {
  // Build-time env flag OR runtime ?mock=1 query param.
  const envFlag = (import.meta.env.VITE_MOCK as string | undefined) === '1';
  if (typeof window !== 'undefined') {
    const q = new URLSearchParams(window.location.search);
    if (q.get('mock') === '1') return true;
    if (q.get('mock') === '0') return false;
  }
  return envFlag;
}

export async function fetchState(): Promise<StateResponse> {
  if (isMockMode()) {
    await delay(120);
    return structuredClone(MOCK_STATE);
  }
  const res = await fetch('/api/state');
  if (!res.ok) throw new Error(`GET /api/state failed: ${res.status}`);
  return (await res.json()) as StateResponse;
}

export async function approve(
  decision: 'approve' | 'reject',
): Promise<ApproveResponse> {
  if (isMockMode()) {
    await delay(400);
    return MOCK_APPROVE[decision];
  }
  const res = await fetch('/api/approve', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision }),
  });
  if (!res.ok) throw new Error(`POST /api/approve failed: ${res.status}`);
  return (await res.json()) as ApproveResponse;
}

export interface RunHandle {
  cancel: () => void;
}

// Streams /api/run. Calls onEvent for each event, onDone when complete,
// onError on failure. Returns a handle to cancel.
export function runSentinel(
  onEvent: (e: SentinelEvent) => void,
  onDone: () => void,
  onError: (err: Error) => void,
): RunHandle {
  if (isMockMode()) {
    return replayMock(onEvent, onDone);
  }

  const es = new EventSource('/api/run');
  let closed = false;

  es.onmessage = (msg) => {
    try {
      const evt = JSON.parse(msg.data) as SentinelEvent;
      onEvent(evt);
      if (evt.type === 'done') {
        closed = true;
        es.close();
        onDone();
      }
    } catch (err) {
      onError(err instanceof Error ? err : new Error(String(err)));
    }
  };

  es.onerror = () => {
    if (closed) return;
    // EventSource auto-reconnects; for a one-shot run we surface and stop.
    es.close();
    onError(new Error('Run stream connection error.'));
  };

  return {
    cancel: () => {
      closed = true;
      es.close();
    },
  };
}

function replayMock(
  onEvent: (e: SentinelEvent) => void,
  onDone: () => void,
): RunHandle {
  let i = 0;
  let cancelled = false;
  let timer: ReturnType<typeof setTimeout>;

  const step = () => {
    if (cancelled) return;
    if (i >= MOCK_EVENTS.length) {
      onDone();
      return;
    }
    const evt = MOCK_EVENTS[i++];
    onEvent(evt);
    if (evt.type === 'done') {
      onDone();
      return;
    }
    // Stagger so the timeline streams in like a live run; phases pause longer.
    const wait = evt.type === 'phase' ? 650 : evt.type === 'tool_result' ? 600 : 420;
    timer = setTimeout(step, wait);
  };

  timer = setTimeout(step, 250);

  return {
    cancel: () => {
      cancelled = true;
      clearTimeout(timer);
    },
  };
}

function delay(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}
