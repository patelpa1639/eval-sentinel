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

  useEffect(() => {
    fetchState()
      .then((s) => {
        setState(s);
        setRunState(s.regressed_categories.length > 0 ? 'regression' : 'healthy');
      })
      .catch((e) => setLoadError(e instanceof Error ? e.message : String(e)));
  }, []);

  useEffect(() => {
    timelineEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [events.length]);

  const onEvent = useCallback((e: SentinelEvent) => {
    setEvents((prev) => [...prev, e]);

    if (e.type === 'tool_result' && e.kind === 'recovery') {
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

  // Mock-only convenience: ?autorun=1 kicks off the replay automatically so the
  // full streamed timeline can be captured in a headless screenshot. No effect
  // against the real backend.
  const autoRunRef = useRef(false);
  useEffect(() => {
    if (!mock || autoRunRef.current || !state) return;
    const q = new URLSearchParams(window.location.search);
    if (q.get('autorun') === '1') {
      autoRunRef.current = true;
      startRun();
    }
  }, [mock, state, startRun]);

  if (loadError && !state) {
    return (
      <Shell mock={mock} dataset={null} runState={runState}>
        <div className="panel p-5 text-sm font-mono">
          <span className="text-regress">Failed to load /api/state:</span>{' '}
          <span className="text-zinc-300">{loadError}</span>
          <div className="text-zinc-500 mt-2 leading-relaxed">
            Backend not up? Append <span className="text-accent-bright">?mock=1</span>{' '}
            to the URL or run with{' '}
            <span className="text-accent-bright">VITE_MOCK=1</span>.
          </div>
        </div>
      </Shell>
    );
  }

  if (!state) {
    return (
      <Shell mock={mock} dataset={null} runState={runState}>
        <div className="text-zinc-600 font-mono text-sm py-16 text-center">
          loading state…
        </div>
      </Shell>
    );
  }

  return (
    <Shell mock={mock} dataset={state.dataset} runState={runState}>
      <section className="panel p-6 sm:p-7">
        <StatusHeader state={state} runState={runState} />
        <CategoryBars
          state={state}
          runState={runState}
          healedCategories={healed}
        />

        <div className="mt-7 flex items-center justify-between gap-4 flex-wrap border-t border-hairline pt-5">
          <RunButton runState={runState} running={running} onRun={startRun} />
          <a
            href={state.phoenix_url}
            target="_blank"
            rel="noreferrer"
            className="group font-mono text-xs text-zinc-500 hover:text-accent-bright transition-colors inline-flex items-center gap-1.5"
          >
            open in Phoenix
            <svg
              width="11"
              height="11"
              viewBox="0 0 12 12"
              fill="none"
              className="transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
            >
              <path
                d="M3.5 8.5L8.5 3.5M8.5 3.5H4.5M8.5 3.5V7.5"
                stroke="currentColor"
                strokeWidth="1.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </a>
        </div>

        {runError && (
          <div className="mt-4 rounded-lg border border-regress/30 bg-regress/[0.06] p-3 text-sm text-regress font-mono">
            {runError}
          </div>
        )}
      </section>

      <section className="mt-5 panel p-6 sm:p-7">
        <div className="flex items-center justify-between mb-5">
          <h2 className="label">Incident timeline</h2>
          {running && (
            <span className="inline-flex items-center gap-2 font-mono text-2xs text-accent-bright">
              <span className="relative flex h-1.5 w-1.5">
                <span className="absolute inline-flex h-full w-full rounded-full bg-accent animate-livePulse" />
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-accent-bright" />
              </span>
              streaming
            </span>
          )}
        </div>
        <RunTimeline events={events} />

        {gate && (
          <div className="mt-5">
            <ApprovalGate gate={gate} />
          </div>
        )}
        <div ref={timelineEndRef} />
      </section>
    </Shell>
  );
}

function ShieldMark() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M12 2.5L4 5.5V11C4 15.6 7.4 19.7 12 21.5C16.6 19.7 20 15.6 20 11V5.5L12 2.5Z"
        stroke="url(#sg)"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
      <path
        d="M7.5 12.2L10 12.2L11.2 9L12.9 15L14.1 12.2L16.5 12.2"
        stroke="#818CF8"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <defs>
        <linearGradient id="sg" x1="12" y1="2.5" x2="12" y2="21.5" gradientUnits="userSpaceOnUse">
          <stop stopColor="#818CF8" />
          <stop offset="1" stopColor="#6366F1" stopOpacity="0.6" />
        </linearGradient>
      </defs>
    </svg>
  );
}

function Shell({
  children,
  mock,
  dataset,
  runState,
}: {
  children: React.ReactNode;
  mock: boolean;
  dataset: string | null;
  runState: RunState;
}) {
  const statusTone =
    runState === 'regression'
      ? 'text-regress'
      : runState === 'healing'
        ? 'text-progress'
        : runState === 'healed'
          ? 'text-ok'
          : 'text-ok';
  const statusDot =
    runState === 'regression'
      ? 'bg-regress'
      : runState === 'healing'
        ? 'bg-progress'
        : 'bg-ok';
  const statusLabel =
    runState === 'regression'
      ? 'Regression'
      : runState === 'healing'
        ? 'Healing'
        : runState === 'healed'
          ? 'Healed'
          : 'Healthy';

  return (
    <div className="min-h-full">
      <header className="sticky top-0 z-20 border-b border-hairline bg-bg/80 backdrop-blur-md">
        <div className="mx-auto max-w-5xl px-5 sm:px-8 h-14 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2.5 min-w-0">
            <ShieldMark />
            <span className="text-ink font-semibold text-[0.95rem] tracking-tight">
              Eval Sentinel
            </span>
            {dataset && (
              <>
                <span className="text-hairline select-none">/</span>
                <span className="font-mono text-xs text-zinc-400 bg-elevated border border-hairline rounded-md px-2 py-1 truncate max-w-[40vw] sm:max-w-none">
                  {dataset}
                </span>
              </>
            )}
          </div>
          <div className="flex items-center gap-4 shrink-0">
            <span className="inline-flex items-center gap-1.5 font-mono text-2xs">
              <span className={`h-1.5 w-1.5 rounded-full ${statusDot}`} />
              <span className={`${statusTone} hidden xs:inline sm:inline`}>
                {statusLabel}
              </span>
            </span>
          </div>
        </div>
        {mock && (
          <div className="border-t border-accent/20 bg-accent/[0.06] text-accent-bright text-2xs font-mono text-center py-1 tracking-wide px-3 truncate">
            <span className="hidden sm:inline">
              MOCK MODE · replaying static fixture, no backend
            </span>
            <span className="sm:hidden">MOCK MODE · static fixture</span>
          </div>
        )}
      </header>

      <main className="mx-auto max-w-5xl px-5 sm:px-8 py-8 sm:py-12">
        {children}
      </main>
    </div>
  );
}
