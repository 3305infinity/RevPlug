import "./globals.css";
import type { Metadata } from "next";
import AppShell from "@/components/AppShell";

export const metadata: Metadata = {
  title: "RecoverOS — Autonomous Revenue Recovery Infrastructure",
  description: "AI-assisted revenue recovery engine with deterministic safety controls and payment verification",
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
