import { useState } from "react";
import { NavLink, Outlet, Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function DashboardLayout() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  function handleSignOut() {
    logout();
    navigate("/login");
  }

  return (
    <div className="min-h-screen bg-parchment">
      <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-ink/10 bg-white/90 px-4 backdrop-blur md:px-6">
        <div className="flex items-center gap-6">
          <Link to="/" className="flex items-center gap-2 font-display text-sm font-semibold text-ink">
            <span className="flex h-6 w-6 items-center justify-center rounded bg-ink text-[10px] font-mono text-parchment">§</span>
            Compliance
          </Link>
          <nav className="hidden items-center gap-1 sm:flex">
            <NavLink
              to="/dashboard"
              end
              className={({ isActive }) =>
                `rounded-md px-3 py-1.5 text-sm font-medium transition ${
                  isActive ? "bg-teal-50 text-teal-600" : "text-slate-500 hover:bg-parchment-200 hover:text-ink"
                }`
              }
            >
              Documents
            </NavLink>
          </nav>
        </div>

        <div className="relative">
          <button
            onClick={() => setMenuOpen((v) => !v)}
            className="flex h-8 w-8 items-center justify-center rounded-full bg-ink font-mono text-xs text-parchment transition hover:opacity-90"
          >
            A
          </button>
          {menuOpen && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setMenuOpen(false)} />
              <div className="absolute right-0 top-10 z-50 w-44 overflow-hidden rounded-md border border-ink/10 bg-white py-1 shadow-card-hover animate-fade-up" style={{ animationDuration: "0.15s" }}>
                <button
                  onClick={handleSignOut}
                  className="block w-full px-3.5 py-2 text-left text-sm text-slate-600 transition hover:bg-parchment-100"
                >
                  Sign out
                </button>
              </div>
            </>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-[1600px] px-4 py-6 md:px-6 md:py-8">
        <Outlet />
      </main>
    </div>
  );
}
