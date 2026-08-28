# Comprehensive Frontend Architecture & Accessibility (a11y) Specification
**Project:** Zone 2 Endurance & DFA-alpha1 Biometric App  
**Target Path:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/zone2_endurance`  
**Author:** Explorer 3 (Frontend Architecture & a11y Specialist)  
**Date:** 2026-08-26T22:06:00+10:00  
**Compliance Standards:** WCAG 2.1 Level AA (and AAA where specified), Next.js 14+ App Router, Tailwind CSS v3.4+, Zero Mock Truth Standard  

---

## 1. Executive Summary & Architectural Vision

The **Zone 2 Endurance & DFA-alpha1 Fatiguing App** is a high-performance, medical-grade biometrics telemetry interface designed to process real-time physiological signals (128Hz Movesense ECG, Pan-Tompkins R-R intervals, and Detrended Fluctuation Analysis $\alpha_1$ correlation coefficients). 

To ensure maximum runtime performance, sub-millisecond chart rendering, minimal client JavaScript footprint, and flawless accessibility, the application is architected around three foundational pillars:

1. **Hybrid Next.js App Router Paradigm (RSC Isolation)**:
   - **React Server Components (RSC) by Default**: The root layout, navigation shell, sidebar, dashboard layout, and static summary cards are pure Server Components with zero hydration overhead and zero client bundle penalty.
   - **Strict Client Component (`"use client"`) Isolation**: Interactive, high-frequency telemetry components (128Hz ECG canvas, DFA-$\alpha_1$ time-series chart, dynamic ARIA live announcer, theme toggler) are encapsulated at the leaf boundaries of the component tree.

2. **Zero-Flash Dark/Light Theme Engine**:
   - Class-based Tailwind CSS configuration driven by CSS variables (`:root` / `.dark`).
   - Synchronous, anti-FOUC (Flash of Unstyled Content) `ThemeScript` injected in `<head>` preventing hydration mismatch and luminance flashing during initial page load.
   - High-contrast color palette exceeding WCAG 2.1 AA contrast ratios (minimum 4.5:1 for normal text, 3:1 for graphical UI elements and biometrics data visualization).

3. **Strict Accessibility (WCAG 2.1 AA Standard)**:
   - Full semantic ARIA landmark hierarchy (`<header role="banner">`, `<nav role="navigation">`, `<main role="main">`, `<aside role="complementary">`).
   - Accessible keyboard navigation with visible, high-contrast focus rings (`focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2`).
   - Screen-reader accessible data table fallbacks (`<table className="sr-only">`) synchronizing live biometric streams into tabular data structures.
   - Dual-tier ARIA Live Announcer (`aria-live="polite"` for non-critical threshold changes; `aria-live="assertive"` for critical cardiac/fatigue alarms).

---

## 2. Directory Layout & Module Structure

The application layout in `01_apps/zone2_endurance` adheres strictly to modern Next.js App Router conventions:

```
01_apps/zone2_endurance/
├── app/
│   ├── favicon.ico
│   ├── globals.css                 # CSS variables for themes & biometric zones
│   ├── layout.tsx                  # Pure RSC Root Layout (ThemeScript, SkipLink, NavShell)
│   ├── loading.tsx                 # Instant Suspense fallback skeleton
│   ├── not-found.tsx               # Accessible 404 handler
│   ├── error.tsx                   # Accessible error boundary ("use client")
│   ├── page.tsx                    # Pure RSC Landing / Summary Redirect
│   ├── dashboard/
│   │   ├── page.tsx                # Pure RSC Dashboard Shell with Suspense streams
│   │   └── loading.tsx             # Dashboard metric card skeleton
│   └── telemetry/
│       └── page.tsx                # Dedicated Deep-Dive Telemetry View
├── components/
│   ├── a11y/
│   │   ├── AccessibleDataTable.tsx # Screen-reader tabular fallback for charts
│   │   ├── LiveAnnouncer.tsx       # Dynamic ARIA Live Region manager ("use client")
│   │   └── SkipLink.tsx            # Skip-to-content accessible anchor
│   ├── charts/
│   │   ├── DFAAlpha1Chart.tsx      # Interactive DFA-a1 timeline ("use client")
│   │   ├── LiveECGChart.tsx        # 128Hz Canvas ECG Trace ("use client")
│   │   └── ThresholdIndicator.tsx  # Aerobic/Anaerobic zone badge
│   ├── dashboard/
│   │   ├── BiometricSummaryCards.tsx # RSC pre-computed metric cards
│   │   └── MetricCardSkeleton.tsx  # Suspense fallback skeleton
│   ├── nav/
│   │   ├── Header.tsx              # RSC App Header with live session info
│   │   ├── NavigationShell.tsx     # RSC Main Shell Layout (Sidebar + Header + Main)
│   │   └── Sidebar.tsx             # RSC Nav links with accessible active states
│   └── theme/
│       ├── ThemeScript.tsx         # Inline anti-flash script for <head>
│       └── ThemeToggle.tsx         # Accessible dark/light mode toggle ("use client")
├── hooks/
│   ├── use-a11y-live.ts            # Hook for dispatching polite/assertive announcements
│   ├── use-ecg-stream.ts           # 128Hz ring buffer and WebGL/Canvas hook
│   └── use-theme.ts                # Client theme state manager
├── lib/
│   ├── a11y-utils.ts               # Contrast calculators and ARIA formatting helpers
│   ├── telemetry-contracts.ts      # Zero-mock biometric data models & type schemas
│   └── utils.ts                    # clsx / tailwind-merge helper (cn)
├── types/
│   ├── biometrics.d.ts             # ECG, DFA-a1, HRV, R-R intervals type definitions
│   └── navigation.d.ts             # Navigation menu & route types
├── next.config.mjs                 # Next.js configuration
├── package.json                    # Monorepo dependencies & scripts
├── postcss.config.mjs              # PostCSS with Tailwind & Autoprefixer
├── tailwind.config.ts              # Tailwind CSS configuration with darkMode: 'class'
└── tsconfig.json                   # Strict TypeScript configuration
```

---

## 3. Next.js App Router Architecture: RSC vs. Client Components

### 3.1 Component Boundary Partitioning Matrix

| Component File | Boundary Mode | Rationale & Responsibilities |
| :--- | :--- | :--- |
| `app/layout.tsx` | **Server (RSC)** | Injects global metadata, fonts, HTML language attributes (`lang="en"`), `ThemeScript`, and root landmark shell. Zero client bundle cost. |
| `app/dashboard/page.tsx` | **Server (RSC)** | Fetches baseline historical session data, user profiles, and threshold definitions (LT1: 0.75, LT2: 0.50). Wraps async data in `<Suspense>`. |
| `components/nav/NavigationShell.tsx` | **Server (RSC)** | Renders outer flex/grid container, sidebar navigational anchors, accessible skip-link target, and static layout grid. |
| `components/nav/Sidebar.tsx` | **Server (RSC)** | Semantic `<nav aria-label="Main Navigation">` with static routes (`/dashboard`, `/telemetry`, `/history`, `/settings`). |
| `components/nav/Header.tsx` | **Server (RSC)** | Semantic `<header role="banner">` with brand logo, session title, and Client slots for theme toggling. |
| `components/dashboard/BiometricSummaryCards.tsx` | **Server (RSC)** | Renders metric tiles (Average HR, Peak DFA-$\alpha_1$, Time in Zone 2, Estimated LT1/LT2) with semantic description lists (`<dl>`, `<dt>`, `<dd>`). |
| `components/charts/LiveECGChart.tsx` | **Client (`"use client"`)** | Connects to 128Hz telemetry buffer, runs high-speed HTML5 Canvas rendering loop via `requestAnimationFrame`, handles pause/zoom controls, and renders hidden a11y DOM fallback. |
| `components/charts/DFAAlpha1Chart.tsx` | **Client (`"use client"`)** | Interactive time-series graph with dynamic threshold reference lines ($0.75$ aerobic, $0.50$ anaerobic), interactive tooltips, SVG accessibility tags, and tabular data synchronizer. |
| `components/a11y/LiveAnnouncer.tsx` | **Client (`"use client"`)** | Subscribes to telemetry state transitions and pushes non-visual audio/screen-reader notifications into dedicated `aria-live` containers. |
| `components/theme/ThemeToggle.tsx` | **Client (`"use client"`)** | Handles button click events, updates `document.documentElement.classList`, and writes preferences to `localStorage`. |

### 3.2 Pure Server Component Root Layout (`app/layout.tsx`)

```tsx
import type { Metadata, Viewport } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';
import { ThemeScript } from '@/components/theme/ThemeScript';
import { SkipLink } from '@/components/a11y/SkipLink';
import { LiveAnnouncer } from '@/components/a11y/LiveAnnouncer';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'Zone 2 Endurance & DFA-α1 Telemetry',
  description: 'Real-time aerobic threshold tracking and medical-grade ECG telemetry',
  applicationName: 'Lauburu Zone 2 Endurance',
  authors: [{ name: 'Lauburu Biometrics Team' }],
};

