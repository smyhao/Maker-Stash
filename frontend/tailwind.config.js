/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,ts}'],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          'Inter',
          'ui-sans-serif',
          'system-ui',
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          '"Microsoft YaHei"',
          'sans-serif',
        ],
      },
      colors: {
        ink: '#121721',
        muted: '#667085',
        line: '#dfe4ec',
        panel: '#ffffff',
        wash: '#f7f9fc',
        blue: '#1677ff',
        teal: '#1f9d70',
        amber: '#f08a00',
      },
      boxShadow: {
        soft: '0 10px 30px rgba(18, 23, 33, 0.07)',
      },
    },
  },
  plugins: [],
}
