/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class', // We will force dark mode or let it be class based
  theme: {
    extend: {
      colors: {
        background: {
          light: '#FAFAF8',
          dark: '#05050A',
        },
        surface: {
          light: '#FFFFFF',
          dark: '#1A1D23',
        },
        primary: {
          light: '#1A1A1A',
          dark: '#F3F4F6',
          brand: '#6D5EF0',
        },
        secondary: {
          light: '#6B7280',
          dark: '#9CA3AF',
        },
        border: {
          light: '#E5E7EB',
          dark: '#2A2E37',
        },
        status: {
          security: '#EF4444',
          structure: '#F59E0B',
          style: '#3B82F6',
          verified: '#22C55E',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
        display: ['"Space Grotesk"', 'sans-serif'],
        meta: ['"IBM Plex Mono"', 'monospace'],
      },
      boxShadow: {
        'vscode': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06), 0 0 0 1px rgba(255, 255, 255, 0.05)',
      }
    },
  },
  plugins: [],
}