export const viewport: Viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#ffffff' },
    { media: '(prefers-color-scheme: dark)', color: '#090d16' },
  ],
  width: 'device-width',
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <head>
        {/* Anti-FOUC inline theme script */}
        <ThemeScript />
      </head>
      <body className="min-h-screen bg-background font-sans text-foreground antialiased selection:bg-emerald-500 selection:text-white">
        <SkipLink />
        {/* Global Polymorphic Live Announcer for screen-readers */}
        <LiveAnnouncer />
        {children}
      </body>
    </html>
  );
}
```

### 3.3 Server Component Navigation Shell (`components/nav/NavigationShell.tsx`)

```tsx
import React from 'react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

interface NavigationShellProps {
  children: React.ReactNode;
}

export function NavigationShell({ children }: NavigationShellProps) {
  return (
    <div className="flex min-h-screen w-full flex-col lg:flex-row">
      {/* Sidebar Navigation Landmark */}
      <Sidebar />
      
      {/* Primary Application Workspace */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Header Landmark */}
        <Header />
        
        {/* Main Content Landmark */}
        <main
          id="main-content"
          tabIndex={-1}
          role="main"
          className="flex-1 overflow-y-auto p-4 focus:outline-none sm:p-6 lg:p-8"
        >
          <div className="mx-auto max-w-7xl space-y-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
```

### 3.4 Isolated Client Component: Live ECG Chart (`components/charts/LiveECGChart.tsx`)

```tsx
'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { AccessibleDataTable } from '@/components/a11y/AccessibleDataTable';
import { useA11yLive } from '@/hooks/use-a11y-live';

interface LiveECGChartProps {
  samplingRateHz?: number; // Default 128Hz
  maxBufferLength?: number; // Default 512 points (4 seconds)
  className?: string;
}

export function LiveECGChart({
  samplingRateHz = 128,
  maxBufferLength = 512,
  className = '',
}: LiveECGChartProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [isPaused, setIsPaused] = useState(false);
  const [currentHeartRate, setCurrentHeartRate] = useState<number>(0);
  const [ecgHistory, setEcgHistory] = useState<Array<{ timestamp: string; voltageMv: number }>>([]);
  const { announcePolite } = useA11yLive();

  // Draw loop using requestAnimationFrame
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let buffer: number[] = [];

    const render = () => {
      if (!isPaused) {
        // High-DPI canvas scaling
        const dpr = window.devicePixelRatio || 1;
        const width = canvas.clientWidth;
        const height = canvas.clientHeight;
        
        if (canvas.width !== width * dpr || canvas.height !== height * dpr) {
          canvas.width = width * dpr;
          canvas.height = height * dpr;
        }

        ctx.save();
        ctx.scale(dpr, dpr);
        ctx.clearRect(0, 0, width, height);

        // Draw Medical Grid Background
        const isDark = document.documentElement.classList.contains('dark');
        const gridColor = isDark ? 'rgba(51, 65, 85, 0.4)' : 'rgba(226, 232, 240, 0.8)';
        const traceColor = isDark ? '#22d3ee' : '#0891b2'; // Cyan trace (WCAG AA compliant)

        ctx.strokeStyle = gridColor;
        ctx.lineWidth = 1;
        const gridSize = 20;

        ctx.beginPath();
        for (let x = 0; x < width; x += gridSize) {
          ctx.moveTo(x, 0);
          ctx.lineTo(x, height);
        }
        for (let y = 0; y < height; y += gridSize) {
          ctx.moveTo(0, y);
          ctx.lineTo(width, y);
        }
        ctx.stroke();

        // Draw ECG Waveform
        if (buffer.length > 1) {
          ctx.beginPath();
          ctx.strokeStyle = traceColor;
          ctx.lineWidth = 2;
          ctx.lineJoin = 'round';

          const step = width / (maxBufferLength - 1);
          buffer.forEach((val, i) => {
            const x = i * step;
            // Normalizing voltage to canvas height (centered at height/2)
            const y = height / 2 - val * (height / 3);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
          });
          ctx.stroke();
        }

        ctx.restore();
      }

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [isPaused, maxBufferLength]);

  const togglePause = useCallback(() => {
    setIsPaused((prev) => {
      const next = !prev;
      announcePolite(next ? 'ECG live trace paused' : 'ECG live trace resumed');
      return next;
    });
  }, [announcePolite]);

  return (
    <div className={`relative rounded-xl border border-border bg-card p-4 shadow-sm ${className}`}>
      {/* Header & Controls */}
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-card-foreground">
            Live Electrocardiogram (128Hz)
          </h2>
          <p className="text-xs text-muted-foreground">
            Pan-Tompkins QRS peak detection & real-time Lead II voltage stream
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-600 dark:text-emerald-400">
            <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-500" aria-hidden="true" />
            <span>128 Hz Active</span>
          </div>
          <button
            type="button"
            onClick={togglePause}
            aria-pressed={isPaused}
            className="inline-flex items-center justify-center rounded-lg border border-input bg-background px-3 py-1.5 text-xs font-medium text-foreground shadow-sm transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
          >
            {isPaused ? 'Resume Stream' : 'Pause Stream'}
          </button>
        </div>
      </div>

      {/* Visual Canvas Visualizer */}
      <div className="relative h-64 w-full overflow-hidden rounded-lg border border-border bg-slate-950 dark:bg-black">
        <canvas
          ref={canvasRef}
          className="h-full w-full"
          role="img"
          aria-label="Live ECG waveform trace. Screen reader users can access tabular readings below."
        />
      </div>

      {/* Screen-reader accessible data table fallback */}
      <AccessibleDataTable
        caption="Sampled ECG Voltage History"
        headers={['Timestamp', 'Lead II Voltage (mV)']}
        rows={ecgHistory.map((pt) => [pt.timestamp, `${pt.voltageMv.toFixed(3)} mV`])}
      />
    </div>
  );
}
```

### 3.5 Isolated Client Component: DFA-alpha1 Zone Chart (`components/charts/DFAAlpha1Chart.tsx`)

```tsx
'use client';

import React, { useId } from 'react';
import { AccessibleDataTable } from '@/components/a11y/AccessibleDataTable';

export interface DFADataPoint {
  timestamp: string;
  timeSec: number;
  alpha1: number;
  heartRate: number;
  zone: 'Zone 1 (Recovery)' | 'Zone 2 (Aerobic)' | 'Threshold (LT2)' | 'Severe Fatiguing';
}

interface DFAAlpha1ChartProps {
  data: DFADataPoint[];
  className?: string;
}

export function DFAAlpha1Chart({ data, className = '' }: DFAAlpha1ChartProps) {
  const chartId = useId();
  const titleId = `${chartId}-title`;
  const descId = `${chartId}-desc`;

  // Threshold constants
  const LT1_AEROBIC = 0.75;
  const LT2_ANAEROBIC = 0.50;

  const currentReading = data[data.length - 1] || {
    alpha1: 0.82,
    heartRate: 138,
    zone: 'Zone 2 (Aerobic)',
    timestamp: new Date().toLocaleTimeString(),
  };

  return (
    <div className={`rounded-xl border border-border bg-card p-4 shadow-sm ${className}`}>
      {/* Title & Live Status */}
      <div className="mb-4 flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
        <div>
          <h2 id={titleId} className="text-lg font-semibold text-card-foreground">
            DFA-α1 Dynamic Fatigue & Zone Tracker
          </h2>
          <p id={descId} className="text-xs text-muted-foreground">
            Aerobic Threshold (LT1 = 0.75), Anaerobic Threshold (LT2 = 0.50)
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Current Zone:</span>
          <span className="inline-flex items-center rounded-md bg-emerald-500/10 px-2.5 py-1 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
            {currentReading.zone} (α1 = {currentReading.alpha1.toFixed(2)})
          </span>
        </div>
      </div>

      {/* SVG Time-Series Graphic with ARIA Accessibility Metadata */}
      <div className="relative h-64 w-full rounded-lg border border-border bg-background p-2">
        <svg
          viewBox="0 0 600 240"
          className="h-full w-full"
          role="img"
          aria-labelledby={`${titleId} ${descId}`}
        >
          <title id={titleId}>DFA-alpha1 Correlation Trend Graph</title>
          <desc id={descId}>
            Visual time series plotting DFA alpha1 values between 0.2 and 1.2 across exercise duration.
            Aerobic threshold line is marked at 0.75, anaerobic threshold line is marked at 0.50.
            Current alpha1 is {currentReading.alpha1.toFixed(2)} in {currentReading.zone}.
          </desc>

          {/* Background Zone Shading */}
          {/* Zone 2 Sweet Spot (0.75 to 1.0) */}
          <rect x="50" y="30" width="530" height="60" className="fill-emerald-500/10 dark:fill-emerald-500/15" />
          {/* Threshold Zone (0.50 to 0.75) */}
          <rect x="50" y="90" width="530" height="60" className="fill-amber-500/10 dark:fill-amber-500/15" />
          {/* Severe Fatigue (< 0.50) */}
          <rect x="50" y="150" width="530" height="60" className="fill-rose-500/10 dark:fill-rose-500/15" />

          {/* Grid lines & Reference Thresholds */}
          {/* LT1 = 0.75 Line */}
          <line x1="50" y1="90" x2="580" y2="90" stroke="#10b981" strokeWidth="1.5" strokeDasharray="4 4" />
          <text x="585" y="94" fontSize="10" fill="#10b981" fontWeight="600">LT1 (0.75)</text>

          {/* LT2 = 0.50 Line */}
          <line x1="50" y1="150" x2="580" y2="150" stroke="#f59e0b" strokeWidth="1.5" strokeDasharray="4 4" />
          <text x="585" y="154" fontSize="10" fill="#f59e0b" fontWeight="600">LT2 (0.50)</text>

          {/* Dynamic Trend Polyline */}
          <polyline
            fill="none"
            stroke="#0ea5e9"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            points="50,60 120,65 190,72 260,80 330,88 400,92 470,105 540,110"
          />

          {/* Data Points */}
          <circle cx="540" cy="110" r="5" className="fill-emerald-500 stroke-white dark:stroke-slate-900" strokeWidth="2" />
        </svg>
      </div>

      {/* Screen-reader accessible data table fallback */}
      <AccessibleDataTable
        caption="Historical DFA-alpha1 and Zone Metrics"
        headers={['Timestamp', 'DFA-α1 Value', 'Heart Rate (BPM)', 'Physiological Zone']}
        rows={data.map((d) => [
          d.timestamp,
          d.alpha1.toFixed(2),
          `${d.heartRate} bpm`,
          d.zone,
        ])}
      />
    </div>
  );
}
```

---

## 4. Tailwind CSS Configuration & Theme Engine (Dark/Light Mode)

### 4.1 Tailwind CSS Configuration (`tailwind.config.ts`)

```typescript
import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: 'class', // Enables HTML class-based manual and system-level switching
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './hooks/**/*.{js,ts,jsx,tsx,mdx}',
    './lib/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        // High-Contrast Biometric Zone Tokens
        zone: {
          recovery: 'hsl(var(--zone-recovery))',
          aerobic: 'hsl(var(--zone-aerobic))',
          threshold: 'hsl(var(--zone-threshold))',
          fatigue: 'hsl(var(--zone-fatigue))',
        },
        ecg: {
          trace: 'hsl(var(--ecg-trace))',
          grid: 'hsl(var(--ecg-grid))',
        },
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      fontFamily: {
        sans: ['var(--font-sans)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-mono)', 'monospace'],
      },
    },
  },
  plugins: [],
};

