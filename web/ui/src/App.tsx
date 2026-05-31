import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type {
  ApprovalGateEvent,
  RunState,
  SentinelEvent,
  StateResponse,
} from './lib/types';
import { fetchState, isMockMode, runSentinel, type RunHandle } from './lib/api';
import { CategoryBars } from './components/CategoryBars';
import { RunButton } from './components/RunButton';
import { RunTimeline } from './components/RunTimeline';
import { ApprovalGate } from './components/ApprovalGate';
import { Sidebar, MobileTopBar } from './components/Sidebar';
import { KpiTiles } from './components/KpiTiles';
import { TrendChart } from './components/TrendChart';

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
  // full streamed timeline can be captured in a headless screenshot.
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
      <Shell mock={mock}>
        <PageHeader runState="regression" dataset={null} running={false} onRun={() => {}} disabled />
        <div className="panel p-5 text-sm font-mono mt-6">
          <span className="text-regress">Failed to load /api/state:</span>{' '}
          <span className="text-zinc-300">{loadError}</span>
          <div className="text-zinc-500 mt-2 leading-relaxed">
            Backend not up? Append <span className="text-accent-bright">?mock=1</span> to the URL or
            run with <span className="text-accent-bright">VITE_MOCK=1</span>.
          </div>
        </div>
      </Shell>
    );
  }

  if (!state) {
    return (
      <Shell mock={mock}>
        <div className="text-zinc-600 font-mono text-sm py-24 text-center">loading state…</div>
      </Shell>
    );
  }

  return (
    <Shell mock={mock}>
      <PageHeader
        runState={runState}
        dataset={state.dataset}
        running={running}
        onRun={startRun}
      />

      <div className="mt-6 sm:mt-7">
        <KpiTiles state={state} runState={runState} mock={mock} />
      </div>

      <div className="mt-4 sm:mt-5 grid grid-cols-1 xl:grid-cols-[minmax(0,1.55fr)_minmax(0,1fr)] gap-4 sm:gap-5 items-start min-w-0">
        <div className="min-w-0">
          <TrendChart state={state} runState={runState} mock={mock} />
        </div>

        <section className="panel p-5 sm:p-6 min-w-0">
          <div className="flex items-center justify-between mb-1">
            <div>
              <h2 className="text-ink text-sm font-semibold tracking-tight">Category breakdown</h2>
              <p className="text-zinc-500 text-xs mt-0.5">Per-category accuracy vs baseline</p>
            </div>
            <a
              href={state.phoenix_url}
              target="_blank"
              rel="noreferrer"
              className="group font-mono text-[0.625rem] text-zinc-500 hover:text-accent-bright transition-colors inline-flex items-center gap-1"
            >
              Phoenix
              <svg width="10" height="10" viewBox="0 0 12 12" fill="none" className="transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5">
                <path d="M3.5 8.5L8.5 3.5M8.5 3.5H4.5M8.5 3.5V7.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </a>
          </div>
          <CategoryBars state={state} runState={runState} healedCategories={healed} />
        </section>
      </div>

      <section className="mt-4 sm:mt-5 panel p-5 sm:p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-ink text-sm font-semibold tracking-tight">Incident timeline</h2>
            <p className="text-zinc-500 text-xs mt-0.5">Autonomous detect → root-cause → fix → verify</p>
          </div>
          {running && (
            <span className="inline-flex items-center gap-2 font-mono text-[0.625rem] text-accent-bright">
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
        {runError && (
          <div className="mt-4 rounded-lg border border-regress/30 bg-regress/[0.06] p-3 text-sm text-regress font-mono">
            {runError}
          </div>
        )}
        <div ref={timelineEndRef} />
      </section>
    </Shell>
  );
}

function PageHeader({
  runState,
  dataset,
  running,
  onRun,
  disabled,
}: {
  runState: RunState;
  dataset: string | null;
  running: boolean;
  onRun: () => void;
  disabled?: boolean;
}) {
  const tone =
    runState === 'regression'
      ? { dot: 'bg-regress', text: 'text-regress', border: 'border-regress/25', bg: 'bg-regress/[0.07]', label: 'Regression' }
      : runState === 'healing'
        ? { dot: 'bg-progress', text: 'text-progress', border: 'border-progress/25', bg: 'bg-progress/[0.07]', label: 'Healing' }
        : runState === 'healed'
          ? { dot: 'bg-ok', text: 'text-ok', border: 'border-ok/25', bg: 'bg-ok/[0.07]', label: 'Healed' }
          : { dot: 'bg-ok', text: 'text-ok', border: 'border-ok/25', bg: 'bg-ok/[0.07]', label: 'Healthy' };

  return (
    <div className="flex items-start sm:items-center justify-between gap-4 flex-wrap">
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="text-ink text-xl sm:text-2xl font-semibold tracking-tight">Overview</h1>
        {dataset && (
          <span className="font-mono text-xs text-zinc-400 bg-elevated border border-hairline rounded-md px-2 py-1">
            {dataset}
          </span>
        )}
        <span
          className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[0.6875rem] ${tone.border} ${tone.bg} ${tone.text}`}
        >
          <span className={`h-1.5 w-1.5 rounded-full ${tone.dot} ${runState === 'healing' ? 'animate-pulseSoft' : ''}`} />
          {tone.label}
        </span>
      </div>
      {!disabled && <RunButton runState={runState} running={running} onRun={onRun} />}
    </div>
  );
}

function Shell({ children, mock }: { children: React.ReactNode; mock: boolean }) {
  return (
    <div className="min-h-full overflow-x-hidden">
      <Sidebar />
      <MobileTopBar />
      <div className="lg:pl-[220px] overflow-x-hidden">
        {mock && (
          <div className="border-b border-accent/15 bg-accent/[0.05] text-accent-bright text-[0.625rem] font-mono text-center py-1.5 tracking-wide px-3 truncate">
            <span className="hidden sm:inline">MOCK MODE · replaying static fixture, no backend</span>
            <span className="sm:hidden">MOCK MODE · static fixture</span>
          </div>
        )}
        <main className="mx-auto w-full max-w-[1100px] px-4 sm:px-7 lg:px-9 py-6 sm:py-9 overflow-x-hidden">{children}</main>
      </div>
    </div>
  );
}
