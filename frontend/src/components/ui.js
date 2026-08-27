import React from "react";

export function Money({ minor, className = "" }) {
  if (minor === null || minor === undefined) return <span className={className}>—</span>;
  const sign = minor < 0 ? "-" : "";
  const val = (Math.abs(minor) / 100).toLocaleString("en-IN", { minimumFractionDigits: 2 });
  return <span className={`mono-num ${minor < 0 ? "text-red-700" : ""} ${className}`}>{sign}₹{val}</span>;
}

export function Mono({ children, className = "" }) {
  return <span className={`mono-num text-[13px] ${className}`}>{children}</span>;
}

const badgeStyles = {
  green: "bg-green-100 text-green-800 border-green-200",
  amber: "bg-amber-100 text-amber-900 border-amber-200",
  red: "bg-red-100 text-red-900 border-red-200",
  slate: "bg-slate-100 text-slate-700 border-slate-200",
  blue: "bg-blue-50 text-blue-800 border-blue-200",
};

export function Badge({ tone = "slate", children, testId }) {
  return (
    <span data-testid={testId}
      className={`inline-flex items-center text-xs font-medium px-2.5 py-0.5 rounded-full border whitespace-nowrap ${badgeStyles[tone]}`}>
      {children}
    </span>
  );
}

export const severityTone = { critical: "red", high: "red", medium: "amber", low: "slate" };
export const statusTone = {
  OPEN: "amber", IN_REVIEW: "blue", RESOLVED: "green", REJECTED: "slate", UNRESOLVED: "red",
  CREATED: "slate", INGESTING: "amber", READY: "blue", RUNNING: "amber",
  COMPLETED: "green", REVIEWING: "blue", CLOSED: "green", FAILED: "red",
};
export const decisionTone = { auto_matched: "green", review: "amber", approved: "green", rejected: "slate", unresolved: "red" };

export function ConfidenceBar({ value, testId }) {
  const pct = Math.round((value || 0) * 100);
  const color = value >= 0.9 ? "bg-green-600" : value >= 0.6 ? "bg-amber-500" : "bg-red-600";
  return (
    <div className="flex items-center gap-2" data-testid={testId}>
      <div className="w-16 h-1.5 bg-slate-200 rounded-full overflow-hidden">
        <div className={`h-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="mono-num text-xs text-slate-600">{(value ?? 0).toFixed(2)}</span>
    </div>
  );
}

export function MetricCard({ label, value, sub, testId }) {
  return (
    <div className="card p-4 fade-up" data-testid={testId}>
      <div className="text-xs font-semibold tracking-[0.05em] uppercase text-slate-500">{label}</div>
      <div className="text-2xl font-semibold text-slate-950 tracking-tight mt-1 mono-num">{value}</div>
      {sub && <div className="text-xs text-slate-500 mt-1">{sub}</div>}
    </div>
  );
}

export function Section({ title, children, right, testId }) {
  return (
    <div className="card fade-up" data-testid={testId}>
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200">
        <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
        {right}
      </div>
      <div>{children}</div>
    </div>
  );
}

export function EmptyState({ title, hint, testId }) {
  return (
    <div className="py-12 text-center" data-testid={testId}>
      <div className="text-sm font-medium text-slate-700">{title}</div>
      {hint && <div className="text-xs text-slate-500 mt-1">{hint}</div>}
    </div>
  );
}

export function Skeleton({ className = "h-6 w-full" }) {
  return <div className={`skeleton ${className}`} />;
}

export function Modal({ open, onClose, title, children, testId }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-16 px-4" data-testid={testId}>
      <div className="absolute inset-0 bg-slate-950/40 backdrop-blur-sm" onClick={onClose} data-testid="modal-backdrop" />
      <div className="relative bg-white border border-slate-200 rounded-lg shadow-xl w-full max-w-2xl max-h-[80vh] overflow-auto fade-up">
        <div className="flex items-center justify-between px-5 py-3 border-b border-slate-200 sticky top-0 bg-white z-10">
          <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
          <button onClick={onClose} data-testid="modal-close-btn"
            className="text-slate-400 hover:text-slate-700 text-lg leading-none px-2">×</button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}
