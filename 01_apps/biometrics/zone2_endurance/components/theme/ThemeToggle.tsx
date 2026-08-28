"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Sun, Moon } from "lucide-react";

export interface ThemeToggleProps {
  className?: string;
  showLabel?: boolean;
}

/**
 * Accessible Dark/Light Mode Theme Toggle Component
 * - Persists theme preference to localStorage ('theme' key)
 * - Toggles 'dark' class on document.documentElement
 * - Fully accessible: ARIA attributes, semantic button, keyboard navigable, screen-reader status
 */
export function ThemeToggle({ className = "", showLabel = false }: ThemeToggleProps) {
  const [theme, setTheme] = useState<"light" | "dark">("dark");
  const [mounted, setMounted] = useState(false);

  // Synchronize with DOM on mount
  useEffect(() => {
    const isDark = document.documentElement.classList.contains("dark");
    setTheme(isDark ? "dark" : "light");
    setMounted(true);

    // Watch for system preference changes if no manual override in localStorage
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const handleChange = (e: MediaQueryListEvent) => {
      if (!localStorage.getItem("theme")) {
        const newTheme = e.matches ? "dark" : "light";
        setTheme(newTheme);
        if (newTheme === "dark") {
          document.documentElement.classList.add("dark");
        } else {
          document.documentElement.classList.remove("dark");
        }
      }
    };

    mediaQuery.addEventListener("change", handleChange);
    return () => mediaQuery.removeEventListener("change", handleChange);
  }, []);

  const toggleTheme = useCallback(() => {
    const nextTheme = theme === "dark" ? "light" : "dark";
    setTheme(nextTheme);

    try {
      localStorage.setItem("theme", nextTheme);
    } catch (e) {
      console.warn("Failed to persist theme preference to localStorage:", e);
    }

    if (nextTheme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [theme]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      toggleTheme();
    }
  };

  const isDark = theme === "dark";
  const ariaLabel = isDark
    ? "Current theme is Dark. Activate to switch to Light mode."
    : "Current theme is Light. Activate to switch to Dark mode.";

  return (
    <button
      type="button"
      role="switch"
      aria-checked={isDark}
      aria-label={ariaLabel}
      title={isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}
      onClick={toggleTheme}
      onKeyDown={handleKeyDown}
      tabIndex={0}
      className={`relative inline-flex items-center justify-center p-2 rounded-lg border border-border bg-card text-foreground hover:bg-secondary transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background min-h-[44px] min-w-[44px] ${className}`}
    >
      <span className="sr-only">
        {isDark ? "Switch to light theme" : "Switch to dark theme"}
      </span>

      {/* Avoid hydration mismatch visual pop */}
      {!mounted ? (
        <div className="w-5 h-5 opacity-0" aria-hidden="true" />
      ) : isDark ? (
        <Sun className="w-5 h-5 text-amber-400 transition-transform duration-200 hover:rotate-45" aria-hidden="true" />
      ) : (
        <Moon className="w-5 h-5 text-slate-700 transition-transform duration-200 hover:-rotate-12" aria-hidden="true" />
      )}

      {showLabel && mounted && (
        <span className="ml-2 text-sm font-medium">
          {isDark ? "Light Mode" : "Dark Mode"}
        </span>
      )}
    </button>
  );
}

export default ThemeToggle;
