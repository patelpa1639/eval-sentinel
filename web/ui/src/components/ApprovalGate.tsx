import { useState } from 'react';
import type { ApprovalGateEvent, ApproveResponse } from '../lib/types';
import { approve } from '../lib/api';

interface Props {
  gate: ApprovalGateEvent;
}

export function ApprovalGate({ gate }: Props) {
  const [pending, setPending] = useState<'approve' | 'reject' | null>(null);
  const [result, setResult] = useState<ApproveResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function decide(decision: 'approve' | 'reject') {
    setPending(decision);
    setError(null);
    try {
      const res = await approve(decision);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setPending(null);
    }
  }

  return (
    <div className="rounded-xl border border-accent/30 bg-accent/[0.04] p-4 sm:p-5">
      <div className="flex items-center justify-between gap-3 mb-3">
        <div className="flex items-center gap-2.5">
          <span className="grid h-6 w-6 place-items-center rounded-md border border-accent/30 bg-accent/[0.1] text-accent-bright">
            <svg width="13" height="13" viewBox="0 0 14 14" fill="none">
              <path d="M5 3.5V10.5M9 3.5V10.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </span>
          <span className="text-ink text-sm font-semibold">Approval gate</span>
        </div>
        <span className="font-mono text-2xs text-zinc-500 bg-elevated border border-hairline rounded px-2 py-1">
          {gate.new_experiment_id}
        </span>
      </div>

      <p className="text-zinc-400 text-sm mb-3.5">
        Fix verified. Promote the proposed routing prompt to production?
      </p>

      <pre className="font-mono text-xs text-zinc-300 whitespace-pre-wrap leading-relaxed bg-[#070709] border border-hairline rounded-md p-3 mb-4 max-h-56 overflow-auto">
        {gate.proposed_prompt}
      </pre>

      {result ? (
        <div
          className={`rounded-lg border px-3.5 py-2.5 text-sm flex items-center gap-2 ${
            result.promoted
              ? 'border-ok/30 bg-ok/[0.08] text-ok'
              : 'border-hairline bg-elevated text-zinc-400'
          }`}
        >
          <span className="label">
            {result.promoted ? 'promoted' : 'rejected'}
          </span>
          <span className="text-zinc-300">{result.message}</span>
        </div>
      ) : (
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => decide('approve')}
            disabled={pending !== null}
            className="inline-flex items-center gap-1.5 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.12)] hover:bg-accent-bright disabled:opacity-50 transition-colors"
          >
            {pending === 'approve' ? <Dots /> : <Check />}
            Approve &amp; promote
          </button>
          <button
            onClick={() => decide('reject')}
            disabled={pending !== null}
            className="inline-flex items-center gap-1.5 rounded-lg border border-hairline bg-elevated px-4 py-2 text-sm font-medium text-zinc-300 hover:bg-[#1d1d23] disabled:opacity-50 transition-colors"
          >
            {pending === 'reject' ? <Dots /> : <X />}
            Reject
          </button>
        </div>
      )}

      {error && <p className="text-regress text-xs mt-2 font-mono">{error}</p>}
    </div>
  );
}

function Check() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
      <path d="M2 6.5L5 9.5L10 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
function X() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
      <path d="M3 3L9 9M9 3L3 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}
function Dots() {
  return <span className="inline-block w-3 text-center animate-pulseSoft">…</span>;
}
