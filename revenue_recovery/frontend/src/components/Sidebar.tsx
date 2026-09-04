"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api, User } from "@/lib/api";

const navGroups = [
  {
    label: "OVERVIEW",
    items: [
      { href: "/dashboard", label: "Command Center", icon: "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" },
    ],
  },
  {
    label: "RECOVER WORKFLOW",
    items: [
      { href: "/recovery", label: "Recovery Queue", icon: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" },
      { href: "/run-recovery", label: "Single Case Control", icon: "M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z M21 12a9 9 0 11-18 0 9 9 0 0118 0z" },
      { href: "/customers", label: "Customers", icon: "M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" },
      { href: "/batch-recovery", label: "Batch Results", icon: "M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" },
    ],
  },
  {
    label: "CONTROL & LABS",
    items: [
      { href: "/review", label: "Review Queue", icon: "M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" },
      { href: "/controls", label: "Safety & Policies", icon: "M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" },
      { href: "/policy-simulator", label: "Policy Simulator", icon: "M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 01-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" },
      { href: "/reliability", label: "Reliability / Failure Lab", icon: "M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L5.6 15.12a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" },
      { href: "/proof-lab", label: "Benchmark Proof Lab", icon: "M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" },
    ],
  },
];

interface SidebarProps {
  user?: User | null;
  onLogout?: () => void;
}

export default function Sidebar({ user, onLogout }: SidebarProps) {
  const pathname = usePathname();
  const [status, setStatus] = useState<"checking" | "connected" | "disconnected">("checking");

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/health`)
      .then((r) => r.ok ? setStatus("connected") : setStatus("disconnected"))
      .catch(() => setStatus("disconnected"));
  }, []);

  const colors = { checking: "var(--warning)", connected: "var(--success)", disconnected: "var(--danger)" };
  const labels = { checking: "Checking", connected: "Connected", disconnected: "Disconnected" };

  const handleLogoutClick = async () => {
    try { await api.logout(); } catch { /* ignore */ }
    localStorage.removeItem("revplug_user");
    if (onLogout) onLogout(); else window.location.href = "/login";
  };

  return (
    <aside style={{
      width: 220,
      background: "var(--bg-secondary)",
      borderRight: "1px solid var(--border)",
      display: "flex",
      flexDirection: "column",
      position: "fixed",
      height: "100vh",
      zIndex: 100,
    }}>
      {/* Brand Header */}
      <div style={{ padding: "1rem 1rem", borderBottom: "1px solid var(--border)" }}>
        <Link href="/dashboard" style={{ display: "flex", alignItems: "center", gap: "0.625rem", textDecoration: "none" }}>
          <div style={{
            width: 28, height: 28, borderRadius: 6,
            background: "#2563eb",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "0.8125rem", fontWeight: 700, color: "#fff",
          }}>
            R
          </div>
          <div>
            <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)", letterSpacing: "-0.01em" }}>
              RevPlug
            </div>
            <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
              Revenue Control Plane
            </div>
          </div>
        </Link>
      </div>

      {/* Navigation Links */}
      <nav style={{ flex: 1, padding: "0.75rem 0.5rem", overflowY: "auto" }}>
        {navGroups.map((group) => (
          <div key={group.label} style={{ marginBottom: "1rem" }}>
            <div style={{
              padding: "0.25rem 0.625rem",
              fontSize: "0.625rem",
              fontWeight: 600,
              color: "var(--text-muted)",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
            }}>
              {group.label}
            </div>
            {group.items.map((item) => {
              const active = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href));
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.5rem",
                    padding: "0.45rem 0.625rem",
                    borderRadius: 6,
                    background: active ? "rgba(59, 130, 246, 0.1)" : "transparent",
                    color: active ? "#60a5fa" : "var(--text-secondary)",
                    fontWeight: active ? 600 : 400,
                    textDecoration: "none",
                    fontSize: "0.8125rem",
                    marginBottom: "0.125rem",
                    transition: "background 0.12s, color 0.12s",
                  }}
                >
                  <svg width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" style={{ flexShrink: 0, opacity: active ? 1 : 0.7 }}>
                    <path strokeLinecap="round" strokeLinejoin="round" d={item.icon} />
                  </svg>
                  {item.label}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Operational System Status Strip */}
      <div style={{ padding: "0.625rem 0.875rem", borderTop: "1px solid var(--border)", background: "rgba(0,0,0,0.15)" }}>
        <div style={{ fontSize: "0.625rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 4 }}>
          SYSTEM STATUS
        </div>
        <div style={{ fontSize: "0.6875rem", color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: 2 }}>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span>API:</span>
            <span style={{ color: colors[status], fontWeight: 600 }}>{labels[status]}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span>Execution:</span>
            <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>Razorpay Test</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span>AI Provider:</span>
            <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>Groq Primary</span>
          </div>
        </div>
      </div>

      {user && (
        <div style={{ padding: "0.625rem 0.875rem", borderTop: "1px solid var(--border)" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {user.full_name || "Operations User"}
              </div>
            </div>
            <button
              onClick={handleLogoutClick}
              style={{ background: "transparent", border: "none", color: "var(--danger)", cursor: "pointer", fontSize: "0.6875rem", fontWeight: 600 }}
            >
              Logout
            </button>
          </div>
        </div>
      )}
    </aside>
  );
}
