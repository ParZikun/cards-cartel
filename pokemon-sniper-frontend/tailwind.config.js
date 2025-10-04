/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#000000',
          50: '#1a1a1a',
          100: '#333333',
          200: '#4d4d4d',
          300: '#666666',
          400: '#808080',
          500: '#999999',
          600: '#b3b3b3',
          700: '#cccccc',
          800: '#e6e6e6',
          900: '#ffffff',
        },
        secondary: {
          DEFAULT: '#ffffff',
          50: '#f2f2f2',
          100: '#e6e6e6',
          200: '#cccccc',
          300: '#b3b3b3',
          400: '#999999',
          500: '#808080',
          600: '#666666',
          700: '#4d4d4d',
          800: '#333333',
          900: '#1a1a1a',
        },
        accent: {
          DEFAULT: '#FFD700',
          50: '#fff9e6',
          100: '#fff2cc',
          200: '#ffe699',
          300: '#ffd966',
          400: '#ffcc33',
          500: '#FFD700',
          600: '#e6c200',
          700: '#ccad00',
          800: '#b39900',
          900: '#998500',
        },
        pokemon: {
          red: '#FF6B6B',
          blue: '#4ECDC4',
          orange: '#FF8E53',
          green: '#45B7D1',
        }
      },
      fontFamily: {
        'pokemon': ['Pokemon', 'monospace'],
        'gameboy': ['GameBoy', 'monospace'],
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gold-gradient': 'linear-gradient(45deg, #FFD700, #FFA500, #FFD700)',
        'dark-gradient': 'radial-gradient(circle at center, rgba(255,255,255,0.1) 0%, rgba(0,0,0,0.8) 100%)',
      },
      animation: {
        'gold-shimmer': 'shimmer 2s ease-in-out infinite',
        'float': 'float 3s ease-in-out infinite',
      },
      keyframes: {
        shimmer: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
      },
    },
  },
  plugins: [],
}