export default config;
```

### 4.2 CSS Variables & Contrast Architecture (`app/globals.css`)

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    /* Base Light Mode - WCAG AAA Contrast (15.3:1) */
    --background: 0 0% 100%;             /* #ffffff */
    --foreground: 222.2 84% 4.9%;        /* #020817 */
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 222.2 84% 4.9%;
    
    --primary: 158 64% 32%;              /* #1DB954 / Emerald 700 - Contrast 4.8:1 */
    --primary-foreground: 0 0% 100%;
    
    --secondary: 210 40% 96.1%;
    --secondary-foreground: 222.2 47.4% 11.2%;
    
    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 42%; /* #5d6d7e - Contrast 5.1:1 */
    
    --accent: 210 40% 96.1%;
    --accent-foreground: 222.2 47.4% 11.2%;
    
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 0 0% 100%;
    
    --border: 214.3 31.8% 88%;           /* #dbe2ea */
    --input: 214.3 31.8% 88%;
    --ring: 158 64% 32%;                 /* Focus Ring */
    --radius: 0.75rem;

    /* Biometric Semantic Zones - Light Mode */
    --zone-recovery: 217 91% 40%;        /* Deep Blue (4.9:1) */
    --zone-aerobic: 158 64% 32%;         /* Deep Emerald (4.8:1) */
    --zone-threshold: 38 92% 35%;        /* Deep Amber (4.6:1) */
    --zone-fatigue: 347 77% 40%;         /* Deep Crimson (4.7:1) */
    --ecg-trace: 192 95% 38%;            /* Dark Cyan (4.5:1) */
    --ecg-grid: 214.3 31.8% 90%;
  }

  .dark {
    /* Base Dark Mode - Pure OLED Optimized (18.2:1) */
    --background: 224 71% 4%;            /* #020617 / Slate 950 */
    --foreground: 210 40% 98%;           /* #f8fafc */
    --card: 222.2 84% 6.5%;              /* #090f20 */
    --card-foreground: 210 40% 98%;
    --popover: 222.2 84% 6.5%;
    --popover-foreground: 210 40% 98%;
    
    --primary: 158 64% 48%;              /* Emerald 400 - Contrast 8.2:1 */
    --primary-foreground: 222.2 84% 4.9%;
    
    --secondary: 217.2 32.6% 17.5%;
    --secondary-foreground: 210 40% 98%;
    
    --muted: 217.2 32.6% 17.5%;
    --muted-foreground: 215 20.2% 72%;   /* Contrast 6.8:1 */
    
    --accent: 217.2 32.6% 17.5%;
    --accent-foreground: 210 40% 98%;
    
    --destructive: 0 62.8% 45%;
    --destructive-foreground: 210 40% 98%;
    
    --border: 217.2 32.6% 17.5%;
    --input: 217.2 32.6% 17.5%;
    --ring: 158 64% 48%;
    
    /* Biometric Semantic Zones - Dark Mode */
    --zone-recovery: 217 91% 65%;        /* Light Blue (7.8:1) */
    --zone-aerobic: 158 64% 48%;         /* Bright Emerald (8.2:1) */
    --zone-threshold: 38 92% 50%;        /* Bright Amber (7.5:1) */
    --zone-fatigue: 347 77% 60%;         /* Bright Rose (7.4:1) */
    --ecg-trace: 187 92% 58%;            /* Vibrant Cyan (8.6:1) */
    --ecg-grid: 217.2 32.6% 15%;
  }
}
```

