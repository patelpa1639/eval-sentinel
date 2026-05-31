import type { RunState, StateResponse } from '../lib/types';

interface Props {
  state: StateResponse;
  runState: RunState;
  // categories already verified-healed (animate to 100 as recovery streams in)
  healedCategories: Set<string>;
}

type Tone = 'ok' | 'regress' | 'healing';

function Bar({
  pct,
  tone,
  showGhost,
  emphasis,
}: {
  pct: number;
  tone: Tone;
  // baseline ghost tick at 100% — shows the drop on regressed rows
  showGhost: boolean;
  // 'attention' rows (regressed/healing/healed) pop; calm rows stay muted.
  emphasis: 'attention' | 'calm';
}) {
  let fillStyle: React.CSSProperties;
  if (tone === 'regress') {
    fillStyle = { backgroundColor: '#FB7185' };
  } else if (tone === 'healing') {
    fillStyle = { backgroundColor: '#F59E0B' };
  } else if (emphasis === 'attention') {
    // healed — brighter calm emerald so the recovery reads
    fillStyle = { backgroundColor: '#34D399' };
  } else {
    // calm healthy — muted, low-intensity so it recedes
    fillStyle = { backgroundColor: 'rgba(52,211,153,0.32)' };
  }
  return (
    <div
      className="relative h-2 w-full rounded-full"
      style={{ backgroundColor: 'rgba(255,255,255,0.05)' }}
    >
      {showGhost && (
        <>
          {/* faint baseline track from current → 100 */}
          <div
            className="absolute inset-y-0 rounded-full"
            style={{
              left: `${pct}%`,
              right: 0,
              backgroundColor: 'rgba(251,113,133,0.10)',
            }}
          />
          {/* baseline ghost tick at the 100% mark */}
          <div className="absolute -top-0.5 -bottom-0.5 right-0 w-px bg-regress/40" />
        </>
      )}
      <div
        className="bar-fill absolute inset-y-0 left-0 rounded-full"
        style={{ width: `${pct}%`, ...fillStyle }}
      />
    </div>
  );
}

export function CategoryBars({ state, runState, healedCategories }: Props) {
  const cats = Object.keys(state.baseline.per_category);
  const regressed = new Set(state.regressed_categories);

  return (
    <div className="mt-7 space-y-3.5">
      {cats.map((cat) => {
        const baseline = state.baseline.per_category[cat];
        const current = state.current.per_category[cat];
        const isRegressed = regressed.has(cat);
        const isHealed = healedCategories.has(cat);

        let pct: number;
        let tone: Tone;
        let showGhost = false;
        let tag: { text: string; cls: string } | null = null;
        let deltaNode: React.ReactNode = null;

        if (runState === 'healthy') {
          pct = baseline;
          tone = 'ok';
        } else if (isRegressed && !isHealed) {
          pct = current;
          tone = runState === 'healing' ? 'healing' : 'regress';
          showGhost = runState !== 'healing';
          const drop = current - baseline;
          if (runState === 'healing') {
            tag = {
              text: 'healing',
              cls: 'text-progress border-progress/30 bg-progress/[0.08]',
            };
          } else {
            tag = {
              text: 'regressed',
              cls: 'text-regress border-regress/30 bg-regress/[0.08]',
            };
            deltaNode = (
              <span className="hidden sm:inline font-mono text-xs text-regress tabular-nums">
                {drop}
              </span>
            );
          }
        } else if (isRegressed && isHealed) {
          pct = baseline;
          tone = 'ok';
          tag = {
            text: 'healed',
            cls: 'text-ok border-ok/30 bg-ok/[0.08]',
          };
        } else {
          pct = baseline;
          tone = 'ok';
        }

        const isAttention = isRegressed || isHealed;
        const pctCls =
          tone === 'regress'
            ? 'text-regress'
            : tone === 'healing'
              ? 'text-progress'
              : isHealed
                ? 'text-ok'
                : 'text-zinc-500';

        return (
          <div
            key={cat}
            className="grid grid-cols-[3.5rem_minmax(0,1fr)_auto] sm:grid-cols-[4.5rem_minmax(0,1fr)_auto] items-center gap-2.5 sm:gap-4"
          >
            <span
              className={`font-mono text-xs ${
                isAttention && tone !== 'ok' ? 'text-zinc-300' : 'text-zinc-500'
              }`}
            >
              {cat}
            </span>
            <Bar
              pct={pct}
              tone={tone}
              showGhost={showGhost}
              emphasis={isAttention ? 'attention' : 'calm'}
            />
            <div className="flex items-center justify-end gap-2 sm:gap-2.5 sm:min-w-[7.5rem]">
              {deltaNode}
              <span
                className={`font-mono text-sm tabular-nums w-10 text-right ${pctCls}`}
              >
                {pct}%
              </span>
              {tag ? (
                <span
                  className={`hidden xs:inline-flex sm:inline-flex items-center justify-center rounded-full border px-2 py-0.5 font-mono text-2xs sm:w-[4.75rem] ${tag.cls}`}
                >
                  {tag.text}
                </span>
              ) : (
                <span className="hidden sm:block w-[4.75rem]" />
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
