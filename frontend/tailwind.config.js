/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  "#EEF4FB",
          100: "#D5E3F5",
          200: "#A8C6EA",
          300: "#6FA0D9",
          400: "#3D7CC4",
          500: "#1B5FAA",
          600: "#1B3A5C",
          700: "#162F4A",
          800: "#112439",
          900: "#0C1928",
        },
        accent: {
          400: "#F59E0B",
          500: "#D97706",
          600: "#B45309",
        },
      },
    },
  },
  plugins: [],
};