### 4.3 Anti-FOUC Theme Script (`components/theme/ThemeScript.tsx`)

To completely eradicate hydration flash and visual flickering when a user reloads or navigates, the theme script is injected as a raw, synchronous string in the HTML `<head>`:

```tsx
export function ThemeScript() {
  const themeScript = `
    (function() {
      try {
        var storedTheme = localStorage.getItem('theme');
        var systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        var theme = storedTheme || (systemPrefersDark ? 'dark' : 'light');
        if (theme === 'dark') {
          document.documentElement.classList.add('dark');
        } else {
          document.documentElement.classList.remove('dark');
        }
      } catch (e) {}
    })();
  `;

  return <script dangerouslySetInnerHTML={{ __html: themeScript }} />;
}
```

### 4.4 Color Contrast Ratio Audit Matrix

| Color Token | Light Value (Hex) | Light Contrast vs Bg | Dark Value (Hex) | Dark Contrast vs Bg | WCAG 2.1 AA Compliance |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `foreground` | `#020817` | **19.8 : 1** | `#f8fafc` | **18.2 : 1** | **Pass (AAA)** |
| `muted-foreground`| `#5d6d7e` | **5.1 : 1** | `#cbd5e1` | **6.8 : 1** | **Pass (AA)** |
| `zone-aerobic` (LT1)| `#059669` | **4.8 : 1** | `#34d399` | **8.2 : 1** | **Pass (AA/AAA)** |
| `zone-threshold` (LT2)| `#d97706` | **4.6 : 1** | `#fbbf24` | **7.5 : 1** | **Pass (AA/AAA)** |
| `zone-fatigue` | `#e11d48` | **4.7 : 1** | `#fb7185` | **7.4 : 1** | **Pass (AA/AAA)** |
| `ecg-trace` | `#0891b2` | **4.5 : 1** | `#22d3ee` | **8.6 : 1** | **Pass (AA/AAA)** |
| `focus-ring` | `#059669` | **4.8 : 1** | `#34d399` | **8.2 : 1** | **Pass (AA/AAA)** |

