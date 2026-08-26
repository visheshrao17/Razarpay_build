import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";
import { formatApiError } from "../api/client";
import { Scales } from "@phosphor-icons/react";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("operator@settlesense.dev");
  const [password, setPassword] = useState("operator123");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      <div className="hidden lg:flex flex-col justify-between bg-slate-950 text-white p-12">
        <div className="flex items-center gap-2">
          <span className="w-8 h-8 rounded bg-blue-700 flex items-center justify-center">
            <Scales size={18} weight="bold" />
          </span>
          <span className="font-semibold tracking-tight text-lg">SettleSense</span>
        </div>
        <div>
          <h1 className="text-4xl font-semibold tracking-tight leading-tight max-w-lg">
            Every rupee, explained.<br />Every uncertainty, surfaced.
          </h1>
          <p className="text-slate-400 mt-4 max-w-md text-sm leading-relaxed">
            SettleSense reconciles Razorpay settlements, bank credits and internal orders —
            and refuses to force-match unexplained differences.
          </p>
          <div className="mt-8 grid grid-cols-3 gap-4 max-w-md">
            <div><div className="mono-num text-2xl font-semibold">260+</div><div className="text-xs text-slate-400 mt-1">records per run</div></div>
            <div><div className="mono-num text-2xl font-semibold">100%</div><div className="text-xs text-slate-400 mt-1">decisions with evidence</div></div>
            <div><div className="mono-num text-2xl font-semibold">0</div><div className="text-xs text-slate-400 mt-1">forced matches</div></div>
          </div>
        </div>
        <p className="text-[11px] text-slate-500">
          Synthetic and Razorpay Test Mode data only. Not tax, legal or accounting advice.
        </p>
      </div>
      <div className="flex items-center justify-center p-8">
        <form onSubmit={submit} className="w-full max-w-sm fade-up" data-testid="login-form">
          <h2 className="text-2xl font-semibold tracking-tight text-slate-950">Sign in</h2>
          <p className="text-sm text-slate-500 mt-1 mb-6">Demo accounts are pre-filled.</p>
          <label className="label">Email</label>
          <input className="input mb-4" type="email" value={email} data-testid="login-email-input"
            onChange={(e) => setEmail(e.target.value)} autoComplete="username" />
          <label className="label">Password</label>
          <input className="input mb-4" type="password" value={password} data-testid="login-password-input"
            onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
          {error && <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2 mb-4" data-testid="login-error">{error}</div>}
          <button className="btn-primary w-full justify-center" disabled={busy} data-testid="login-submit-btn">
            {busy ? "Signing in…" : "Sign in"}
          </button>
          <div className="mt-6 text-xs text-slate-500 space-y-1 border-t border-slate-200 pt-4">
            <div>Operator: <span className="mono-num">operator@settlesense.dev / operator123</span></div>
            <div>Reviewer: <span className="mono-num">reviewer@settlesense.dev / reviewer123</span></div>
          </div>
        </form>
      </div>
    </div>
  );
}
