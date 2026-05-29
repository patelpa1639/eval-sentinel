// Minimal, safe markdown -> React. Supports the subset the agent emits:
// headings (###), bold (**x**), inline code (`x`), and paragraphs/line breaks.
// No raw HTML is ever injected — everything is built from React nodes.

import { Fragment, type ReactNode } from 'react';

function renderInline(text: string, keyBase: string): ReactNode[] {
  // Split on **bold** and `code`, preserving delimiters.
  const tokens = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return tokens
    .filter((t) => t.length > 0)
    .map((tok, i) => {
      const key = `${keyBase}-${i}`;
      if (tok.startsWith('**') && tok.endsWith('**')) {
        return (
          <strong key={key} className="font-semibold text-zinc-100">
            {tok.slice(2, -2)}
          </strong>
        );
      }
      if (tok.startsWith('`') && tok.endsWith('`')) {
        return (
          <code
            key={key}
            className="font-mono text-[0.85em] text-accent bg-elevated px-1 py-0.5 rounded"
          >
            {tok.slice(1, -1)}
          </code>
        );
      }
      return <Fragment key={key}>{tok}</Fragment>;
    });
}

export function Markdown({ text }: { text: string }) {
  const lines = text.trim().split('\n');
  const blocks: ReactNode[] = [];

  lines.forEach((line, idx) => {
    const trimmed = line.trim();
    if (trimmed.length === 0) return;
    if (trimmed.startsWith('### ')) {
      blocks.push(
        <h4
          key={idx}
          className="text-zinc-200 font-semibold text-sm mb-1.5 mt-1 first:mt-0"
        >
          {renderInline(trimmed.slice(4), `h-${idx}`)}
        </h4>,
      );
    } else {
      blocks.push(
        <p key={idx} className="text-zinc-400 text-sm leading-relaxed mb-1.5 last:mb-0">
          {renderInline(trimmed, `p-${idx}`)}
        </p>,
      );
    }
  });

  return <div>{blocks}</div>;
}
