import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        cream: {
          50: '#fdfaf7',
          100: '#fdf7f0',
          200: '#f9e9d9',
          300: '#f5d9c2',
          400: '#f0c6a8',
          500: '#e8b390',
        },
        rose: {
          50: '#fff4f6',
          100: '#ffe4e9',
          200: '#fccdd7',
          300: '#f8a5b9',
          400: '#f78fb3',
          500: '#f06292',
        },
        sage: {
          50: '#f7f9f7',
          100: '#e8f0e8',
          200: '#cfe0cf',
          300: '#a8c8a8',
          400: '#7fb07f',
          500: '#5a945a',
        },
      },
      fontFamily: {
        display: ['Georgia', 'Cambria', 'Times New Roman', 'serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
      boxShadow: {
        'soft': '0 4px 20px rgba(0, 0, 0, 0.06)',
        'soft-lg': '0 8px 30px rgba(0, 0, 0, 0.08)',
      },
    },
  },
  plugins: [],
};

export default config;
