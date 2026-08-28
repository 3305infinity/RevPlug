"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

const navItems = [
  { href: "/", label: "Revenue Recovery", icon: "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" },
  { href: "/recovery", label: "Recovery Cases", icon: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" },
  { href: "/customers", label: "Customers", icon: "M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2 M9 11a4 4 0 100-8 4 4 0 000 8z" },
  { href: "/programs", label: "Programs", icon: "M4 6h16M4 10h16M4 14h16M4 18h16" },
  { href: "/run-recovery", label: "Run Recovery", icon: "M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z M21 12a9 9 0 11-18 0 9 9 0 0118 0z" },
  { href: "/batch-recovery", label: "Batch Recovery", icon: "M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" },
  { href: "/review", label: "Review Queue", icon: "M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" },
  { href: "/activity", label: "Activity", icon: "M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" },
  { href: "/reliability", label: "AI Performance", icon: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2 2z" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [status, setStatus] = useState<"checking" | "connected" | "disconnected">("checking");

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/health`)
      .then((r) => r.ok ? setStatus("connected") : setStatus("disconnected"))
      .catch(() => setStatus("disconnected"));
  }, []);

  const colors = { checking: "var(--warning)", connected: "var(--success)", disconnected: "var(--danger)" };
  const labels = { checking: "Checking...", connected: "API Connected", disconnected: "API Disconnected" };

  return (
    <aside style={{
      width: 240,
      background: "var(--bg-secondary)",
      borderRight: "1px solid var(--border)",
      display: "flex",
      flexDirection: "column",
      position: "fixed",
      height: "100vh",
      zIndex: 100,
    }}>
      <div style={{ padding: "1.25rem 1.25rem", borderBottom: "1px solid var(--border)" }}>
        <Link href="/" style={{ display: "flex", alignItems: "center", gap: "0.625rem", textDecoration: "none" }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8,
            background: "linear-gradient(135deg, var(--accent), var(--purple))",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "0.875rem", fontWeight: 700, color: "#fff",
          }}>
            R
          </div>
          <div>
            <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--text-primary)", letterSpacing: "-0.01em" }}>
              RecoverOS
            </div>
            <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
              Revenue Recovery
            </div>
          </div>
        </Link>
      </div>

      <nav style={{ flex: 1, padding: "0.75rem 0.5rem" }}>
        {navItems.map((item) => {
          const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.625rem",
                padding: "0.6rem 0.75rem",
                borderRadius: 8,
                background: active ? "var(--accent-subtle)" : "transparent",
                color: active ? "var(--accent)" : "var(--text-secondary)",
                fontWeight: active ? 500 : 400,
                textDecoration: "none",
                fontSize: "0.8125rem",
                marginBottom: "0.125rem",
                transition: "background 0.15s, color 0.15s",
              }}
            >
              <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d={item.icon} />
              </svg>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div style={{ padding: "0.75rem 1.25rem", borderTop: "1px solid var(--border)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.6875rem" }}>
          <div style={{ width: 6, height: 6, borderRadius: "50%", background: colors[status] }} />
          <span style={{ color: colors[status] }}>{labels[status]}</span>
        </div>
      </div>
    </aside>
  );
}
