import React from "react";
import Link from "next/link";
import { Activity, Radio, BarChart3, Settings, ShieldCheck, HeartPulse, Gauge } from "lucide-react";

export interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string; "aria-hidden"?: boolean | "true" | "false" }>;
}

export interface SidebarProps {
  currentPath?: string;
  className?: string;
}

const navItems: NavItem[] = [
  { label: "Dashboard", href: "/", icon: Activity },
  { label: "Live ECG", href: "/#ecg-monitor-heading", icon: Radio },
  { label: "DFA-alpha1", href: "/#dfa-chart-heading", icon: Gauge },
  { label: "Session History", href: "/history", icon: BarChart3 },
  { label: "Settings", href: "/settings", icon: Settings },
];

/**
 * Server Component: Sidebar
 * Renders the desktop sidebar navigation panel with accessible semantic landmarks.
 */
export function Sidebar({ currentPath = "/", className = "" }: SidebarProps) {
  return (
    <aside
      role="navigation"
      aria-label="Main Navigation"
      className={`hidden lg:flex flex-col w-64 border-r border-border bg-card/50 p-4 shrink-0 justify-between ${className}`}
    >
      <div className="space-y-6">
        {/* Navigation Section */}
        <div>
          <h3 className="px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
            Navigation Menu
          </h3>
          <nav className="space-y-1" aria-label="Sidebar Feeds">
            {navItems.map((item) => {
              const isActive = currentPath === item.href || (item.href !== "/" && currentPath.startsWith(item.href));
              const Icon = item.icon;
              return (
                <Link
                  key={item.label}
                  href={item.href}
                  aria-current={isActive ? "page" : undefined}
                  className={`flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg transition-colors min-h-[40px] focus-visible:ring-2 focus-visible:ring-primary ${
                    isActive
                      ? "bg-primary/10 text-primary font-semibold"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted"
                  }`}
                >
                  <Icon className="w-4 h-4 shrink-0" aria-hidden="true" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Biometric Threshold Profile */}
        <div>
          <h3 className="px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
            Endurance Thresholds
          </h3>
          <div className="rounded-lg border border-border bg-background p-3 text-xs space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">LT1 (Aerobic):</span>
              <span className="font-mono font-bold text-emerald-600 dark:text-emerald-400">&alpha;<sub>1</sub> = 0.75</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">LT2 (Anaerobic):</span>
              <span className="font-mono font-bold text-rose-600 dark:text-rose-400">&alpha;<sub>1</sub> = 0.50</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">Zone 2 Target:</span>
              <span className="font-mono font-bold text-primary">[0.75 - 1.00]</span>
            </div>
          </div>
        </div>
      </div>

      {/* Sensor Pairing Status Footer */}
      <div className="rounded-lg border border-border bg-card p-3 text-xs">
        <div className="flex items-center gap-2 mb-1.5 font-semibold text-foreground">
          <HeartPulse className="w-4 h-4 text-primary" aria-hidden="true" />
          <span>Movesense ECG</span>
        </div>
        <p className="text-muted-foreground text-[11px] leading-tight">
          Single-lead medical ECG strap active at 128Hz.
        </p>
      </div>
    </aside>
  );
}

export default Sidebar;
