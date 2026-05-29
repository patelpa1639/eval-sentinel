import type { RunState } from '../lib/types';

interface Props {
  runState: RunState;
  running: boolean;
  onRun: () => void;
}

export function RunButton({ runState, running, onRun }: Props) {
  const done = runState === 'healed';
  return (
    <button
      onClick={onRun}
      disabled={running || done}
      className={`group inline-flex items-center gap-2 rounded-md border px-3.5 py-2 text-sm font-medium transition-colors
        ${
          running
            ? 'border-progress/40 text-progress bg-progress/5 cursor-default'
            : done
              ? 'border-ok/40 text-ok bg-ok/5 cursor-default'
              : 'border-accent/40 text-accent bg-accent/5 hover:bg-accent/10 active:bg-accent/15'
        }`}
    >
      {running ? (
        <>
          <Spinner />
          Running Eval Sentinel…
        </>
      ) : done ? (
        <>
          <span>✓</span>
          Run complete
        </>
      ) : (
        <>
          <span className="text-[0.7rem]">▶</span>
          Run Eval Sentinel
        </>
      )}
    </button>
  );
}

function Spinner() {
  return (
    <span className="inline-block h-3.5 w-3.5 rounded-full border-2 border-progress/30 border-t-progress animate-spin" />
  );
}
