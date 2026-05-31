import { useMemo } from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { RunState, StateResponse } from '../lib/types';
import { MOCK_TREND, type TrendPoint } from '../lib/mock';

interface Props {
  state: StateResponse;
  runState: RunState;
  mock: boolean;
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: { payload: TrendPoint }[] }) {
  if (!active || !payload || !payload.length) return null;
  const p = payload[0].payload;
  const low = p.accuracy < 100;
  return (
    <div className="rounded-lg border border-hairline bg-elevated/95 backdrop-blur px-3 py-2 shadow-[0_4px_16px_rgba(0,0,0,0.5)]">
      <div className="label text-[#71717A] mb-1">{p.label}</div>
      <div className={`font-mono text-sm tabular-nums ${low ? 'text-regress' : 'text-ok'}`}>
        {p.accuracy}% accuracy
      </div>
    </div>
  );
}

export function TrendChart({ state, runState, mock }: Props) {
  // In mock mode: rich history. In live mode: build honestly from /api/state —
  // baseline → current → (healed only once recovery is observed).
  const data: TrendPoint[] = useMemo(() => {
    if (mock) return MOCK_TREND;
    const pts: TrendPoint[] = [
      { run: 1, label: 'baseline', accuracy: state.baseline.overall },
      {
        run: 2,
        label: 'current',
        accuracy: state.current.overall,
        marker: state.current.overall < state.baseline.overall ? 'dip' : undefined,
      },
    ];
    if (runState === 'healed') {
      pts.push({ run: 3, label: 'healed', accuracy: state.baseline.overall, marker: 'recovery' });
    }
    return pts;
  }, [mock, state, runState]);

  const dip = data.find((d) => d.marker === 'dip');
  const recovery = data.find((d) => d.marker === 'recovery');
  const minVal = Math.min(...data.map((d) => d.accuracy));
  const yMin = Math.max(0, Math.floor((minVal - 8) / 5) * 5);

  return (
    <div className="panel p-5 sm:p-6">
      <div className="flex items-start justify-between gap-4 mb-1">
        <div>
          <h2 className="text-ink text-sm font-semibold tracking-tight">Accuracy over runs</h2>
          <p className="text-zinc-500 text-xs mt-0.5">
            {mock ? 'Last 12 evaluation runs' : 'baseline → current → verified'}
          </p>
        </div>
        <div className="flex items-center gap-3 font-mono text-[0.625rem] text-zinc-500">
          <span className="inline-flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-regress" /> dip
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-ok" /> recovery
          </span>
        </div>
      </div>

      <div className="h-[200px] sm:h-[240px] -ml-2 mt-3">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 12, right: 14, bottom: 4, left: 4 }}>
            <defs>
              <linearGradient id="accFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#818CF8" stopOpacity="0.28" />
                <stop offset="60%" stopColor="#6366F1" stopOpacity="0.06" />
                <stop offset="100%" stopColor="#6366F1" stopOpacity="0" />
              </linearGradient>
              <linearGradient id="accStroke" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#6366F1" />
                <stop offset="100%" stopColor="#818CF8" />
              </linearGradient>
            </defs>
            <CartesianGrid
              stroke="#1C1C22"
              strokeDasharray="2 5"
              vertical={false}
            />
            <XAxis
              dataKey="label"
              tick={{ fill: '#52525B', fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }}
              axisLine={{ stroke: '#1C1C22' }}
              tickLine={false}
              interval="preserveStartEnd"
              minTickGap={mock ? 18 : 0}
              dy={6}
            />
            <YAxis
              domain={[yMin, 100]}
              tick={{ fill: '#52525B', fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }}
              axisLine={false}
              tickLine={false}
              width={34}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#3F3F46', strokeWidth: 1, strokeDasharray: '3 3' }} />
            <Area
              type="monotone"
              dataKey="accuracy"
              stroke="url(#accStroke)"
              strokeWidth={2}
              fill="url(#accFill)"
              dot={false}
              activeDot={{ r: 4, fill: '#818CF8', stroke: '#0E0E12', strokeWidth: 2 }}
              isAnimationActive={false}
            />
            {dip && (
              <ReferenceDot
                x={dip.label}
                y={dip.accuracy}
                r={4.5}
                fill="#FB7185"
                stroke="#0E0E12"
                strokeWidth={2}
                isFront
                label={{ value: `${dip.accuracy}`, position: 'bottom', fill: '#FB7185', fontSize: 11, fontFamily: 'JetBrains Mono, monospace', dy: 4 }}
              />
            )}
            {recovery && (
              <ReferenceDot
                x={recovery.label}
                y={recovery.accuracy}
                r={4.5}
                fill="#34D399"
                stroke="#0E0E12"
                strokeWidth={2}
                isFront
                label={{ value: `${recovery.accuracy}`, position: 'top', fill: '#34D399', fontSize: 11, fontFamily: 'JetBrains Mono, monospace', dy: -4 }}
              />
            )}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
