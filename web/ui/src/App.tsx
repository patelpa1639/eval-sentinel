import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type {
  ApprovalGateEvent,
  RunState,
  SentinelEvent,
  StateResponse,
} from './lib/types';
import { fetchState, isMockMode, runSentinel, type RunHandle } from './lib/api';
import { StatusHeader } from './components/StatusHeader';
import { CategoryBars } from './components/CategoryBars';
import { RunButton } from './components/RunButton';
import { RunTimeline } from './components/RunTimeline';
import { ApprovalGate } from './components/ApprovalGate';

export default function App() {
  const [state, setState] = useState<StateResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [events, setEvents] = useState<SentinelEvent[]>([]);
  const [running, setRunning] = useState(false);
  const [runState, setRunState] = useState<RunState>('healthy');
  const [healed, setHealed] = useState<Set<string>>(new Set());
  const [gate, setGate] = useState<ApprovalGateEvent | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  const handleRef = useRef<RunHandle | null>(null);
  const timelineEndRef = useRef<HTMLDivElement | null>(null);

  // Initial state load. Reflects the regression that already exists.
  useEffect(() => {
    fetchState()
      .then((s) => {
        setState(s);
        setRunState(s.regressed_categories.length > 0 ? 'regression' : 'healthy');
      })
      .catch((e) => setLoadError(e instanceof Error ? e.message : String(e)));
  }, []);

  // Auto-scroll the timeline as events stream in.
  useEffect(() => {
    timelineEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [events.length]);

  const onEvent = useCallback((e: SentinelEvent) => {
    setEvents((prev) => [...prev, e]);

    if (e.type === 'phase') {
      if (e.phase === 'report' || e.phase === 'approval') {
        // keep healing pill until healed; approval reached after verify
      }
    }
    if (e.type === 'tool_result' && e.kind === 'recovery') {
      // Mark regressed categories as healed -> bars animate up.
      const data = e.data as { rows?: { category: string }[] };
      const cats = (data.rows ?? []).map((r) => r.category);
      setHealed((prev) => {
        const next = new Set(prev);
        cats.forEach((c) => next.add(c));
        return next;
      });
      setRunState('healed');
    }
    if (e.type === 'approval_gate') {
      setGate(e);
    }
  }, []);

  const onDone = useCallback(() => {
    setRunning(false);
    setRunState((s) => (s === 'healing' ? 'healed' : s));
  }, []);

  const onError = useCallback((err: Error) => {
    setRunning(false);
    setRunError(err.message);
  }, []);

  const startRun = useCallback(() => {
    if (!state) return;
    setEvents([]);
    setHealed(new Set());
    setGate(null);
    setRunError(null);
    setRunning(true);
    setRunState('healing');
    handleRef.current = runSentinel(onEvent, onDone, onError);
  }, [state, onEvent, onDone, onError]);

  useEffect(() => () => handleRef.current?.cancel(), []);

  const mock = useMemo(() => isMockMode(), []);

  if (loadError && !state) {
    return (
      <Shell mock={mock}>
        <div className="rounded-md border border-regress/40 bg-regress/5 p-4 text-sm text-regress font-mono">
          Failed to load /api/state: {loadError}
          <div className="text-zinc-500 mt-2">
            Backend not up? Append <span className="text-accent">?mock=1</span> to
            the URL or run with <span className="text-accent">VITE_MOCK=1</span>.
          </div>
        </div>
      </Shell>
    );
  }

  if (!state) {
    return (
      <Shell mock={mock}>
        <div className="text-zinc-600 font-mono text-sm py-10">loading state…</div>
      </Shell>
    );
  }

  return (
    <Shell mock={mock}>
      <div className="rounded-lg border border-zinc-800 bg-panel p-5">
        <StatusHeader state={state} runState={runState} />
        <CategoryBars state={state} runState={runState} healedCategories={healed} />

        <div className="mt-5 flex items-center justify-between gap-3 flex-wrap">
          <RunButton runState={runState} running={running} onRun={startRun} />
          <a
            href={state.phoenix_url}
            target="_blank"
            rel="noreferrer"
            className="font-mono text-xs text-zinc-500 hover:text-accent transition-colors inline-flex items-center gap-1.5"
          >
            <span className="text-[0.7rem]">↗</span> open in Phoenix
          </a>
        </div>

        {runError && (
          <div className="mt-3 rounded-md border border-regress/40 bg-regress/5 p-3 text-sm text-regress font-mono">
            {runError}
          </div>
        )}
      </div>

      <section className="mt-5 rounded-lg border border-zinc-800 bg-panel p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-zinc-200 text-sm font-semibold">Incident timeline</h2>
          {running && (
            <span className="font-mono text-2xs text-progress animate-pulseSoft">
              ● streaming
            </span>
          )}
        </div>
        <RunTimeline events={events} />

        {gate && (
          <div className="mt-4">
            <ApprovalGate gate={gate} />
          </div>
        )}
        <div ref={timelineEndRef} />
      </section>
    </Shell>
  );
}

function Shell({
  children,
  mock,
}: {
  children: React.ReactNode;
  mock: boolean;
}) {
  return (
    <div className="min-h-full">
      {mock && (
        <div className="bg-progress/10 border-b border-progress/30 text-progress text-2xs font-mono text-center py-1">
          MOCK MODE — replaying static fixture, no backend
        </div>
      )}
      <main className="mx-auto max-w-3xl px-4 py-6 sm:py-10">{children}</main>
    </div>
  );
}
