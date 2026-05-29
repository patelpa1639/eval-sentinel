import type { RunState, StateResponse } from '../lib/types';

interface Props {
  state: StateResponse;
  runState: RunState;
}

export function StatusHeader({ state, runState }: Props) {
  // Overall to show: baseline when healthy, restored (100) when healed, else current.
  const overall =
    runState === 'healthy' || runState === 'healed'
      ? state.baseline.overall
      : state.current.overall;
  const delta = overall - state.baseline.overall;

  const headline =
    runState === 'regression'
      ? `${state.regressed_categories.length} categories regressed`
      : runState === 'healing'
        ? 'Diagnosing and verifying a fix'
        : runState === 'healed'
          ? 'Fix verified — restored to baseline'
          : 'All categories at baseline';

  return (
    <header>
      <div className="flex items-end justify-between gap-6 flex-wrap">
        <div>
          <div className="label mb-2.5">Overall accuracy</div>
          <div className="flex items-baseline gap-3">
            <span className="font-mono text-[2.75rem] leading-none font-semibold text-ink tabular-nums tracking-tight">
              {overall}
              <span className="text-zinc-500 text-2xl font-medium">%</span>
            </span>
            <DeltaPill delta={delta} runState={runState} />
          </div>
          <p className="text-zinc-400 text-sm mt-3">{headline}</p>
        </div>

        <div className="text-right hidden sm:block">
          <div className="label mb-2.5">Baseline</div>
          <span className="font-mono text-xl text-zinc-500 tabular-nums">
            {state.baseline.overall}%
          </span>
        </div>
      </div>
    </header>
  );
}

function DeltaPill({ delta, runState }: { delta: number; runState: RunState }) {
  if (delta === 0) {
    if (runState === 'healed') {
      return (
        <span className="inline-flex items-center gap-1 rounded-full border border-ok/30 bg-ok/[0.08] px-2 py-0.5 font-mono text-xs font-medium text-ok">
          <Check /> restored
        </span>
      );
    }
    return null;
  }
  const down = delta < 0;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-mono text-xs font-medium tabular-nums ${
        down
          ? 'border border-regress/30 bg-regress/[0.08] text-regress'
          : 'border border-ok/30 bg-ok/[0.08] text-ok'
      }`}
    >
      {down ? <Arrow down /> : <Arrow />}
      {delta > 0 ? '+' : ''}
      {delta}
    </span>
  );
}

function Arrow({ down }: { down?: boolean }) {
  return (
    <svg width="9" height="9" viewBox="0 0 10 10" fill="none">
      <path
        d={down ? 'M5 1.5V8.5M5 8.5L2 5.5M5 8.5L8 5.5' : 'M5 8.5V1.5M5 1.5L2 4.5M5 1.5L8 4.5'}
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function Check() {
  return (
    <svg width="9" height="9" viewBox="0 0 10 10" fill="none">
      <path
        d="M1.5 5.5L4 8L8.5 2.5"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
