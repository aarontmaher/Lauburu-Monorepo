import React from "react";
import Link from "next/link";
import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { Activity, Radio, BarChart3, Settings } from "lucide-react";

export interface HeaderProps {
  title?: string;
  className?: string;
}

/**
 * Server Component: Header
 * Renders the top navigation banner, branding, live status pill, and ThemeToggle.
 */
export function Header({
  title = "Zone 2 Endurance Biometrics",
  className = "",
}: HeaderProps) {
  return (
    <header
      role="banner"
      aria-label="Application Header"
      className={`sticky top-0 z-40 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 ${className}`}
    >
      <div className="container flex h-16 max-w-7xl items-center justify-between px-4 sm:px-8">
        {/* Brand & Logo */}
        <div className="flex items-center gap-3">
          <Link
            href="/"
            aria-label="Zone 2 Endurance Home"
            className="flex items-center gap-2.5 font-bold text-foreground hover:opacity-90 transition-opacity focus-visible:ring-2 focus-visible:ring-primary rounded-md p-1"
          >
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
              <Activity className="h-5 w-5" aria-hidden="true" />
            </div>
            <div className="flex flex-col">
              <span className="text-base font-bold tracking-tight text-foreground leading-none">
                {title}
              </span>
              <span className="text-[10px] text-muted-foreground font-medium tracking-wide uppercase mt-0.5">
                Biometric Telemetry Hub
              </span>
            </div>
          </Link>
        </div>

        {/* Live Session Status Pill */}
        <div
          role="status"
          aria-label="Live telemetry stream status: Active"
          className="hidden sm:inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30"
        >
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
          </span>
          <span className="font-semibold">Live Telemetry</span>
        </div>

        {/* Navigation Links & Theme Switch */}
        <div className="flex items-center gap-3 sm:gap-4">
          <nav role="navigation" aria-label="Main Navigation" className="hidden md:flex items-center gap-1">
            <Link
              href="/"
              className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-foreground hover:bg-muted rounded-md transition-colors focus-visible:ring-2 focus-visible:ring-primary"
            >
              <Radio className="w-4 h-4 text-emerald-500" aria-hidden="true" />
              <span>Live Monitor</span>
            </Link>
            <Link
              href="/history"
              className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted rounded-md transition-colors focus-visible:ring-2 focus-visible:ring-primary"
            >
              <BarChart3 className="w-4 h-4" aria-hidden="true" />
              <span>History</span>
            </Link>
            <Link
              href="/settings"
              className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted rounded-md transition-colors focus-visible:ring-2 focus-visible:ring-primary"
            >
              <Settings className="w-4 h-4" aria-hidden="true" />
              <span>Settings</span>
            </Link>
          </nav>

          <div className="h-4 w-px bg-border hidden md:block" aria-hidden="true" />

          {/* Accessible Theme Toggle (Client Component) */}
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}

export default Header;
