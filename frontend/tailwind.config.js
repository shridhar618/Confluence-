/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Syne', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
        display: ['Syne', 'sans-serif'],
      },
      colors: {
        bg: {
          900: '#080c14',
          800: '#0d1220',
          700: '#111827',
          600: '#1a2235',
        },
        accent: {
          DEFAULT: '#00e5ff',
          dim: '#00b8cc',
          glow: 'rgba(0,229,255,0.15)',
        },
        danger: '#ff4d6d',
        warn: '#ffb703',
        success: '#06d6a0',
        purple: '#a78bfa',
      },
      boxShadow: {
        glow: '0 0 20px rgba(0,229,255,0.2)',
        'glow-lg': '0 0 40px rgba(0,229,255,0.3)',
        card: '0 4px 24px rgba(0,0,0,0.4)',
      },
      animation: {
        'pulse-slow': 'pulse 3s ease-in-out infinite',
        'fade-in': 'fadeIn 0.4s ease forwards',
        'slide-up': 'slideUp 0.4s ease forwards',
        'slide-in': 'slideIn 0.3s ease forwards',
        typing: 'typing 1.2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: { from: { opacity: 0 }, to: { opacity: 1 } },
        slideUp: { from: { opacity: 0, transform: 'translateY(16px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        slideIn: { from: { opacity: 0, transform: 'translateX(-16px)' }, to: { opacity: 1, transform: 'translateX(0)' } },
        typing: {
          '0%, 100%': { opacity: 0.2 },
          '50%': { opacity: 1 },
        },
      },
    },
  },
  plugins: [],
}
