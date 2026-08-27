import React from "react";
import { Link, NavLink, useLocation, useParams } from "react-router-dom";
import { useAuth } from "../AuthContext";
import { SignOut, Scales } from "@phosphor-icons/react";

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const runMatch = location.pathname.match(/^\/runs\/([^/]+)/);
  const runId = runMatch ? runMatch[1] : null;

  const tabs = runId
    ? [
        { to: `/runs/${runId}`, label: "Summary", end: true },
        { to: `/runs/${runId}/matches`, label: "Matches" },
        { to: `/runs/${runId}/exceptions`, label: "Exceptions" },
        { to: `/runs/${runId}/audit`, label: "Audit" },
        { to: `/runs/${runId}/report`, label: "Report" },
      ]
    : [];

  return (
    <div className="min-h-screen">
      <header className="bg-white/90 backdrop-blur-xl border-b border-slate-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center h-14 gap-6">
          <Link to="/" className="flex items-center gap-2" data-testid="nav-logo-link">
            <span className="w-7 h-7 rounded bg-blue-700 text-white flex items-center justify-center">
              <Scales size={16} weight="bold" />
            </span>
            <span className="font-semibold tracking-tight text-slate-950">SettleSense</span>
          </Link>
          <nav className="flex items-center gap-1 flex-1">
            <NavLink to="/" end data-testid="nav-runs-link"
              className={({ isActive }) =>
                `text-sm px-3 py-1.5 rounded-md ${isActive && !runId ? "bg-slate-100 text-slate-950 font-medium" : "text-slate-600 hover:text-slate-950"}`}>
              Runs
            </NavLink>
            {tabs.map((t) => (
              <NavLink key={t.to} to={t.to} end={t.end}
                data-testid={`nav-tab-${t.label.toLowerCase()}`}
                className={({ isActive }) =>
                  `text-sm px-3 py-1.5 rounded-md ${isActive ? "bg-slate-100 text-slate-950 font-medium" : "text-slate-600 hover:text-slate-950"}`}>
                {t.label}
              </NavLink>
            ))}
          </nav>
          {runId && (
            <span className="mono-num text-xs text-slate-500 hidden sm:block" data-testid="nav-run-id">{runId}</span>
          )}
          {user && (
            <div className="flex items-center gap-3">
              <div className="text-right hidden sm:block">
                <div className="text-xs font-medium text-slate-800">{user.name}</div>
                <div className="text-[11px] text-slate-500">{user.role}</div>
              </div>
              <button onClick={logout} className="text-slate-500 hover:text-red-700 p-1.5"
                title="Sign out" data-testid="logout-btn">
                <SignOut size={18} />
              </button>
            </div>
          )}
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">{children}</main>
      <footer className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-8 text-[11px] text-slate-400">
        SettleSense · synthetic / Test Mode data only · fee &amp; tax rules are versioned demo assumptions · not tax or accounting advice
      </footer>
    </div>
  );
}
