/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          bg: '#0c0a15',
          text: '#E2E8F0',
        },
        accent: {
          gold: '#FFD700',
        },
        status: {
          alert: '#EF4444',
          info: '#3B82F6',
          success: '#22C55E',
        },
      },
      fontFamily: {
        pixel: ['"Press Start 2P"', 'cursive'],
        mono: ['"VT323"', 'monospace'],
      },
      backdropBlur: {
        xs: '2px',
      },
      animation: {
        'float': 'float 20s ease-in-out infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translate(0px, 0px)' },
          '33%': { transform: 'translate(30px, -30px)' },
          '66%': { transform: 'translate(-20px, 20px)' },
        },
        glow: {
          '0%': { boxShadow: '0 0 5px #FFD700, 0 0 10px #FFD700, 0 0 15px #FFD700' },
          '100%': { boxShadow: '0 0 10px #FFD700, 0 0 20px #FFD700, 0 0 30px #FFD700' },
        },
      },
    },
  },
  plugins: [],
}