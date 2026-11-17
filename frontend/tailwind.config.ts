import type { Config } from "tailwindcss";

export default {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-plus-jakarta)", "sans-serif"],
      },
      colors: {
        brand: {
          50: "#F0FDF9",
          100: "#CCFBEF",
          500: "#14B8A6",
          700: "#0F766E",
          800: "#0D7A5F",
          900: "#095341",
        },
      },
      keyframes: {
        "pulse-subtle": {
          "0%, 100%": { opacity: "0.3", transform: "scale(0.85)" },
          "50%": { opacity: "1", transform: "scale(1)" },
        },
      },
      animation: {
        "dot-1": "pulse-subtle 1.2s infinite ease-in-out",
        "dot-2": "pulse-subtle 1.2s infinite ease-in-out 0.2s",
        "dot-3": "pulse-subtle 1.2s infinite ease-in-out 0.4s",
      },
    },
  },
  plugins: [],
} satisfies Config;