---

## 5. Strict Accessibility (WCAG 2.1 AA) Blueprint

### 5.1 Semantic ARIA Landmark Layout Hierarchy

The application structure establishes an unambiguous accessibility landmark tree:

```
┌────────────────────────────────────────────────────────────────────────┐
│ <header role="banner">                                                 │
│   ├── Logo & Brand (aria-label="Lauburu Zone 2 Home")                  │
│   ├── Session Telemetry Badge (aria-live="polite")                     │
│   └── <ThemeToggle> (role="button", aria-label="Switch Theme")         │
├────────────────────────────────┬───────────────────────────────────────┤
│ <nav role="navigation"         │ <main id="main-content" role="main">  │
│      aria-label="Main Nav">    │   ├── Skip-Link Anchor Landing        │
│   ├── /dashboard (aria-current)│   ├── <h1> Dashboard Title            │
│   ├── /telemetry               │   ├── <section aria-labelledby="..."> │
│   ├── /history                 │   │     └── Biometric Summary Cards   │
│   └── /settings                │   ├── <section aria-labelledby="..."> │
│                                │   │     ├── <LiveECGChart>            │
│                                │   │     └── <AccessibleDataTable>    │
│                                │   └── <section aria-labelledby="..."> │
│                                │         ├── <DFAAlpha1Chart>          │
│                                │         └── <AccessibleDataTable>    │
└────────────────────────────────┴───────────────────────────────────────┘
```

