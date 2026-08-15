/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef4ff",
          100: "#dbe6fe",
          200: "#bcd0fe",
          300: "#8fb0fc",
          400: "#5b87f8",
          500: "#3760ef",
          600: "#2542e0",
          700: "#2034c0",
          800: "#212f9b",
          900: "#1f2b7a",
        },
      },
    },
  },
  plugins: [],
};
