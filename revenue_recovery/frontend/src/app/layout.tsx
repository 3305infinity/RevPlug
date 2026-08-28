import "./globals.css";
import type { Metadata } from "next";
import Sidebar from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "RecoverOS — Intelligent Revenue Recovery",
  description: "AI-assisted payment recovery engine with deterministic safety controls",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div style={{ display: "flex", minHeight: "100vh" }}>
          <Sidebar />
          <main style={{ flex: 1, overflow: "auto", background: "var(--bg-root)" }}>
            <div style={{ maxWidth: 1280, margin: "0 auto", padding: "2rem 2.5rem" }}>
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  );
}
