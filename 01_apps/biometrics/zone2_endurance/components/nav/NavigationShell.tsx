import React from "react";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";

export interface NavigationShellProps {
  children: React.ReactNode;
  className?: string;
}

/**
 * Server Component: NavigationShell
 * Provides the global navigation layout with responsive Header, Sidebar, and accessible Main landmark.
 */
export function NavigationShell({ children, className = "" }: NavigationShellProps) {
  return (
    <div className={`min-h-screen flex flex-col bg-background text-foreground ${className}`}>
      {/* Global Header */}
      <Header />

      {/* Main App Body with Sidebar */}
      <div className="flex-1 flex">
        <Sidebar />
        <main
          id="main-content"
          role="main"
          tabIndex={-1}
          className="flex-1 flex flex-col min-w-0 focus:outline-none"
        >
          {children}
        </main>
      </div>
    </div>
  );
}

export default NavigationShell;
