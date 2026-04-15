/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  "#F4F5F6",
          100: "#E2E4E7",
          200: "#C5C9CF",
          300: "#9BA1AB",
          400: "#6B7280",
          500: "#4A4F57",
          600: "#3D3D3D",
          700: "#2D2D2D",
          800: "#1E1E1E",
          900: "#111111",
        },
        accent: {
          50:  "#FEF2F2",
          100: "#FDE3E3",
          200: "#FCBCBC",
          300: "#F98888",
          400: "#E63329",
          500: "#CC2D24",
          600: "#A8241D",
        },
      },
    },
  },
  plugins: [],
};
