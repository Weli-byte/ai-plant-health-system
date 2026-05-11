import { ReactNode, useState } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
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
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { label: "Dashboard", path: "/", icon: LayoutDashboard },
  { label: "Analizler", path: "/history", icon: History },
  { label: "Bitkilerim", path: "/plants", icon: Sprout },
  { label: "Raporlar", path: "/reports", icon: FileBarChart2 },
  { label: "AI Sohbet", path: "/chat", icon: MessageCircle, highlight: true },
];

export function AppShell({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const current = navItems.find((n) => n.path === location.pathname);

  const logout = () => {
    localStorage.removeItem("agri_user");
    navigate("/login");
  };

  return (
    <div className="flex min-h-dvh flex-col bg-background">
      {/* Top bar */}
      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-border/60 bg-card/80 px-4 py-3 backdrop-blur-md">
        <button
          onClick={() => setOpen(true)}
          className="flex h-10 w-10 items-center justify-center rounded-full bg-accent/60 text-accent-foreground transition hover:bg-accent"
          aria-label="Menüyü aç"
        >
          <Menu className="h-5 w-5" />
        </button>
        <Link to="/" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-leaf-gradient">
            <Leaf className="h-4 w-4 text-primary-foreground" />
          </div>
          <span className="text-base font-semibold tracking-tight text-foreground">
            AI Plant Health System
          </span>
        </Link>
        <Link
          to="/profile"
          className="flex h-10 w-10 items-center justify-center rounded-full bg-accent/60 text-accent-foreground transition hover:bg-accent"
        >
          <User className="h-4 w-4" />
        </Link>
      </header>

      {/* Page title strip */}
      {current && (
        <div className="px-5 pb-1 pt-4">
          <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
            AI Plant Health System
          </p>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            {current.label}
          </h1>
        </div>
      )}

      <main className="flex-1 px-4 pb-24 pt-3">{children}</main>

      {/* Drawer overlay */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-foreground/20 backdrop-blur-sm sm:absolute"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Sidebar drawer */}
      <aside
        className={cn(
          "fixed left-0 top-0 z-50 flex h-full w-72 flex-col bg-sidebar text-sidebar-foreground shadow-2xl transition-transform sm:absolute",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex items-center justify-between border-b border-sidebar-border px-5 py-4">
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-leaf-gradient">
              <Leaf className="h-5 w-5 text-primary-foreground" />
            </div>
            <div>
              <p className="text-sm font-semibold">AI Plant Health System</p>
              <p className="text-[11px] text-muted-foreground">Tarım Asistanı</p>
            </div>
          </div>
          <button
            onClick={() => setOpen(false)}
            className="flex h-9 w-9 items-center justify-center rounded-full hover:bg-sidebar-accent"
            aria-label="Kapat"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <nav className="flex-1 space-y-1 px-3 py-4">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-2xl px-3 py-3 text-sm font-medium transition",
                  isActive
                    ? "bg-sidebar-accent text-sidebar-accent-foreground shadow-card"
                    : "text-sidebar-foreground/80 hover:bg-sidebar-accent/60",
                  item.highlight && !isActive && "ring-1 ring-primary/30"
                )
              }
            >
              <span
                className={cn(
                  "flex h-9 w-9 items-center justify-center rounded-xl",
                  item.highlight
                    ? "bg-leaf-gradient text-primary-foreground"
                    : "bg-accent/60 text-accent-foreground"
                )}
              >
                <item.icon className="h-4 w-4" />
              </span>
              <span className="flex-1">{item.label}</span>
              {item.highlight && (
                <span className="rounded-full bg-primary/15 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-primary">
                  AI
                </span>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-sidebar-border p-3">
          <button
            onClick={logout}
            className="flex w-full items-center gap-3 rounded-2xl px-3 py-3 text-sm font-medium text-sidebar-foreground/80 transition hover:bg-sidebar-accent/60"
          >
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent/60">
              <LogOut className="h-4 w-4" />
            </span>
            Çıkış yap
          </button>
        </div>
      </aside>
    </div>
  );
}
