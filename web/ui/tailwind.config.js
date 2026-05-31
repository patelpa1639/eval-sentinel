/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      screens: {
        xs: '400px',
      },
      colors: {
        // Layered dark surface scale — not flat black.
        bg: '#08080A',
        panel: '#0E0E12',
        elevated: '#16161B',
        hairline: '#1C1C22',
        // Text
        ink: '#FAFAFA',
        // Single refined indigo accent — interactive / live.
        accent: '#6366F1',
        'accent-bright': '#818CF8',
        // Semantic, muted.
        ok: '#34D399',
        'ok-deep': '#10B981',
        regress: '#FB7185',
        'regress-deep': '#F43F5E',
        progress: '#F59E0B',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem' }],
      },
      letterSpacing: {
        label: '0.08em',
      },
      keyframes: {
        nodeIn: {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.4' },
        },
        livePulse: {
          '0%': { transform: 'scale(1)', opacity: '0.55' },
          '70%, 100%': { transform: 'scale(2.4)', opacity: '0' },
        },
        spinSlow: {
          to: { transform: 'rotate(360deg)' },
        },
      },
      animation: {
        nodeIn: 'nodeIn 0.34s cubic-bezier(0.16, 1, 0.3, 1) both',
        pulseSoft: 'pulseSoft 1.6s ease-in-out infinite',
        livePulse: 'livePulse 2s cubic-bezier(0.16, 1, 0.3, 1) infinite',
        spinSlow: 'spinSlow 0.7s linear infinite',
      },
    },
  },
  plugins: [],
};
