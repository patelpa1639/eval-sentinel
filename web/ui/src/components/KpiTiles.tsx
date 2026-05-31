import { useEffect, useRef, useState } from 'react';
import type { RunState, StateResponse } from '../lib/types';
import { Sparkline } from './Sparkline';
import { MOCK_METRICS } from '../lib/mock';

interface Props {
  state: StateResponse;
  runState: RunState;
  mock: boolean;
}

type Tone = 'accent' | 'ok' | 'regress';

// Count-up hook — eases a number from its previous value to target on change.
// Clamps `t` to [0,1] and always lands exactly on target; a settle timeout
// guarantees the final value even under headless virtual-time where rAF
// timestamps can misbehave.
function useCountUp(target: number, duration = 650) {
  const [val, setVal] = useState(target);
  const fromRef = useRef(target);
  useEffect(() => {
    // Automation harness: snap instantly so screenshots capture the real value.
    if (typeof document !== 'undefined' && document.documentElement.hasAttribute('data-no-anim')) {
      fromRef.current = target;
      setVal(target);
      return;
    }
    const from = fromRef.current;
    if (from === target) {
      setVal(target);
      return;
    }
    const start = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const elapsed = Math.max(0, now - start);
      const t = Math.min(1, elapsed / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      setVal(from + (target - from) * eased);
      if (t < 1) raf = requestAnimationFrame(tick);
      else setVal(target);
    };
    raf = requestAnimationFrame(tick);
    const settle = setTimeout(() => setVal(target), duration + 80);
    fromRef.current = target;
    return () => {
      cancelAnimationFrame(raf);
      clearTimeout(settle);
    };
  }, [target, duration]);
  return val;
}

function DeltaChip({ delta, tone }: { delta: string; tone: Tone | 'neutral' }) {
  const cls =
    tone === 'regress'
      ? 'border-regress/25 bg-regress/[0.07] text-regress'
      : tone === 'ok'
        ? 'border-ok/25 bg-ok/[0.07] text-ok'
        : 'border-hairline bg-elevated text-zinc-500';
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-1.5 py-0.5 font-mono text-[0.625rem] tabular-nums ${cls}`}
    >
      {delta}
    </span>
  );
}

function Tile({
  label,
  value,
  suffix,
  delta,
  spark,
  sparkTone,
}: {
  label: string;
  value: React.ReactNode;
  suffix?: string;
  delta?: { text: string; tone: Tone | 'neutral' };
  spark: number[];
  sparkTone: Tone;
}) {
  return (
    <div className="group relative min-w-0 overflow-hidden rounded-xl border border-hairline bg-panel p-3.5 sm:p-[1.1rem] shadow-[inset_0_1px_0_0_rgba(255,255,255,0.03)] transition-colors hover:border-[#26262d]">
      <div className="flex items-start justify-between gap-2">
        <span className="label leading-tight">{label}</span>
        {delta && <DeltaChip delta={delta.text} tone={delta.tone} />}
      </div>
      <div className="mt-3 flex items-end justify-between gap-2">
        <div className="font-mono text-[1.625rem] sm:text-[1.75rem] leading-none font-semibold text-ink tabular-nums tracking-tight whitespace-nowrap">
          {value}
          {suffix && <span className="text-zinc-600 text-lg font-medium">{suffix}</span>}
        </div>
        <div className="hidden xs:block shrink-0 pb-0.5 opacity-90">
          <Sparkline data={spark} tone={sparkTone} />
        </div>
      </div>
    </div>
  );
}

export function KpiTiles({ state, runState, mock }: Props) {
  const healed = runState === 'healed';
  const overallTarget = healed ? state.baseline.overall : state.current.overall;
  const overall = useCountUp(overallTarget);
  const regressedCount = healed ? 0 : state.regressed_categories.length;
  const regCount = useCountUp(regressedCount, 700);
  const totalCats = Object.keys(state.baseline.per_category).length;

  const evalRuns = mock ? MOCK_METRICS.evalRuns : 2;
  const runsCount = useCountUp(evalRuns, 700);
  const spark = mock
    ? MOCK_METRICS.spark
    : { accuracy: [100, state.current.overall], regressed: [0, state.regressed_categories.length], runs: [1, 2], heal: [120, 108] };

  const accDelta = overallTarget - state.baseline.overall;

  return (
    <div className="kpi-grid grid gap-3 sm:gap-4">
      <Tile
        label="Overall Accuracy"
        value={Math.round(overall)}
        suffix="%"
        delta={
          healed
            ? { text: '+0 · ok', tone: 'ok' }
            : accDelta < 0
              ? { text: `▾ ${Math.abs(accDelta)}`, tone: 'regress' }
              : { text: 'stable', tone: 'neutral' }
        }
        spark={spark.accuracy}
        sparkTone={healed ? 'ok' : 'regress'}
      />
      <Tile
        label="Regressed Categories"
        value={
          <>
            {Math.round(regCount)}
            <span className="text-zinc-600 text-lg"> / {totalCats}</span>
          </>
        }
        delta={
          healed
            ? { text: 'cleared', tone: 'ok' }
            : { text: `${regressedCount} active`, tone: 'regress' }
        }
        spark={spark.regressed}
        sparkTone={healed ? 'ok' : 'regress'}
      />
      <Tile
        label="Eval Runs"
        value={Math.round(runsCount)}
        delta={{ text: mock ? '+1 today' : 'this run', tone: 'neutral' }}
        spark={spark.runs}
        sparkTone="accent"
      />
      <Tile
        label="Mean Time to Heal"
        value={mock ? MOCK_METRICS.meanTimeToHeal : '—'}
        delta={mock ? { text: '▾ 9s', tone: 'ok' } : undefined}
        spark={spark.heal}
        sparkTone="accent"
      />
    </div>
  );
}
