import "./globals.css";
import type { Metadata } from "next";
import AppShell from "@/components/AppShell";

export const metadata: Metadata = {
  title: "RevPlug — Revenue Recovery Control Plane",
  description: "RevPlug detects payment failures, chooses recovery actions within policy, and counts revenue only after settlement is verified.",
  openGraph: {
    title: "RevPlug — Revenue Recovery Control Plane",
    description: "Detect payment failures, enforce policy bounds, execute recovery actions, and count revenue only post-settlement.",
    siteName: "RevPlug",
    type: "website",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: "RevPlug — Revenue Recovery Control Plane",
    description: "Detect payment failures, enforce policy bounds, execute recovery actions, and count revenue only post-settlement.",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
