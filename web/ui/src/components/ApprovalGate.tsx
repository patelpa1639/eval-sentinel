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
    <div className="rounded-md border border-accent/40 bg-accent/[0.03] p-4">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-accent text-sm">⏸</span>
        <span className="text-zinc-100 text-sm font-semibold">Approval gate</span>
        <span className="font-mono text-2xs text-zinc-500">
          {gate.new_experiment_id}
        </span>
      </div>

      <p className="text-zinc-400 text-sm mb-3">
        Fix verified. Promote the proposed routing prompt to production?
      </p>

      <pre className="font-mono text-xs text-zinc-300 whitespace-pre-wrap leading-relaxed bg-panel border border-zinc-800 rounded p-3 mb-4 max-h-56 overflow-auto">
        {gate.proposed_prompt}
      </pre>

      {result ? (
        <div
          className={`rounded-md border px-3 py-2.5 text-sm ${
            result.promoted
              ? 'border-ok/40 bg-ok/5 text-ok'
              : 'border-zinc-700 bg-elevated text-zinc-400'
          }`}
        >
          <span className="font-mono text-2xs uppercase tracking-wide mr-2">
            {result.promoted ? '✓ promoted' : 'rejected'}
          </span>
          {result.message}
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <button
            onClick={() => decide('approve')}
            disabled={pending !== null}
            className="inline-flex items-center gap-1.5 rounded-md border border-ok/40 bg-ok/5 text-ok px-3.5 py-2 text-sm font-medium hover:bg-ok/10 disabled:opacity-50 transition-colors"
          >
            {pending === 'approve' ? '…' : '✓'} Approve
          </button>
          <button
            onClick={() => decide('reject')}
            disabled={pending !== null}
            className="inline-flex items-center gap-1.5 rounded-md border border-zinc-700 bg-elevated text-zinc-300 px-3.5 py-2 text-sm font-medium hover:bg-zinc-800 disabled:opacity-50 transition-colors"
          >
            {pending === 'reject' ? '…' : '✕'} Reject
          </button>
        </div>
      )}

      {error && (
        <p className="text-regress text-xs mt-2 font-mono">{error}</p>
      )}
    </div>
  );
}
