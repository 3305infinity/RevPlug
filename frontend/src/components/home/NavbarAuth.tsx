"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

export default function NavbarAuth() {
  // Default to true for demo as requested ("use this state for the demo")
  const [isLoggedIn, setIsLoggedIn] = useState(true);
  const [user, setUser] = useState({
    name: "Alex Vance",
    email: "alex@revplug.io",
    initials: "AV",
  });
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Check if real user is stored in localStorage
    const storedUser = typeof window !== "undefined" ? localStorage.getItem("revplug_user") : null;
    if (storedUser) {
      try {
        const parsed = JSON.parse(storedUser);
        if (parsed && parsed.full_name) {
          const names = String(parsed.full_name).trim().split(" ");
          const inits = names.length > 1
            ? (names[0][0] + names[names.length - 1][0]).toUpperCase()
            : names[0].substring(0, 2).toUpperCase();
          setUser({
            name: parsed.full_name,
            email: parsed.email || "user@revplug.io",
            initials: inits,
          });
          setIsLoggedIn(true);
        }
      } catch {
        // use default demo state
      }
    }
  }, []);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = async () => {
    try {
      await api.logout();
    } catch {
      // ignore
    }
    if (typeof window !== "undefined") {
      localStorage.removeItem("revplug_user");
      localStorage.removeItem("revplug_session_token");
    }
    setIsLoggedIn(false);
    setDropdownOpen(false);
  };

  if (!isLoggedIn) {
    return (
      <div style={{ display: "flex", alignItems: "center", gap: "0.85rem" }}>
        <Link
          href="/login"
          style={{
            fontSize: "0.8125rem",
            color: "#8b949e",
            textDecoration: "none",
            fontWeight: 500,
            transition: "color 0.15s ease",
          }}
        >
          Log in
        </Link>
        <Link
          href="/signup"
          style={{
            fontSize: "0.75rem",
            color: "#ffffff",
            background: "#2563eb",
            padding: "0.35rem 0.75rem",
            borderRadius: 4,
            fontWeight: 600,
            textDecoration: "none",
            boxShadow: "0 1px 3px rgba(37, 99, 235, 0.3)",
            transition: "background 0.15s ease",
            display: "inline-flex",
            alignItems: "center",
            gap: "0.3rem",
          }}
        >
          Sign up
        </Link>
      </div>
    );
  }

  return (
    <div ref={dropdownRef} style={{ position: "relative" }}>
      <button
        onClick={() => setDropdownOpen(!dropdownOpen)}
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.5rem",
          background: "rgba(22, 27, 34, 0.8)",
          border: "1px solid #30363d",
          borderRadius: 20,
          padding: "0.25rem 0.6rem 0.25rem 0.3rem",
          cursor: "pointer",
          color: "#f0f6fc",
          fontSize: "0.75rem",
          fontWeight: 500,
          fontFamily: "inherit",
          transition: "all 0.15s ease",
        }}
      >
        {/* Circular Avatar / Initials */}
        <div
          style={{
            width: 24,
            height: 24,
            borderRadius: "50%",
            background: "linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)",
            color: "#ffffff",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "0.6875rem",
            fontWeight: 700,
            letterSpacing: "0.02em",
            boxShadow: "0 0 6px rgba(37, 99, 235, 0.4)",
          }}
        >
          {user.initials}
        </div>

        {/* User Name */}
        <span style={{ color: "#c9d1d9", fontWeight: 500 }}>{user.name}</span>

        {/* Chevron Icon */}
        <svg
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{
            color: "#8b949e",
            transition: "transform 0.2s ease",
            transform: dropdownOpen ? "rotate(180deg)" : "rotate(0deg)",
          }}
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {/* Dropdown Menu */}
      {dropdownOpen && (
        <div
          style={{
            position: "absolute",
            top: "calc(100% + 8px)",
            right: 0,
            width: 190,
            background: "#0d1117",
            border: "1px solid #30363d",
            borderRadius: 8,
            boxShadow: "0 10px 30px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(255, 255, 255, 0.05)",
            padding: "0.375rem 0",
            zIndex: 200,
          }}
        >
          {/* User Info Header */}
          <div style={{ padding: "0.5rem 0.85rem", borderBottom: "1px solid #21262d" }}>
            <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "#f0f6fc" }}>
              {user.name}
            </div>
            <div style={{ fontSize: "0.6875rem", color: "#8b949e", marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {user.email}
            </div>
          </div>

          {/* Menu Items */}
          <div style={{ padding: "0.25rem 0" }}>
            <Link
              href="/controls"
              onClick={() => setDropdownOpen(false)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                padding: "0.45rem 0.85rem",
                fontSize: "0.75rem",
                color: "#c9d1d9",
                textDecoration: "none",
                transition: "background 0.12s ease",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.background = "#161b22";
                (e.currentTarget as HTMLElement).style.color = "#ffffff";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.background = "transparent";
                (e.currentTarget as HTMLElement).style.color = "#c9d1d9";
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
              </svg>
              <span>Settings</span>
            </Link>

            <button
              onClick={handleLogout}
              style={{
                width: "100%",
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                padding: "0.45rem 0.85rem",
                fontSize: "0.75rem",
                color: "#f85149",
                background: "transparent",
                border: "none",
                cursor: "pointer",
                textAlign: "left",
                fontFamily: "inherit",
                transition: "background 0.12s ease",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.background = "rgba(248, 81, 73, 0.1)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.background = "transparent";
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" y1="12" x2="9" y2="12" />
              </svg>
              <span>Log out</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
