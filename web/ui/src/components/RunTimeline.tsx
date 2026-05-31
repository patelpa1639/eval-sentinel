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

type Sem = 'regress' | 'progress' | 'accent' | 'ok';

const PHASE_META: Record<Phase, { sem: Sem; glyph: React.ReactNode }> = {
  detect: { sem: 'regress', glyph: <IconSearch /> },
  root_cause: { sem: 'progress', glyph: <IconBranch /> },
  propose: { sem: 'accent', glyph: <IconPencil /> },
  verify: { sem: 'progress', glyph: <IconRefresh /> },
  approval: { sem: 'accent', glyph: <IconPause /> },
  report: { sem: 'ok', glyph: <IconDoc /> },
};

const SEM_TEXT: Record<Sem, string> = {
  regress: 'text-regress',
  progress: 'text-progress',
  accent: 'text-accent-bright',
  ok: 'text-ok',
};
const SEM_DOT: Record<Sem, string> = {
  regress: 'bg-regress',
  progress: 'bg-progress',
  accent: 'bg-accent',
  ok: 'bg-ok',
};

export function RunTimeline({ events }: Props) {
  const nodes = events.filter(
    (e) => e.type !== 'approval_gate' && e.type !== 'done',
  );

  if (nodes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-9 text-center">
        <div className="text-zinc-700 mb-3">
          <IconWaveform />
        </div>
        <p className="text-zinc-500 text-sm">
          No incident yet. Run Eval Sentinel to stream the investigation.
        </p>
        <p className="text-zinc-600 text-xs mt-1.5 font-mono">
          detect · root-cause · propose · verify · approve
        </p>
      </div>
    );
  }

  return (
    <ol className="relative">
      {/* spine */}
      <div className="absolute left-[8px] top-2 bottom-2 w-px bg-hairline" />
      {nodes.map((e, i) => (
        <li
          key={i}
          className="relative pl-8 pb-5 last:pb-0 animate-nodeIn"
          style={{ animationDelay: `${Math.min(i, 8) * 20}ms` }}
        >
          <Dot event={e} />
          <Node event={e} />
        </li>
      ))}
    </ol>
  );
}

function Dot({ event }: { event: SentinelEvent }) {
  if (event.type === 'phase') {
    const sem = PHASE_META[event.phase].sem;
    return (
      <span
        className={`absolute left-0 top-0 grid h-[17px] w-[17px] place-items-center rounded-full border border-hairline bg-elevated ${SEM_TEXT[sem]}`}
      >
        <span className="scale-[0.62]">{PHASE_META[event.phase].glyph}</span>
      </span>
    );
  }
  let cls = 'bg-zinc-700';
  if (event.type === 'plan') cls = 'bg-accent';
  else if (event.type === 'report') cls = 'bg-ok';
  else if (event.type === 'proposed_prompt') cls = 'bg-accent';
  return (
    <span className="absolute left-[5px] top-[5px] grid place-items-center">
      <span className={`h-1.5 w-1.5 rounded-full ${cls}`} />
    </span>
  );
}

