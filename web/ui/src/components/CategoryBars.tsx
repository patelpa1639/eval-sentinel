import type { RunState, StateResponse } from '../lib/types';

interface Props {
  state: StateResponse;
  runState: RunState;
  // categories already verified-healed (animate to 100 as recovery streams in)
  healedCategories: Set<string>;
}

const SEGMENTS = 11; // matches the ASCII mock's bar width

function Bar({
  pct,
  tone,
}: {
  pct: number;
  tone: 'ok' | 'regress' | 'healing';
}) {
  const color =
    tone === 'regress'
      ? 'bg-regress'
      : tone === 'healing'
        ? 'bg-progress'
        : 'bg-ok';
  // Render as discrete blocks like the mock (██████▒▒▒▒▒) but smooth-filled.
  return (
    <div className="relative h-2.5 w-full rounded-sm overflow-hidden bg-elevated border border-zinc-800">
      <div
        className={`bar-fill absolute inset-y-0 left-0 ${color}`}
        style={{ width: `${pct}%` }}
      />
      {/* segment ticks for the dense ops-console feel */}
      <div className="absolute inset-0 flex">
        {Array.from({ length: SEGMENTS - 1 }).map((_, i) => (
          <div
            key={i}
            className="flex-1 border-r border-bg/60 last:border-r-0"
          />
        ))}
      </div>
    </div>
  );
}

export function CategoryBars({ state, runState, healedCategories }: Props) {
  const cats = Object.keys(state.baseline.per_category);
  const regressed = new Set(state.regressed_categories);

  return (
    <div className="space-y-2.5">
      {cats.map((cat) => {
        const baseline = state.baseline.per_category[cat];
        const current = state.current.per_category[cat];
        const isRegressed = regressed.has(cat);
        const isHealed = healedCategories.has(cat);

        // Determine displayed value + tone for the current run state.
        let pct: number;
        let tone: 'ok' | 'regress' | 'healing';
        let badge: { text: string; cls: string } | null = null;

        if (runState === 'healthy') {
          pct = baseline;
          tone = 'ok';
        } else if (isRegressed && !isHealed) {
          pct = current;
          tone = runState === 'healing' ? 'healing' : 'regress';
          if (runState === 'regression') {
            badge = { text: '▼ regressed', cls: 'text-regress' };
          } else if (runState === 'healing') {
            badge = { text: 'healing…', cls: 'text-progress' };
          } else {
            badge = { text: '▼ regressed', cls: 'text-regress' };
          }
        } else if (isRegressed && isHealed) {
          pct = baseline; // recovered to 100
          tone = 'ok';
          badge = { text: '✓ healed', cls: 'text-ok' };
        } else {
          pct = baseline;
          tone = 'ok';
        }

        return (
          <div key={cat} className="grid grid-cols-[5.5rem_1fr_auto] items-center gap-3">
            <span className="font-mono text-xs text-zinc-400 truncate">{cat}</span>
            <Bar pct={pct} tone={tone} />
            <div className="flex items-center gap-2 justify-end min-w-[7.5rem]">
              <span
                className={`font-mono text-xs tabular-nums w-9 text-right ${
                  tone === 'regress'
                    ? 'text-regress'
                    : tone === 'healing'
                      ? 'text-progress'
                      : 'text-zinc-300'
                }`}
              >
                {pct}%
              </span>
              {badge ? (
                <span className={`font-mono text-2xs ${badge.cls} w-16`}>
                  {badge.text}
                </span>
              ) : (
                <span className="w-16" />
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
