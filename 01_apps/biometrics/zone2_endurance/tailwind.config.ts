import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        // Endurance Biometric Zones (High-Contrast Palettes)
        zone1: {
          DEFAULT: "#0284c7", // Sky 600 (Recovery)
          light: "#38bdf8",   // Sky 400
          dark: "#0369a1",    // Sky 700
          subtle: "rgba(2, 132, 199, 0.12)",
          text: "#0369a1",
        },
        zone2: {
          DEFAULT: "#059669", // Emerald 600 (Aerobic Base - Target)
          light: "#34d399",   // Emerald 400
          dark: "#047857",    // Emerald 700
          subtle: "rgba(5, 150, 105, 0.12)",
          accent: "#10b981",  // Emerald 500
          text: "#047857",
        },
        zone3: {
          DEFAULT: "#d97706", // Amber 600 (Tempo / Aerobic Power)
          light: "#fbbf24",   // Amber 400
          dark: "#b45309",    // Amber 700
          subtle: "rgba(217, 119, 6, 0.12)",
          text: "#b45309",
        },
        zone4: {
          DEFAULT: "#ea580c", // Orange 600 (Threshold)
          light: "#fb923c",   // Orange 400
          dark: "#c2410c",    // Orange 700
          subtle: "rgba(234, 88, 12, 0.12)",
          text: "#c2410c",
        },
        zone5: {
          DEFAULT: "#e11d48", // Rose 600 (Anaerobic / VO2Max)
          light: "#fb7185",   // Rose 400
          dark: "#be123c",    // Rose 700
          subtle: "rgba(225, 29, 72, 0.12)",
          text: "#be123c",
        },
        // Specialized Telemetry & ECG Tokens
        ecg: {
          line: "#10b981",    // Oscilloscope phosphor emerald
          leadOff: "#f43f5e", // Rose alarm
          noisy: "#f59e0b",   // Amber warning
          gridMajor: "var(--ecg-grid-major)",
          gridMinor: "var(--ecg-grid-minor)",
          background: "var(--ecg-bg)",
        },
        dfa: {
          corridor: "rgba(5, 150, 105, 0.18)", // 0.75 - 1.00 Zone 2 Corridor
          lt1: "#059669",                      // 0.75 Aerobic Threshold
          lt2: "#e11d48",                      // 0.50 Anaerobic Threshold
          recovery: "#0284c7",                 // > 1.00 Recovery
          point: "#10b981",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "ecg-sweep": "ecgSweep 2.5s linear infinite",
      },
      keyframes: {
        ecgSweep: {
          "0%": { transform: "translateX(0%)" },
          "100%": { transform: "translateX(100%)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
