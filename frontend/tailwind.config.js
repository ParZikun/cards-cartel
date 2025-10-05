/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,jsx}',
    './components/**/*.{js,jsx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          bg: '#0c0a15',
          gold: '#FFD700',
        },
        accent: {
          red: '#EF4444',
          blue: '#3B82F6',
          green: '#22C55E',
        },
      },
      fontFamily: {
        pixel: ['"Press Start 2P"', 'cursive'],
        retro: ['"VT323"', 'monospace'],
      },
      animation: {
        'pan': 'pan 60s linear infinite',
      },
      keyframes: {
        pan: {
          '0%': { transform: 'translate(0, 0)' },
          '100%': { transform: 'translate(-50%, -50%)' },
        },
      },
    },
  },
  plugins: [],
};