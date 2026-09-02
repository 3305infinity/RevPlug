"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api, User } from "@/lib/api";

const navGroups = [
  {
    label: "OVERVIEW",
    items: [
      { href: "/dashboard", label: "Overview", icon: "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" },
    ],
  },
  {
    label: "RECOVERY",
    items: [
      { href: "/recovery", label: "Opportunities", icon: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" },
      { href: "/batch-recovery", label: "Batch Results", icon: "M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" },
      { href: "/allocation", label: "Capital Allocation", icon: "M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" },
    ],
  },
  {
    label: "INTELLIGENCE",
    items: [
      { href: "/strategy-analytics", label: "Strategies", icon: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" },
      { href: "/proof-lab", label: "Proof Lab", icon: "M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" },
    ],
  },
  {
    label: "OPERATIONS",
    items: [
      { href: "/review", label: "Review Queue", icon: "M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" },
      { href: "/incidents", label: "Incidents", icon: "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" },
      { href: "/controls", label: "Safety Controls", icon: "M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" },
      { href: "/policy-config", label: "Policy Config", icon: "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z" },
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
