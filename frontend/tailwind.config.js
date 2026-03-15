/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: '#0f1117',
        surface: '#1a1d27',
        'surface-hover': '#22252f',
        border: '#2a2d3a',
        'border-strong': '#3a3d4a',
        'text-primary': '#e4e4e7',
        'text-secondary': '#a1a1aa',
        'text-tertiary': '#71717a',
        accent: '#3b82f6',
        'accent-hover': '#2563eb',
        success: '#22c55e',
        warning: '#eab308',
        error: '#ef4444',
        info: '#6366f1',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        sm: '12px',
        base: '14px',
        lg: '16px',
        xl: '24px',
        '2xl': '32px',
      },
    },
  },
  plugins: [],
};
