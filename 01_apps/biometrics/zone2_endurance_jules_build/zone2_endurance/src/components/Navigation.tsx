import Link from "next/link";
import { ThemeToggle } from "./ThemeToggle";
import { Activity } from "lucide-react";

export function Navigation() {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-gray-200 dark:border-gray-800 bg-white/80 dark:bg-black/80 backdrop-blur">
      <div className="max-w-7xl mx-auto flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-2">
          <Activity className="h-6 w-6 text-blue-600 dark:text-blue-400" aria-hidden="true" />
          <Link href="/" className="font-bold text-xl tracking-tight">
            Zone2
          </Link>
        </div>
        
        <nav aria-label="Main Navigation" className="flex items-center gap-6">
          <Link href="/" className="text-sm font-medium hover:text-blue-600 dark:hover:text-blue-400">
            Dashboard
          </Link>
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
