import type { RunState } from '../lib/types';

interface Props {
  runState: RunState;
  running: boolean;
  onRun: () => void;
}

export function RunButton({ runState, running, onRun }: Props) {
  const done = runState === 'healed';

  if (running) {
    return (
      <button
        disabled
        className="inline-flex items-center gap-2 rounded-lg border border-hairline bg-elevated px-4 py-2 text-sm font-medium text-zinc-300 cursor-default"
      >
        <Spinner />
        Running Eval Sentinel…
      </button>
    );
  }

  if (done) {
    return (
      <button
        disabled
        className="inline-flex items-center gap-2 rounded-lg border border-ok/30 bg-ok/[0.08] px-4 py-2 text-sm font-medium text-ok cursor-default"
      >
        <Check />
        Run complete
      </button>
    );
  }

  return (
    <button
      onClick={onRun}
      className="group inline-flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white shadow-[0_1px_2px_rgba(0,0,0,0.4),inset_0_1px_0_rgba(255,255,255,0.12)] transition-colors hover:bg-accent-bright active:bg-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-bright focus-visible:ring-offset-2 focus-visible:ring-offset-panel"
    >
      <svg width="11" height="11" viewBox="0 0 12 12" fill="currentColor" aria-hidden>
        <path d="M3 2.2L10 6L3 9.8V2.2Z" />
      </svg>
      Run Eval Sentinel
    </button>
  );
}

function Spinner() {
  return (
    <span className="inline-block h-3.5 w-3.5 rounded-full border-2 border-zinc-600 border-t-accent-bright animate-spinSlow" />
  );
}

function Check() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden>
      <path
        d="M2 6.5L5 9.5L10 3"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
