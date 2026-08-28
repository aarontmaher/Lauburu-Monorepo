import type { Metadata } from "next";
import "./globals.css";
import { ThemeScript } from "@/components/theme/ThemeScript";
import { NavigationShell } from "@/components/nav/NavigationShell";
import { LiveAnnouncer } from "@/components/a11y/LiveAnnouncer";

export const metadata: Metadata = {
  title: "Zone 2 Endurance Biometrics",
  description: "Real-time DFA-alpha1 fractal analysis and ECG streaming for aerobic base training",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <ThemeScript />
      </head>
      <body className="min-h-screen bg-background text-foreground antialiased selection:bg-primary/20 selection:text-primary">
        <a href="#main-content" className="skip-link">
          Skip to main content
        </a>
        <LiveAnnouncer politeMessage="Zone 2 Endurance Biometrics Hub ready. Real-time telemetry monitoring initialized." />
        <NavigationShell>
          {children}
        </NavigationShell>
      </body>
    </html>
  );
}
