import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        accent: {
          DEFAULT: "#635bff",
          hover: "#5248db",
        },
        sidebar: "#f6f9fc",
        status: {
          pending: { bg: "#f3f4f6", text: "#4b5563" },
          processing: { bg: "#dbeafe", text: "#1d4ed8" },
          done: { bg: "#dcfce7", text: "#15803d" },
          failed: { bg: "#fee2e2", text: "#b91c1c" },
          to_confirm: { bg: "#ffedd5", text: "#c2410c" },
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
