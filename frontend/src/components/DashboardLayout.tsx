import { NavLink, Outlet, Link } from "react-router-dom";

const navItems = [
  { to: "/dashboard/upload", label: "Upload" },
  { to: "/dashboard/summaries", label: "Summaries" },
  { to: "/dashboard/obligations-risks", label: "Obligations & Risks" },
  { to: "/dashboard/deadlines", label: "Deadlines" },
  { to: "/dashboard/action-items", label: "Action Items" },
];

export default function DashboardLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-slate-50 md:flex-row">
      <aside className="w-full shrink-0 border-b border-slate-200 bg-white md:w-60 md:border-b-0 md:border-r">
        <div className="px-6 py-5">
          <Link to="/" className="text-sm font-semibold text-brand-700">
            Aged Care Compliance
          </Link>
        </div>
        <nav className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-col md:overflow-visible md:pb-6">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium transition ${
                  isActive
                    ? "bg-brand-50 text-brand-700"
                    : "text-slate-600 hover:bg-slate-100"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <main className="flex-1 px-6 py-8 md:px-10">
        <Outlet />
      </main>
    </div>
  );
}
