"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import { api, User } from "@/lib/api";

const PUBLIC_PATHS = ["/", "/login", "/signup"];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const isPublicPage = PUBLIC_PATHS.includes(pathname);

  useEffect(() => {
    // Try reading cached user from localStorage for instant initial render
    const cached = localStorage.getItem("recoveros_user");
    if (cached) {
      try {
        setUser(JSON.parse(cached));
      } catch {
        // ignore
      }
    }

    // Verify session against API /api/auth/me
    api
      .me()
      .then((res) => {
        if (res && res.user) {
          setUser(res.user);
          localStorage.setItem("recoveros_user", JSON.stringify(res.user));
        } else {
          setUser(null);
          localStorage.removeItem("recoveros_user");
          if (!isPublicPage) {
            router.push("/login");
          }
        }
      })
      .catch(() => {
        setUser(null);
        localStorage.removeItem("recoveros_user");
        if (!isPublicPage) {
          router.push("/login");
        }
      })
      .finally(() => {
        setLoading(false);
      });
  }, [pathname, isPublicPage, router]);

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem("recoveros_user");
    router.push("/login");
  };

  if (isPublicPage) {
    return (
      <main style={{ minHeight: "100vh", background: "var(--bg-root)" }}>
        {children}
      </main>
    );
  }

  if (loading && !user) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#09090b",
          color: "#a1a1aa",
          fontFamily: "Inter, system-ui, sans-serif",
          fontSize: "0.875rem",
        }}
      >
        Authenticating session...
      </div>
    );
  }

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar user={user} onLogout={handleLogout} />
      <main style={{ flex: 1, marginLeft: 240, minWidth: 0, background: "var(--bg-root)" }}>
        <div style={{ maxWidth: 1280, margin: "0 auto", padding: "2rem 2.5rem" }}>
          {children}
        </div>
      </main>
    </div>
  );
}
