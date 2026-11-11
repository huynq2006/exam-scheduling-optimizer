import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          50: "#F7F8FA",
          100: "#EDEFF3",
          200: "#DDE1E8",
          300: "#C3C9D4",
          400: "#8D97A8",
          500: "#667085",
          600: "#4B5566",
          700: "#39414F",
          800: "#262C37",
          900: "#171B22",
        },
        accent: {
          50: "#EEF2FB",
          100: "#DCE4F7",
          200: "#BCCBEE",
          300: "#93A9DF",
          400: "#6A84CB",
          500: "#4A66B4",
          600: "#3A5296",
          700: "#2F4278",
          800: "#28375F",
          900: "#1F2A47",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(23, 27, 34, 0.04)",
        pop: "0 8px 24px -12px rgba(23, 27, 34, 0.18)",
      },
      borderRadius: {
        xl: "0.75rem",
      },
    },
  },
  plugins: [],
};

export default config;