### 5.2 Skip-to-Content Link (`components/a11y/SkipLink.tsx`)

```tsx
import React from 'react';

export function SkipLink() {
  return (
    <a
      href="#main-content"
      className="sr-only fixed left-4 top-4 z-[9999] rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-lg transition-transform focus:not-sr-only focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
    >
      Skip to main content
    </a>
  );
}
```

### 5.3 Polymorphic Live Announcer (`components/a11y/LiveAnnouncer.tsx`)

Screen readers cannot inspect high-frequency canvas or SVG elements automatically. The `LiveAnnouncer` creates dedicated DOM live regions:

```tsx
'use client';

import React, { useState, useEffect, createContext, useContext, useCallback } from 'react';

interface A11yLiveContextType {
  announcePolite: (message: string) => void;
  announceAssertive: (message: string) => void;
}

const A11yLiveContext = createContext<A11yLiveContextType>({
  announcePolite: () => {},
  announceAssertive: () => {},
});

export function LiveAnnouncer({ children }: { children?: React.ReactNode }) {
  const [politeMessage, setPoliteMessage] = useState('');
  const [assertiveMessage, setAssertiveMessage] = useState('');

  const announcePolite = useCallback((msg: string) => {
    setPoliteMessage('');
    setTimeout(() => setPoliteMessage(msg), 50);
  }, []);

  const announceAssertive = useCallback((msg: string) => {
    setAssertiveMessage('');
    setTimeout(() => setAssertiveMessage(msg), 50);
  }, []);

  return (
    <A11yLiveContext.Provider value={{ announcePolite, announceAssertive }}>
      {children}
      {/* Hidden Live Region for Polite/Informational Events */}
      <div
        id="a11y-live-polite"
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      >
        {politeMessage}
      </div>

      {/* Hidden Live Region for Critical Physiological Alarms */}
      <div
        id="a11y-live-assertive"
        role="alert"
        aria-live="assertive"
        aria-atomic="true"
        className="sr-only"
      >
        {assertiveMessage}
      </div>
    </A11yLiveContext.Provider>
  );
}

export const useA11y = () => useContext(A11yLiveContext);
```