function Node({ event }: { event: SentinelEvent }) {
  switch (event.type) {
    case 'plan':
      return (
        <Card label="Plan" sem="accent">
          <Markdown text={event.text} />
        </Card>
      );

    case 'phase': {
      return (
        <div className="flex items-center gap-2.5 py-0.5">
          <span className="text-ink text-sm font-medium">{event.label}</span>
          <span className="label text-[#3F3F46]">{event.phase}</span>
        </div>
      );
    }

    case 'tool_call':
      return (
        <div className="font-mono text-xs py-0.5 flex items-baseline gap-2 flex-wrap">
          <span className="text-accent-bright/90">{event.name}</span>
          {event.args != null && (
            <span className="text-zinc-600 truncate">
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
        <Card label="Proposed prompt" sem="accent">
          <CodeBlock text={event.text} />
        </Card>
      );

    case 'report':
      return (
        <Card label="Postmortem" sem="ok">
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
      <Card label="Regression" sem="regress">
        <Table
          head={['category', 'baseline', 'current', 'Δ']}
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
              drop ? (
                <span className="text-regress tabular-nums">
                  {r.current - r.baseline}
                </span>
              ) : (
                <span className="text-zinc-700">—</span>
              ),
            ];
          })}
        />
      </Card>
    );
  }

  if (event.kind === 'failures') {
    return (
      <Card label="Failing examples" sem="regress">
        <Table
          head={['command', 'expected', 'predicted']}
          rows={(rows as FailureRow[]).map((r) => [
            <span className="text-zinc-300">"{r.command}"</span>,
            <span className="text-ok">{r.expected}</span>,
            <span className="text-regress inline-flex items-center gap-1">
              <IconArrowMini /> {r.predicted}
            </span>,
          ])}
        />
      </Card>
    );
  }

  // recovery
  return (
    <Card label="Verified recovery" sem="ok">
      <Table
        head={['category', 'before', 'after', 'Δ']}
        rows={(rows as RecoveryRow[]).map((r) => {
          const up = r.healed > r.current;
          return [
            <span className="text-zinc-300">{r.category}</span>,
            <span className="text-zinc-500 tabular-nums">{r.current}%</span>,
            <span className={`tabular-nums ${up ? 'text-ok' : 'text-zinc-300'}`}>
              {r.healed}%
            </span>,
            up ? (
              <span className="text-ok tabular-nums">+{r.healed - r.current}</span>
            ) : (
              <span className="text-zinc-700">—</span>
            ),
          ];
        })}
      />
    </Card>
  );
}

function Card({
  label,
  sem,
  children,
}: {
  label: string;
  sem: Sem;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-hairline bg-bg/60 p-3.5 mt-1">
      <div className="flex items-center gap-2 mb-2.5">
        <span className={`h-1.5 w-1.5 rounded-full ${SEM_DOT[sem]}`} />
        <span className="label text-zinc-400">{label}</span>
      </div>
      {children}
    </div>
  );
}

function CodeBlock({ text }: { text: string }) {
  return (
    <pre className="font-mono text-xs text-zinc-300 whitespace-pre-wrap leading-relaxed bg-[#070709] border border-hairline rounded-md p-3 overflow-x-auto">
      {text}
    </pre>
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
        <tr className="text-left">
          {head.map((h, i) => (
            <th
              key={i}
              className="label font-normal pb-2 pr-4 last:pr-0 text-[#52525B]"
            >
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((cells, ri) => (
          <tr key={ri} className="border-t border-hairline/70">
            {cells.map((c, ci) => (
              <td key={ci} className="py-2 pr-4 last:pr-0 align-top">
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

/* ---- glyphs (small, functional) ---- */
function IconSearch() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <circle cx="6" cy="6" r="4" stroke="currentColor" strokeWidth="1.4" />
      <path d="M9 9L12 12" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}
function IconBranch() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <circle cx="4" cy="3.5" r="1.6" stroke="currentColor" strokeWidth="1.3" />
      <circle cx="4" cy="10.5" r="1.6" stroke="currentColor" strokeWidth="1.3" />
      <circle cx="10" cy="3.5" r="1.6" stroke="currentColor" strokeWidth="1.3" />
      <path d="M4 5v4M5.6 3.5H8.4M10 5v1.5c0 2-2 2-3.5 2.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}
function IconPencil() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M9.5 2.5L11.5 4.5L5 11L2.5 11.5L3 9L9.5 2.5Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
    </svg>
  );
}
function IconRefresh() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M11.5 6A4.5 4.5 0 1 1 10 3.2" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      <path d="M10.5 1.5V3.5H8.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
function IconPause() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M5 3.5V10.5M9 3.5V10.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}
function IconDoc() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M3.5 2.5H8L10.5 5V11.5H3.5V2.5Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
      <path d="M5.5 7H8.5M5.5 9H8.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}
function IconArrowMini() {
  return (
    <svg width="9" height="9" viewBox="0 0 10 10" fill="none">
      <path d="M2 5H8M8 5L5.5 2.5M8 5L5.5 7.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
function IconWaveform() {
  return (
    <svg width="30" height="30" viewBox="0 0 30 30" fill="none">
      <path
        d="M3 15H7L10 8L14 22L18 11L21 18L24 15H27"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
