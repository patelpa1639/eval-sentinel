import type {
  SentinelEvent,
  Phase,
  RegressionRow,
  FailureRow,
  RecoveryRow,
} from '../lib/types';
import { Markdown } from '../lib/markdown';

interface Props {
  events: SentinelEvent[];
}

const PHASE_META: Record<Phase, { glyph: string; cls: string }> = {
  detect: { glyph: '◎', cls: 'text-regress border-regress/40' },
  root_cause: { glyph: '⌕', cls: 'text-progress border-progress/40' },
  propose: { glyph: '✎', cls: 'text-accent border-accent/40' },
  verify: { glyph: '↻', cls: 'text-progress border-progress/40' },
  approval: { glyph: '⏸', cls: 'text-accent border-accent/40' },
  report: { glyph: '▤', cls: 'text-ok border-ok/40' },
};

export function RunTimeline({ events }: Props) {
  // Skip approval_gate + done here (handled elsewhere / terminal).
  const nodes = events.filter(
    (e) => e.type !== 'approval_gate' && e.type !== 'done',
  );

  if (nodes.length === 0) {
    return (
      <div className="text-zinc-600 text-sm py-10 text-center border border-dashed border-zinc-800 rounded-md font-mono">
        timeline empty — run Eval Sentinel to stream the incident
      </div>
    );
  }

  return (
    <ol className="relative">
      {/* spine */}
      <div className="absolute left-[7px] top-1 bottom-1 w-px bg-zinc-800" />
      {nodes.map((e, i) => (
        <li key={i} className="relative pl-7 pb-4 last:pb-0 animate-nodeIn">
          <Dot event={e} />
          <Node event={e} />
        </li>
      ))}
    </ol>
  );
}

function Dot({ event }: { event: SentinelEvent }) {
  let cls = 'bg-zinc-700 border-zinc-600';
  if (event.type === 'phase') {
    cls = PHASE_META[event.phase].cls.replace('text-', 'bg-').replace(/\/40/, '') + ' border-bg';
  } else if (event.type === 'plan') {
    cls = 'bg-accent border-bg';
  } else if (event.type === 'report') {
    cls = 'bg-ok border-bg';
  }
  return (
    <span
      className={`absolute left-0 top-1 h-[15px] w-[15px] rounded-full border-2 ${cls}`}
    />
  );
}

function Node({ event }: { event: SentinelEvent }) {
  switch (event.type) {
    case 'plan':
      return (
        <Card label="PLAN" labelCls="text-accent">
          <Markdown text={event.text} />
        </Card>
      );

    case 'phase': {
      const meta = PHASE_META[event.phase];
      return (
        <div className="flex items-center gap-2 py-0.5">
          <span className={`font-mono text-sm ${meta.cls.split(' ')[0]}`}>
            {meta.glyph}
          </span>
          <span className="text-zinc-200 text-sm font-medium">{event.label}</span>
          <span className="font-mono text-2xs text-zinc-600 uppercase">
            {event.phase}
          </span>
        </div>
      );
    }

    case 'tool_call':
      return (
        <div className="font-mono text-xs text-zinc-500 py-0.5">
          <span className="text-accent/80">→ {event.name}</span>
          {event.args != null && (
            <span className="text-zinc-600">
              {' '}
              {truncate(JSON.stringify(event.args), 90)}
            </span>
          )}
        </div>
      );

    case 'tool_result':
      return <ToolResult event={event} />;

    case 'narration':
      return (
        <div className="py-0.5">
          <Markdown text={event.text} />
        </div>
      );

    case 'proposed_prompt':
      return (
        <Card label="PROPOSED PROMPT" labelCls="text-accent">
          <pre className="font-mono text-xs text-zinc-300 whitespace-pre-wrap leading-relaxed">
            {event.text}
          </pre>
        </Card>
      );

    case 'report':
      return (
        <Card label="POSTMORTEM" labelCls="text-ok">
          <Markdown text={event.text} />
        </Card>
      );

    default:
      return null;
  }
}

function ToolResult({
  event,
}: {
  event: Extract<SentinelEvent, { type: 'tool_result' }>;
}) {
  const data = event.data as Record<string, unknown>;
  const rows = (data?.rows as unknown[]) ?? [];

  if (event.kind === 'regression') {
    return (
      <Card label="REGRESSION" labelCls="text-regress">
        <Table
          head={['category', 'baseline', 'current', '']}
          rows={(rows as RegressionRow[]).map((r) => {
            const drop = r.current < r.baseline;
            return [
              <span className="text-zinc-300">{r.category}</span>,
              <span className="text-zinc-500 tabular-nums">{r.baseline}%</span>,
              <span
                className={`tabular-nums ${drop ? 'text-regress' : 'text-zinc-300'}`}
              >
                {r.current}%
              </span>,
              drop ? <span className="text-regress">▼ {r.current - r.baseline}</span> : <span />,
            ];
          })}
        />
      </Card>
    );
  }

  if (event.kind === 'failures') {
    return (
      <Card label="FAILING EXAMPLES" labelCls="text-regress">
        <Table
          head={['command', 'expected', 'predicted']}
          rows={(rows as FailureRow[]).map((r) => [
            <span className="text-zinc-300">"{r.command}"</span>,
            <span className="text-ok/80">{r.expected}</span>,
            <span className="text-regress">{r.predicted}</span>,
          ])}
        />
      </Card>
    );
  }

  // recovery
  return (
    <Card label="VERIFIED RECOVERY" labelCls="text-ok">
      <Table
        head={['category', 'before', 'after', '']}
        rows={(rows as RecoveryRow[]).map((r) => {
          const up = r.healed > r.current;
          return [
            <span className="text-zinc-300">{r.category}</span>,
            <span className="text-zinc-500 tabular-nums">{r.current}%</span>,
            <span className={`tabular-nums ${up ? 'text-ok' : 'text-zinc-300'}`}>
              {r.healed}%
            </span>,
            up ? <span className="text-ok">▲ +{r.healed - r.current}</span> : <span />,
          ];
        })}
      />
    </Card>
  );
}

function Card({
  label,
  labelCls,
  children,
}: {
  label: string;
  labelCls: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-md border border-zinc-800 bg-panel p-3 mt-0.5">
      <div className={`font-mono text-2xs tracking-wider mb-2 ${labelCls}`}>
        {label}
      </div>
      {children}
    </div>
  );
}

function Table({
  head,
  rows,
}: {
  head: string[];
  rows: React.ReactNode[][];
}) {
  return (
    <table className="w-full font-mono text-xs">
      <thead>
        <tr className="text-zinc-600 text-left">
          {head.map((h, i) => (
            <th key={i} className="font-normal pb-1.5 pr-3 last:pr-0 uppercase text-2xs">
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((cells, ri) => (
          <tr key={ri} className="border-t border-zinc-800/60">
            {cells.map((c, ci) => (
              <td key={ci} className="py-1.5 pr-3 last:pr-0 align-top">
                {c}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n - 1) + '…' : s;
}
