import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { runs, formatApiError } from "../api/client";
import { Badge, statusTone, Money, Mono, Section, Skeleton, EmptyState } from "../components/ui";
import { Plus, Database, Play, ArrowRight } from "@phosphor-icons/react";

const AI_MODELS = ["gpt-5.4", "claude-sonnet-4-6", "gemini-3.1-pro-preview"];

export default function Runs() {
  const [list, setList] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("May 2026 settlement close");
  const [tolerance, setTolerance] = useState(100);
  const [window_, setWindow] = useState(2);
  const [autoThreshold, setAutoThreshold] = useState(0.9);
  const [aiModel, setAiModel] = useState("gpt-5.4");
  const [busy, setBusy] = useState("");
  const navigate = useNavigate();

  const refresh = () => runs.list().then((r) => setList(r.data)).catch((e) => toast.error(formatApiError(e)));
  useEffect(() => { refresh(); }, []);

  const createRun = async (e) => {
    e.preventDefault();
    setBusy("create");
    try {
      const { data } = await runs.create({
        name,
        config: {
          amount_tolerance_minor: Number(tolerance), date_window_days: Number(window_),
          auto_threshold: Number(autoThreshold), ai_model: aiModel,
        },
      });
      toast.success(`Run ${data.run_id} created`);
      setShowForm(false);
      refresh();
    } catch (err) { toast.error(formatApiError(err)); } finally { setBusy(""); }
  };

  const loadFixtures = async (runId) => {
    setBusy(`fixture-${runId}`);
    try {
      await runs.loadFixtures(runId);
      toast.success("Seeded fixture sources registered (settlements, bank, ledger, payments)");
      refresh();
    } catch (err) { toast.error(formatApiError(err)); } finally { setBusy(""); }
  };

  const execute = async (runId) => {
    setBusy(`exec-${runId}`);
    try {
      const { data } = await runs.execute(runId);
      toast.success(`Reconciliation completed — match rate ${(data.summary_metrics.overall_match_rate * 100).toFixed(1)}%`);
      navigate(`/runs/${runId}`);
    } catch (err) { toast.error(formatApiError(err)); } finally { setBusy(""); }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-950">Reconciliation runs</h1>
          <p className="text-sm text-slate-500 mt-1">
            Create a run, register the three sources, then execute deterministic matching.
          </p>
        </div>
        <button className="btn-primary" onClick={() => setShowForm(!showForm)} data-testid="new-run-btn">
          <Plus size={16} /> New run
        </button>
      </div>

      {showForm && (
        <Section title="Run setup" testId="run-setup-section">
          <form onSubmit={createRun} className="p-4 grid grid-cols-1 md:grid-cols-5 gap-4 items-end">
            <div className="md:col-span-2">
              <label className="label">Run name</label>
              <input className="input" value={name} onChange={(e) => setName(e.target.value)}
                required data-testid="run-name-input" />
            </div>
            <div>
              <label className="label">Amount tolerance (paise)</label>
              <input className="input mono-num" type="number" min="0" value={tolerance}
                onChange={(e) => setTolerance(e.target.value)} data-testid="run-tolerance-input" />
            </div>
            <div>
              <label className="label">Date window (days)</label>
              <input className="input mono-num" type="number" min="0" value={window_}
                onChange={(e) => setWindow(e.target.value)} data-testid="run-window-input" />
            </div>
            <div>
              <label className="label">Auto-match threshold</label>
              <input className="input mono-num" type="number" step="0.01" min="0.5" max="1" value={autoThreshold}
                onChange={(e) => setAutoThreshold(e.target.value)} data-testid="run-threshold-input" />
            </div>
            <div>
              <label className="label">AI model (explanations)</label>
              <select className="input" value={aiModel} onChange={(e) => setAiModel(e.target.value)}
                data-testid="run-ai-model-select">
                {AI_MODELS.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
            <div className="md:col-span-4 text-xs text-slate-500">
              Tolerances and thresholds are visible demo assumptions (v1.0), stored on the run and shown in the report.
              Records below the review threshold are never force-matched.
            </div>
            <button className="btn-primary justify-center" disabled={busy === "create"} data-testid="create-run-submit-btn">
              {busy === "create" ? "Creating…" : "Create run"}
            </button>
          </form>
        </Section>
      )}

      <Section title={`Runs ${list ? `(${list.length})` : ""}`} testId="runs-list-section">
        {!list ? (
          <div className="p-4 space-y-2"><Skeleton /><Skeleton /><Skeleton /></div>
        ) : list.length === 0 ? (
          <EmptyState title="No runs yet." hint="Create a run, then load the seeded fixture to see a full reconciliation in under a second." testId="runs-empty-state" />
        ) : (
          <div className="overflow-x-auto">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Run</th><th>Name</th><th>Status</th><th>Sources</th>
                  <th className="text-right">Match rate</th><th className="text-right">Precision</th>
                  <th className="text-right">Unresolved</th><th></th>
                </tr>
              </thead>
              <tbody>
                {list.map((r) => {
                  const m = r.summary_metrics;
                  const ready = r.status === "READY";
                  const done = ["COMPLETED", "REVIEWING", "CLOSED"].includes(r.status);
                  return (
                    <tr key={r.run_id} data-testid={`run-row-${r.run_id}`}>
                      <td><Mono>{r.run_id}</Mono></td>
                      <td className="max-w-[220px] truncate">{r.name}</td>
                      <td><Badge tone={statusTone[r.status]} testId={`run-status-${r.run_id}`}>{r.status}</Badge></td>
                      <td>
                        <div className="flex gap-1 flex-wrap">
                          {r.sources.map((s) => (
                            <span key={s.source_id} className="text-[11px] bg-slate-100 border border-slate-200 rounded px-1.5 py-0.5 mono-num">
                              {s.source_type} {s.valid_rows}✓{s.invalid_rows > 0 ? ` ${s.invalid_rows}✗` : ""}
                            </span>
                          ))}
                          {r.sources.length === 0 && <span className="text-xs text-slate-400">none</span>}
                        </div>
                      </td>
                      <td className="text-right mono-num">{m ? `${(m.overall_match_rate * 100).toFixed(1)}%` : "—"}</td>
                      <td className="text-right mono-num">{m?.auto_match_precision != null ? m.auto_match_precision.toFixed(2) : "—"}</td>
                      <td className="text-right"><Money minor={m?.unresolved_amount_minor} /></td>
                      <td>
                        <div className="flex gap-2 justify-end">
                          {!done && r.sources.length === 0 && (
                            <button className="btn-secondary !py-1 !px-2.5 text-xs" disabled={busy === `fixture-${r.run_id}`}
                              onClick={() => loadFixtures(r.run_id)} data-testid={`load-fixture-btn-${r.run_id}`}>
                              <Database size={14} /> Load demo fixture
                            </button>
                          )}
                          {ready && (
                            <button className="btn-primary !py-1 !px-2.5 text-xs" disabled={busy === `exec-${r.run_id}`}
                              onClick={() => execute(r.run_id)} data-testid={`execute-run-btn-${r.run_id}`}>
                              <Play size={14} /> {busy === `exec-${r.run_id}` ? "Running…" : "Execute"}
                            </button>
                          )}
                          {done && (
                            <Link to={`/runs/${r.run_id}`} className="btn-secondary !py-1 !px-2.5 text-xs"
                              data-testid={`open-run-btn-${r.run_id}`}>
                              Open <ArrowRight size={14} />
                            </Link>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Section>
    </div>
  );
}
