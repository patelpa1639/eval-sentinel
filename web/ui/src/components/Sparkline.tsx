// Faint inline sparkline for KPI tiles. Hand-rolled SVG with a subtle gradient
// area fill (Stripe-style). Normalizes to its own min/max so flat-ish series
// still read as a line.

interface Props {
  data: number[];
  tone?: 'accent' | 'ok' | 'regress';
  width?: number;
  height?: number;
}

const STROKE: Record<NonNullable<Props['tone']>, string> = {
  accent: '#818CF8',
  ok: '#34D399',
  regress: '#FB7185',
};

export function Sparkline({ data, tone = 'accent', width = 96, height = 30 }: Props) {
  if (data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const span = max - min || 1;
  const pad = 1.5;
  const w = width;
  const h = height;
  const stepX = (w - pad * 2) / (data.length - 1);

  const pts = data.map((v, i) => {
    const x = pad + i * stepX;
    const y = pad + (1 - (v - min) / span) * (h - pad * 2);
    return [x, y] as const;
  });

  const line = pts.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(1)} ${y.toFixed(1)}`).join(' ');
  const area = `${line} L${pts[pts.length - 1][0].toFixed(1)} ${h} L${pts[0][0].toFixed(1)} ${h} Z`;
  const id = `spk-${tone}-${data.length}-${Math.round(data[0])}`;
  const stroke = STROKE[tone];

  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} fill="none" aria-hidden className="overflow-visible">
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={stroke} stopOpacity="0.18" />
          <stop offset="100%" stopColor={stroke} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${id})`} />
      <path
        d={line}
        stroke={stroke}
        strokeWidth="1.3"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.85"
      />
      <circle cx={pts[pts.length - 1][0]} cy={pts[pts.length - 1][1]} r="1.6" fill={stroke} />
    </svg>
  );
}
