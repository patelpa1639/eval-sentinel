import type { RunState, StateResponse } from '../lib/types';

interface Props {
  state: StateResponse;
  runState: RunState;
}

const PILL: Record<
  RunState,
  { label: string; glyph: string; cls: string; dot: string }
> = {
  healthy: {
    label: 'Healthy',
    glyph: '',
    cls: 'text-ok border-ok/30 bg-ok/5',
    dot: 'bg-ok',
  },
  regression: {
    label: 'Regression detected',
    glyph: '⚠',
    cls: 'text-regress border-regress/40 bg-regress/5',
    dot: 'bg-regress',
  },
  healing: {
    label: 'Healing…',
    glyph: '',
    cls: 'text-progress border-progress/40 bg-progress/5',
    dot: 'bg-progress animate-pulseSoft',
  },
  healed: {
    label: 'Healed',
    glyph: '✓',
    cls: 'text-ok border-ok/40 bg-ok/5',
    dot: 'bg-ok',
  },
};

export function StatusHeader({ state, runState }: Props) {
  const pill = PILL[runState];
  // Overall to show: baseline when healthy, healed (100) when healed, else current.
  const overall =
    runState === 'healthy'
      ? state.baseline.overall
      : runState === 'healed'
        ? state.baseline.overall
        : state.current.overall;
  const delta = overall - state.baseline.overall;

  return (
    <header className="border-b border-zinc-800 pb-4 mb-5">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <div className="h-7 w-7 rounded-sm border border-zinc-700 grid place-items-center bg-elevated">
            <span className="text-accent font-mono text-sm font-semibold">ES</span>
          </div>
          <div>
            <h1 className="text-zinc-100 font-semibold text-base tracking-tight leading-none">
              Eval Sentinel
            </h1>
            <p className="text-zinc-500 text-xs mt-1 font-mono">{state.dataset}</p>
          </div>
        </div>

        <div
          className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-md border text-xs font-medium ${pill.cls}`}
        >
          <span className={`h-1.5 w-1.5 rounded-full ${pill.dot}`} />
          {pill.glyph && <span className="text-sm leading-none">{pill.glyph}</span>}
          {pill.label}
        </div>
      </div>

      <div className="mt-4 flex items-baseline gap-3">
        <span className="text-zinc-500 text-xs uppercase tracking-wide">
          Overall
        </span>
        <span className="font-mono text-3xl font-semibold text-zinc-100 tabular-nums">
          {overall}%
        </span>
        {delta !== 0 && (
          <span
            className={`font-mono text-sm font-medium ${
              delta < 0 ? 'text-regress' : 'text-ok'
            }`}
          >
            {delta < 0 ? '▼' : '▲'} {delta > 0 ? '+' : ''}
            {delta}
          </span>
        )}
        {delta === 0 && runState === 'healed' && (
          <span className="font-mono text-sm text-ok">restored</span>
        )}
      </div>
    </header>
  );
}
