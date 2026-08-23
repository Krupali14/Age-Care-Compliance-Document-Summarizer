/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: "#14213D",
          800: "#1C2C4C",
          700: "#26375E",
        },
        parchment: {
          DEFAULT: "#F7F4EC",
          100: "#FFFEFA",
          200: "#EFEADB",
        },
        slate: {
          500: "#5B6472",
          400: "#7B8493",
        },
        teal: {
          DEFAULT: "#0E7C7B",
          600: "#0B6564",
          50: "#E6F3F2",
        },
        amber: {
          DEFAULT: "#D97706",
          50: "#FDF3E4",
        },
        coral: {
          DEFAULT: "#DC4C3E",
          50: "#FBEAE8",
        },
        sage: {
          DEFAULT: "#3F7D58",
          50: "#E9F3EC",
        },
        // kept for any un-migrated brand-* references
        brand: {
          50: "#E6F3F2",
          100: "#CCE7E5",
          600: "#0E7C7B",
          700: "#0B6564",
        },
      },
      fontFamily: {
        display: ['"Fraunces"', "serif"],
        sans: ['"Inter"', "system-ui", "sans-serif"],
        mono: ['"IBM Plex Mono"', "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(20,33,61,0.06), 0 8px 24px -8px rgba(20,33,61,0.12)",
        "card-hover": "0 4px 8px rgba(20,33,61,0.08), 0 16px 40px -12px rgba(20,33,61,0.18)",
        stack: "0 20px 60px -20px rgba(20,33,61,0.35)",
      },
      keyframes: {
        scan: {
          "0%": { transform: "translateY(-10%)", opacity: "0" },
          "10%": { opacity: "1" },
          "90%": { opacity: "1" },
          "100%": { transform: "translateY(110%)", opacity: "0" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        scan: "scan 2.8s ease-in-out infinite",
        shimmer: "shimmer 2s linear infinite",
        "fade-up": "fade-up 0.5s ease-out both",
      },
    },
  },
  plugins: [],
};
