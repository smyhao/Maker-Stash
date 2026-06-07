/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,ts}', '../extensions/*/src/**/*.{vue,ts}'],
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
        ink: '#252921',
        muted: '#747669',
        line: '#e5e0d5',
        panel: '#fffefa',
        nav: '#f3efe5',
        wash: '#faf7f0',
        wood: '#d8c3a5',
        green: '#567a61',
        clay: '#b96846',
        blue: '#567a61',
        teal: '#567a61',
        amber: '#b96846',
      },
      boxShadow: {
        soft: '0 12px 32px rgba(51, 43, 30, 0.08)',
      },
    },
  },
  plugins: [],
}