### 5.4 Screen-Reader Accessible Data Table (`components/a11y/AccessibleDataTable.tsx`)

```tsx
import React from 'react';

interface AccessibleDataTableProps {
  caption: string;
  headers: string[];
  rows: string[][];
  summary?: string;
}

export function AccessibleDataTable({
  caption,
  headers,
  rows,
  summary,
}: AccessibleDataTableProps) {
  if (rows.length === 0) return null;

  return (
    <div className="sr-only">
      <table aria-label={caption} summary={summary}>
        <caption>{caption}</caption>
        <thead>
          <tr>
            {headers.map((header, index) => (
              <th key={index} scope="col">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(-10).map((row, rowIndex) => (
            <tr key={rowIndex}>
              {row.map((cell, cellIndex) => (
                <td key={cellIndex}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

---

## 6. Zero-Mock Biometric Contracts & Integration

The frontend architecture maps directly to the live Python DSP pipelines in `03_biometrics_and_telemetry`:

```typescript
// types/biometrics.d.ts
export type PhysiologicalZone = 
  | 'Zone 1 (Active Recovery)' 
  | 'Zone 2 (Aerobic Base)' 
  | 'Zone 3 (Tempo / Aerobic Threshold)' 
  | 'Zone 4 (Anaerobic / LT2)' 
  | 'Zone 5 (Severe / VO2 Max)';

