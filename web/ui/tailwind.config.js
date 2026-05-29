/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Near-black ops-console surface scale
        bg: '#0a0a0b',
        panel: '#0e0e10',
        elevated: '#141417',
        // Single restrained accent (cool slate-cyan, not neon)
        accent: '#5e9eff',
        // Semantic
        ok: '#3fb950',
        regress: '#f85149',
        progress: '#d29922',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem' }],
      },
      keyframes: {
        nodeIn: {
          '0%': { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.45' },
        },
      },
      animation: {
        nodeIn: 'nodeIn 0.28s cubic-bezier(0.16, 1, 0.3, 1)',
        pulseSoft: 'pulseSoft 1.4s ease-in-out infinite',
      },
    },
  },
  plugins: [],
};
