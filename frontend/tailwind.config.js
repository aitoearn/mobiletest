/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: {
          primary: '#0D1117',
          secondary: '#161B22',
          tertiary: '#21262D',
        },
        accent: {
          primary: '#00FFD1',
          secondary: '#7B61FF',
          success: '#3FB950',
          error: '#F85149',
          warning: '#D29922',
        },
        text: {
          primary: '#F0F6FC',
          secondary: '#8B949E',
        }
      },
      fontFamily: {
        display: ['JetBrains Mono', 'monospace'],
        body: ['Inter Variable', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