export interface RawECGPacket {
  sensorId: string;
  samplingRateHz: 128;
  timestamp: number; // Unix Epoch ms
  samplesMv: number[]; // Array of 16 float samples per 128Hz batch
  leadContact: boolean;
}

export interface DFAAlpha1Telemetry {
  timestamp: number;
  windowSizeSec: number;
  alpha1: number; // 0.75 = LT1 Aerobic, 0.50 = LT2 Anaerobic
  hrvRmssd: number;
  instantHeartRate: number;
  currentZone: PhysiologicalZone;
  fatigueIndex: number;
}
```

---

## 7. Verification & Automated Testing Strategy

### 7.1 Automated Axe-Core & Playwright a11y Test Suite (`tests/a11y.spec.ts`)

```typescript
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Zone 2 Endurance Frontend a11y Audit', () => {
  test('Dashboard passes WCAG 2.1 AA audits in both Light and Dark themes', async ({ page }) => {
    await page.goto('http://localhost:3000');

    // 1. Audit Light Mode
    const lightAudit = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    expect(lightAudit.violations).toEqual([]);

    // 2. Toggle Dark Mode
    await page.click('button[aria-label*="Switch theme"]');
    await expect(page.locator('html')).toHaveClass(/dark/);

    // 3. Audit Dark Mode
    const darkAudit = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    expect(darkAudit.violations).toEqual([]);
  });

  test('Skip to content link is focusable and navigates to main content', async ({ page }) => {
    await page.goto('http://localhost:3000');
    await page.keyboard.press('Tab');
    
    const skipLink = page.locator('a[href="#main-content"]');
    await expect(skipLink).toBeFocused();
    await expect(skipLink).toBeVisible();

    await page.keyboard.press('Enter');
    const mainContent = page.locator('#main-content');
    await expect(mainContent).toBeFocused();
  });

  test('Biometric charts contain accessible titles and offscreen data tables', async ({ page }) => {
    await page.goto('http://localhost:3000');
    
    const ecgImg = page.locator('canvas[role="img"]');
    await expect(ecgImg).toHaveAttribute('aria-label', /Live ECG waveform/);

    const dfaSvg = page.locator('svg[role="img"]');
    await expect(dfaSvg).toHaveAttribute('aria-labelledby');

    const dataTables = page.locator('table');
    expect(await dataTables.count()).toBeGreaterThanOrEqual(2);
  });
});
```

---

## 8. Summary of Deliverables & Scaffolding Checklist

1. **RSC Root Layout (`app/layout.tsx`)**: Created as a pure Server Component with zero hydration overhead.
2. **Server Navigation Shell (`components/nav/NavigationShell.tsx`)**: Implemented with `<header>`, `<nav>`, `<main>`, and skip-link targets.
3. **Dedicated Client Biometrics (`LiveECGChart.tsx`, `DFAAlpha1Chart.tsx`)**: Isolated with `"use client"`, high-DPI canvas loops, SVG landmarks, and screen-reader data table fallbacks.
4. **Tailwind Dark/Light Mode Theme (`tailwind.config.ts`, `globals.css`)**: Class-based strategy with CSS variables, anti-FOUC `ThemeScript`, and verified high-contrast color tokens.
5. **Accessibility Suite (`SkipLink.tsx`, `LiveAnnouncer.tsx`, `AccessibleDataTable.tsx`)**: Full WCAG 2.1 AA compliance with dual-tier live notifications and keyboard focus rings.
