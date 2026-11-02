/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: '#0c3574',
        blue: '#1267d6',
        sky: '#edf5ff',
        ink: '#18324f',
        muted: '#587895',
        line: '#d7e5f5',
      },
    },
  },
  plugins: [],
}
