import { useState } from 'react';

function ShieldMark({ size = 24 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M12 2.5L4 5.5V11C4 15.6 7.4 19.7 12 21.5C16.6 19.7 20 15.6 20 11V5.5L12 2.5Z"
        stroke="url(#sg)"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
      <path
        d="M7.5 12.2L10 12.2L11.2 9L12.9 15L14.1 12.2L16.5 12.2"
        stroke="#818CF8"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <defs>
        <linearGradient id="sg" x1="12" y1="2.5" x2="12" y2="21.5" gradientUnits="userSpaceOnUse">
          <stop stopColor="#818CF8" />
          <stop offset="1" stopColor="#6366F1" stopOpacity="0.6" />
        </linearGradient>
      </defs>
    </svg>
  );
}

interface NavItem {
  label: string;
  icon: React.ReactNode;
  active?: boolean;
}

const NAV: NavItem[] = [
  { label: 'Overview', icon: <IconGrid />, active: true },
  { label: 'Eval Runs', icon: <IconRuns /> },
  { label: 'Datasets', icon: <IconStack /> },
  { label: 'Prompts', icon: <IconPrompt /> },
  { label: 'Settings', icon: <IconGear /> },
];

function NavList({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav className="flex flex-col gap-0.5">
      {NAV.map((item) => (
        <button
          key={item.label}
          onClick={onNavigate}
          aria-current={item.active ? 'page' : undefined}
          className={`group flex items-center gap-2.5 rounded-lg px-2.5 py-[0.4375rem] text-[0.8125rem] font-medium transition-colors ${
            item.active
              ? 'bg-elevated text-ink shadow-[inset_0_1px_0_0_rgba(255,255,255,0.04)]'
              : 'text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.025]'
          }`}
        >
          <span className={item.active ? 'text-accent-bright' : 'text-zinc-600 group-hover:text-zinc-400'}>
            {item.icon}
          </span>
          {item.label}
        </button>
      ))}
    </nav>
  );
}

function McpChip() {
  return (
    <div className="flex items-center gap-2.5 rounded-lg border border-hairline bg-panel px-2.5 py-2">
      <span className="relative flex h-1.5 w-1.5">
        <span className="absolute inline-flex h-full w-full rounded-full bg-ok/70 animate-livePulse" />
        <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-ok" />
      </span>
      <div className="min-w-0 leading-tight">
        <div className="text-[0.6875rem] text-zinc-300 font-medium truncate">MCP · Arize Phoenix</div>
        <div className="text-[0.625rem] text-zinc-600 font-mono">connected</div>
      </div>
    </div>
  );
}

export function Sidebar() {
  return (
    <aside className="hidden lg:flex fixed inset-y-0 left-0 w-[220px] flex-col border-r border-hairline bg-[#0A0A0D] z-30">
      <div className="flex items-center gap-2.5 px-4 h-14 border-b border-hairline">
        <ShieldMark />
        <span className="text-ink font-semibold text-[0.9375rem] tracking-tight">Eval Sentinel</span>
      </div>
      <div className="flex-1 px-3 py-4 overflow-y-auto">
        <div className="label px-2.5 mb-2 text-[#52525B]">Workspace</div>
        <NavList />
      </div>
      <div className="px-3 pb-4">
        <McpChip />
      </div>
    </aside>
  );
}

export function MobileTopBar() {
  const [open, setOpen] = useState(false);
  return (
    <div className="lg:hidden sticky top-0 z-30 border-b border-hairline bg-bg/85 backdrop-blur-md">
      <div className="flex items-center justify-between px-4 h-14">
        <div className="flex items-center gap-2.5">
          <ShieldMark size={22} />
          <span className="text-ink font-semibold text-[0.9375rem] tracking-tight">Eval Sentinel</span>
        </div>
        <button
          onClick={() => setOpen((v) => !v)}
          aria-label="Toggle navigation"
          className="grid h-9 w-9 place-items-center rounded-lg border border-hairline bg-elevated text-zinc-400 active:bg-[#1d1d23]"
        >
          {open ? <IconX /> : <IconMenu />}
        </button>
      </div>
      {open && (
        <div className="px-3 pb-3 pt-1 border-t border-hairline animate-nodeIn">
          <NavList onNavigate={() => setOpen(false)} />
          <div className="mt-3">
            <McpChip />
          </div>
        </div>
      )}
    </div>
  );
}

/* ---- icons ---- */
function IconGrid() {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
      <rect x="2" y="2" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.3" />
      <rect x="9" y="2" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.3" />
      <rect x="2" y="9" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.3" />
      <rect x="9" y="9" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.3" />
    </svg>
  );
}
function IconRuns() {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
      <path d="M2 12V9M6 12V5M10 12V7M14 12V3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}
function IconStack() {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
      <path d="M8 2L14 5L8 8L2 5L8 2Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
      <path d="M2 8L8 11L14 8M2 11L8 14L14 11" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
    </svg>
  );
}
function IconPrompt() {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
      <rect x="2.5" y="3" width="11" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.3" />
      <path d="M5 6.5L6.5 8L5 9.5M8.5 9.5H11" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
function IconGear() {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
      <circle cx="8" cy="8" r="2" stroke="currentColor" strokeWidth="1.3" />
      <path d="M8 1.5V3M8 13V14.5M14.5 8H13M3 8H1.5M12.6 3.4L11.5 4.5M4.5 11.5L3.4 12.6M12.6 12.6L11.5 11.5M4.5 4.5L3.4 3.4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}
function IconMenu() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <path d="M3 5H15M3 9H15M3 13H15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}
function IconX() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <path d="M5 5L13 13M13 5L5 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}
