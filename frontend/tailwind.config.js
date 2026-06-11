/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          900: "#0a0c11",
          800: "#0e1117",
          700: "#141821",
          600: "#1b2030",
          500: "#252b3b",
        },
        line: "#222838",
        amber: {
          DEFAULT: "#ffb454",
          soft: "#ffd9a0",
          deep: "#d98a26",
        },
        teal: "#4fd1c5",
        good: "#34d399",
        warn: "#fbbf24",
        bad: "#fb7185",
        info: "#60a5fa",
      },
      fontFamily: {
        display: ["'Space Grotesk'", "system-ui", "sans-serif"],
        sans: ["'Inter'", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(255,180,84,0.25), 0 8px 40px -12px rgba(255,180,84,0.25)",
        panel: "0 1px 0 0 rgba(255,255,255,0.03) inset, 0 20px 50px -24px rgba(0,0,0,0.8)",
      },
      keyframes: {
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "pulse-ring": {
          "0%": { boxShadow: "0 0 0 0 rgba(255,180,84,0.4)" },
          "100%": { boxShadow: "0 0 0 8px rgba(255,180,84,0)" },
        },
      },
      animation: {
        shimmer: "shimmer 1.6s infinite",
        "fade-up": "fade-up 0.3s ease-out",
        "pulse-ring": "pulse-ring 1.4s ease-out infinite",
      },
    },
  },
  plugins: [],
};
