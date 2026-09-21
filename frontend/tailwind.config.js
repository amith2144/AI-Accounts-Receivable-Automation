/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class'],
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        background: '#090a0f',
        foreground: '#f8fafc',
        surface: {
          DEFAULT: '#12131a',
          elevated: '#1a1b24',
          highlight: '#222330',
        },
        border: {
          DEFAULT: '#232634',
          subtle: '#1d1f2b',
          hover: '#2f3346',
        },
        primary: {
          DEFAULT: '#3b82f6',
          hover: '#2563eb',
          active: '#1d4ed8',
          foreground: '#ffffff',
          glow: 'rgba(59, 130, 246, 0.18)',
        },
        secondary: {
          DEFAULT: '#1e2130',
          hover: '#292d42',
          foreground: '#f1f5f9',
        },
        accent: {
          emerald: '#10b981',
          amber: '#f59e0b',
          coral: '#ef4444',
          violet: '#8b5cf6',
          cyan: '#06b6d4',
        },
        muted: {
          DEFAULT: '#151722',
          foreground: '#94a3b8',
        },
        card: {
          DEFAULT: '#12131a',
          foreground: '#f8fafc',
        },
      },
      borderRadius: {
        DEFAULT: '0.375rem',
        sm: '0.25rem',
        md: '0.375rem',
        lg: '0.5rem',
        xl: '0.75rem',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'Monaco', 'Courier New', 'monospace'],
      },
      boxShadow: {
        'subtle-glow': '0 0 20px -5px rgba(59, 130, 246, 0.15)',
        'emerald-glow': '0 0 20px -5px rgba(16, 185, 129, 0.15)',
        'coral-glow': '0 0 20px -5px rgba(239, 68, 68, 0.15)',
      },
    },
  },
  plugins: [],
};
