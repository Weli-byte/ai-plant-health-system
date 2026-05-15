import { ReactNode, useEffect, useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import {
  Leaf,
  LayoutDashboard,
  History,
  Sprout,
  FileBarChart2,
  MessageCircle,
  Menu,
  X,
  LogOut,
  User,
  Camera,
} from "lucide-react";

const sidebarItems = [
  { label: "Ana Sayfa", path: "/", icon: LayoutDashboard },
  { label: "Analizler", path: "/history", icon: History },
  { label: "Bitkilerim", path: "/plants", icon: Sprout },
  { label: "Raporlar", path: "/reports", icon: FileBarChart2 },
  { label: "AI Sohbet", path: "/chat", icon: MessageCircle },
];

const leftTabs = [
  { label: "Ana Sayfa", path: "/", icon: LayoutDashboard },
  { label: "Analizler", path: "/history", icon: History },
];
const rightTabs = [
  { label: "Raporlar", path: "/reports", icon: FileBarChart2 },
  { label: "Sohbet", path: "/chat", icon: MessageCircle },
];

export function AppShell({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  // Body scroll lock while drawer is open
  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [open]);

  const logout = () => {
    localStorage.removeItem("agri_user");
    navigate("/login");
  };

  return (
    <div
      className="relative flex min-h-dvh flex-col"
      style={{ background: "var(--renk-bej)" }}
    >
      {/* ── Top bar ───────────────────────────────────────────────────────── */}
      <header
        className="sticky top-0 z-30 flex items-center justify-between px-4 py-3"
        style={{ background: "var(--renk-koyu-yesil)" }}
      >
        <button
          onClick={() => setOpen(true)}
          className="flex h-10 w-10 items-center justify-center rounded-full transition"
          style={{ color: "rgba(255,255,255,0.8)" }}
          aria-label="Menüyü aç"
        >
          <Menu className="h-5 w-5" />
        </button>

        <Link to="/" className="flex items-center gap-2">
          <div
            className="flex h-8 w-8 items-center justify-center rounded-full"
            style={{ background: "var(--renk-acik-yesil)" }}
          >
            <Leaf className="h-4 w-4 text-white" />
          </div>
          <span className="text-base font-semibold tracking-tight text-white">
            AI Plant Health System
          </span>
        </Link>

        <Link
          to="/profile"
          className="flex h-10 w-10 items-center justify-center rounded-full transition"
          style={{ color: "rgba(255,255,255,0.8)" }}
        >
          <User className="h-4 w-4" />
        </Link>
      </header>

      {/* ── Main content ──────────────────────────────────────────────────── */}
      <main className="flex-1 px-4 pb-28 pt-4">{children}</main>

      {/* ── Bottom tab bar ────────────────────────────────────────────────── */}
      <nav
        className="fixed bottom-0 z-30 flex items-end bg-white"
        style={{
          left: "50%",
          transform: "translateX(-50%)",
          width: "100%",
          maxWidth: "430px",
          borderTop: "1px solid var(--renk-bej-border)",
        }}
      >
        <div className="flex flex-1">
          {leftTabs.map((tab) => (
            <BottomTabItem key={tab.path} tab={tab} />
          ))}
        </div>

        <div className="relative flex flex-col items-center justify-end pb-2" style={{ width: 72 }}>
          <Link
            to="/analysis/new"
            className="flex h-14 w-14 items-center justify-center rounded-full text-white shadow-lg active:scale-95 transition-transform"
            style={{ background: "var(--renk-acik-yesil)", marginTop: -24 }}
          >
            <Camera className="h-6 w-6" />
          </Link>
          <span className="mt-1 text-[9px] font-medium" style={{ color: "var(--renk-metin-soluk)" }}>
            Analiz
          </span>
        </div>

        <div className="flex flex-1">
          {rightTabs.map((tab) => (
            <BottomTabItem key={tab.path} tab={tab} />
          ))}
        </div>
      </nav>

      {/* ── Overlay — absolute so it's clipped inside phone-frame ─────────── */}
      <div
        onClick={() => setOpen(false)}
        style={{
          position: "absolute",
          inset: 0,
          zIndex: 999,
          background: "rgba(0,0,0,0.5)",
          transition: "opacity 0.3s ease-in-out",
          opacity: open ? 1 : 0,
          pointerEvents: open ? "auto" : "none",
        }}
      />

      {/* ── Sidebar drawer — absolute so it stays inside phone-frame ─────── */}
      <aside
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          height: "100%",
          width: "75%",
          maxWidth: "280px",
          background: "#1e3a1e",
          zIndex: 1000,
          display: "flex",
          flexDirection: "column",
          transform: open ? "translateX(0)" : "translateX(-100%)",
          transition: "transform 0.3s ease-in-out",
          boxShadow: open ? "4px 0 24px rgba(0,0,0,0.35)" : "none",
        }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-5 py-4"
          style={{ borderBottom: "1px solid rgba(255,255,255,0.15)" }}
        >
          <div className="flex items-center gap-2">
            <div
              className="flex h-9 w-9 items-center justify-center rounded-full"
              style={{ background: "var(--renk-acik-yesil)" }}
            >
              <Leaf className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="text-sm font-semibold text-white">AI Plant Health</p>
              <p className="text-[11px]" style={{ color: "rgba(255,255,255,0.55)" }}>
                Tarım Asistanı
              </p>
            </div>
          </div>
          <button
            onClick={() => setOpen(false)}
            className="flex h-9 w-9 items-center justify-center rounded-full transition hover:bg-white/10"
            style={{ color: "rgba(255,255,255,0.7)" }}
            aria-label="Kapat"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Nav links */}
        <nav className="flex-1 space-y-1 px-3 py-4">
          {sidebarItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              onClick={() => setOpen(false)}
              className="flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium transition"
              style={({ isActive }) => ({
                background: isActive ? "#5a8a3c" : "transparent",
                color: isActive ? "#ffffff" : "rgba(255,255,255,0.70)",
              })}
            >
              <span
                className="flex h-8 w-8 items-center justify-center rounded-lg"
                style={{ background: "rgba(255,255,255,0.15)" }}
              >
                <item.icon className="h-4 w-4" />
              </span>
              <span className="flex-1">{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Footer — logout */}
        <div className="p-3" style={{ borderTop: "1px solid rgba(255,255,255,0.15)" }}>
          <button
            onClick={logout}
            className="flex w-full items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium transition hover:bg-white/10"
            style={{ color: "rgba(220,80,80,0.90)" }}
          >
            <span
              className="flex h-8 w-8 items-center justify-center rounded-lg"
              style={{ background: "rgba(220,80,80,0.15)" }}
            >
              <LogOut className="h-4 w-4" />
            </span>
            Çıkış yap
          </button>
        </div>
      </aside>
    </div>
  );
}

function BottomTabItem({
  tab,
}: {
  tab: { label: string; path: string; icon: React.ComponentType<{ className?: string }> };
}) {
  return (
    <NavLink
      to={tab.path}
      className="flex flex-1 flex-col items-center gap-1 py-3 text-[10px] font-medium transition"
      style={({ isActive }) => ({
        color: isActive ? "var(--renk-acik-yesil)" : "var(--renk-metin-soluk)",
      })}
    >
      <tab.icon className="h-5 w-5" />
      <span>{tab.label}</span>
    </NavLink>
  );
}
