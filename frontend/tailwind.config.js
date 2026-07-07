/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: 'var(--color-bg)',
        surface: 'var(--color-surface)',
        ink: 'var(--color-ink)',
        primary: {
          DEFAULT: 'var(--color-primary)',
          hover: '#2F298F', // slightly darker for hover states if needed
        },
        accent: 'var(--color-accent)',
        risk: 'var(--color-risk)',
        growth: 'var(--color-growth)',
        border: 'var(--color-border)',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        display: ['Space Grotesk', 'sans-serif'],
        mono: ['IBM Plex Mono', 'monospace'],
      },
      boxShadow: {
        'card': '0 4px 6px -1px rgba(21, 24, 51, 0.05), 0 2px 4px -1px rgba(21, 24, 51, 0.03)',
        'card-hover': '0 10px 15px -3px rgba(21, 24, 51, 0.08), 0 4px 6px -2px rgba(21, 24, 51, 0.04)',
      }
    },
  },
  plugins: [],
}
