import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { toast } from "sonner";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { runs, formatApiError } from "../api/client";
import { MetricCard, Money, Section, Skeleton, Badge, statusTone, Mono } from "../components/ui";
import { Sparkle, Lightning } from "@phosphor-icons/react";

const SEV_COLORS = { critical: "#b91c1c", high: "#dc2626", medium: "#d97706", low: "#64748b" };
const CODE_COLOR = "#1d4ed8";

export default function RunSummary() {
  const { runId } = useParams();
  const [summary, setSummary] = useState(null);
  const [evaluation, setEvaluation] = useState(null);

  const [aiBusy, setAiBusy] = useState(false);

  const loadSummary = () => {
    runs.summary(runId).then((r) => setSummary(r.data)).catch((e) => toast.error(formatApiError(e)));
  };

  useEffect(() => {
    loadSummary();
    runs.evaluation(runId).then((r) => setEvaluation(r.data)).catch(() => setEvaluation(false));
  }, [runId]);

  const generateAiSummary = async () => {
    setAiBusy(true);
    try {
      await runs.generateAiSummary(runId);
      toast.success("AI run summary generated");
      loadSummary();
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setAiBusy(false);
    }
  };

  if (!summary) return <div className="space-y-4"><Skeleton className="h-24" /><Skeleton className="h-64" /></div>;
  const m = summary.summary_metrics;
  if (!m)
    return (
      <div className="card p-8 text-center" data-testid="run-not-executed">
        <p className="text-sm text-slate-600">This run has not been executed yet.</p>
        <Link to="/" className="btn-primary mt-4 inline-flex">Back to runs</Link>
      </div>
    );

  const codeData = Object.entries(m.exception_counts || {}).map(([code, count]) => ({ code, count }))
    .sort((a, b) => b.count - a.count);
  const cfg = summary.config || {};

  return (
    <div className="space-y-6" data-testid="run-summary-page">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-semibold tracking-tight text-slate-950">Run summary</h1>
            <Badge tone={statusTone[summary.status]} testId="summary-run-status">{summary.status}</Badge>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            <Mono>{runId}</Mono> · rules {m.rules_version} · assumptions {m.assumptions_version}
            {m.dataset_version ? <> · dataset <Mono>{m.dataset_version}</Mono></> : null}
          </p>
        </div>
        <div className="text-xs text-slate-500 text-right">
          Tolerances used: <span className="mono-num">±{cfg.amount_tolerance_minor} paise</span>, window{" "}
          <span className="mono-num">{cfg.date_window_days}d</span>, auto ≥ <span className="mono-num">{cfg.auto_threshold}</span>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Records processed" value={m.records_processed}
          sub={`${m.throughput_records_per_second?.toLocaleString()} rec/s · ${m.elapsed_seconds}s`}
          testId="metric-records-processed" />
        <MetricCard label="Overall match rate" value={`${(m.overall_match_rate * 100).toFixed(1)}%`}
          sub={`${m.auto_matched_records}/${m.eligible_records} eligible records auto-matched`}
          testId="metric-match-rate" />
        <MetricCard label="Auto-match precision" value={m.auto_match_precision != null ? m.auto_match_precision.toFixed(2) : "n/a"}
          sub={m.auto_match_recall != null
            ? <span data-testid="metric-recall">recall {m.auto_match_recall.toFixed(2)} on independent ground truth</span>
            : "no ground truth"}
          testId="metric-precision" />
        <MetricCard label="Forced matches" value={m.forced_match_count}
          sub="target: zero — ambiguity goes to review" testId="metric-forced-matches" />
        <MetricCard label="Gross order value" value={<Money minor={m.gross_amount_minor} />} testId="metric-gross" />
        <MetricCard label="Matched amount" value={<Money minor={m.matched_amount_minor} />} testId="metric-matched-amount" />
        <MetricCard label="Unresolved amount" value={<Money minor={m.unresolved_amount_minor} />}
          sub={`${m.exception_count} exceptions · ${m.duplicate_records} duplicates excluded`}
          testId="metric-unresolved-amount" />
        <MetricCard label="Review queue" value={m.review_records}
          sub={`review rate ${(m.review_rate * 100).toFixed(1)}% · ${m.invalid_rows} invalid rows reported`}
          testId="metric-review-queue" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <Section title="Exceptions by category" testId="exceptions-chart-section"
            right={<Link to={`/runs/${runId}/exceptions`} className="text-xs text-blue-700 hover:underline" data-testid="goto-exceptions-link">Open queue →</Link>}>
            <div className="p-4 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={codeData} layout="vertical" margin={{ left: 60 }}>
                  <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="code" width={140} tick={{ fontSize: 10, fontFamily: "IBM Plex Mono" }} />
                  <Tooltip cursor={{ fill: "#f1f5f9" }} />
                  <Bar dataKey="count" radius={[0, 3, 3, 0]}>
                    {codeData.map((d) => <Cell key={d.code} fill={CODE_COLOR} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Section>
        </div>
        <div className="space-y-6">
          <Section title="Exception status" testId="exception-status-section">
            <div className="p-4 space-y-2">
              {Object.entries(summary.exception_status_counts).map(([s, c]) => (
                <div key={s} className="flex items-center justify-between text-sm">
                  <Badge tone={statusTone[s]}>{s}</Badge>
                  <span className="mono-num">{c}</span>
                </div>
              ))}
              <div className="flex items-center justify-between text-sm border-t border-slate-200 pt-2 mt-2">
                <span className="text-slate-500 text-xs uppercase tracking-wide font-semibold">Open amount at risk</span>
                <Money minor={summary.open_exception_amount_minor} />
              </div>
            </div>
          </Section>
          <Section title="Severity" testId="exception-severity-section">
            <div className="p-4 space-y-2">
              {Object.entries(summary.exception_severity_counts).map(([s, c]) => (
                <div key={s} className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full" style={{ background: SEV_COLORS[s] }} />
                    <span className="capitalize">{s}</span>
                  </span>
                  <span className="mono-num">{c}</span>
                </div>
              ))}
            </div>
          </Section>
        </div>
      </div>

      <Section title="AI run insights (evidence-grounded)" testId="ai-summary-section">
        <div className={`p-5 rounded-b-lg ${summary.ai_summary && !summary.ai_summary._fallback ? 'bg-gradient-to-br from-blue-50 to-indigo-50 border-t border-blue-200' : 'bg-slate-50 border-t border-slate-200'}`}>
          {!summary.ai_summary ? (
            <div className="flex flex-col items-center justify-center py-6 text-center space-y-3">
              <Sparkle size={32} className="text-slate-400" />
              <p className="text-sm text-slate-500 max-w-md">
                Generate an LLM-powered executive summary of this run's health, key findings, root causes, and actionable recommendations.
              </p>
              <button className="btn-primary" onClick={generateAiSummary} disabled={aiBusy}>
                {aiBusy ? "Analyzing run..." : "Generate AI Insights"}
              </button>
            </div>
          ) : (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wide text-blue-800 flex items-center gap-1">
                  <Sparkle size={14} weight="fill" /> {summary.ai_summary._fallback ? 'Deterministic Fallback' : '🤖 LLM Analysis'}
                </span>
                <div className="flex gap-2 items-center text-xs text-slate-500">
                  {summary.ai_summary._model && <span>model: {summary.ai_summary._model}</span>}
                  <button className="text-blue-600 hover:underline disabled:opacity-50" onClick={generateAiSummary} disabled={aiBusy}>
                    {aiBusy ? "Regenerating..." : "Regenerate"}
                  </button>
                </div>
              </div>

              <div className="space-y-4 text-sm text-slate-800">
                <div>
                  <h4 className="font-semibold text-slate-900 mb-1">Overall Assessment</h4>
                  <p className="leading-relaxed bg-white/70 p-3 rounded border border-blue-100">{summary.ai_summary.overall_assessment}</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <h4 className="font-semibold text-slate-900 mb-2">Key Findings</h4>
                    <ul className="list-disc pl-5 space-y-1">
                      {summary.ai_summary.key_findings?.map((f, i) => <li key={i}>{f}</li>)}
                    </ul>
                  </div>
                  
                  <div>
                    <h4 className="font-semibold text-slate-900 mb-2">Recommendations</h4>
                    <ul className="list-disc pl-5 space-y-1">
                      {summary.ai_summary.recommendations?.map((r, i) => <li key={i}>{r}</li>)}
                    </ul>
                  </div>
                </div>

                {summary.ai_summary.common_root_causes?.length > 0 && (
                  <div>
                    <h4 className="font-semibold text-slate-900 mb-2">Common Root Causes</h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                      {summary.ai_summary.common_root_causes.map((c, i) => (
                        <div key={i} className="bg-white/70 border border-amber-100 p-3 rounded-md shadow-sm">
                          <div className="flex justify-between items-start mb-1">
                            <span className="font-medium text-amber-900 capitalize text-xs">{c.cause}</span>
                            <Badge tone="amber" className="!text-[10px]">{c.count}</Badge>
                          </div>
                          <p className="text-xs text-slate-600 mt-1">{c.description}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                <div className="flex items-center gap-4 text-xs pt-2 border-t border-blue-100/50">
                  {summary.ai_summary.risk_analysis && (
                    <span className="flex items-center gap-1 text-rose-700">
                      <strong>Risk:</strong> {summary.ai_summary.risk_analysis}
                    </span>
                  )}
                  {summary.ai_summary.data_quality_notes && (
                    <span className="flex items-center gap-1 text-amber-700">
                      <strong>Data Quality:</strong> {summary.ai_summary.data_quality_notes}
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </Section>

      <Section title="Baseline comparison — same dataset, three matcher configurations (independent ground truth)"
        testId="baseline-section">
        {evaluation === null ? (
          <div className="p-4"><Skeleton /></div>
        ) : evaluation === false ? (
          <div className="p-4 text-sm text-slate-500">Baseline evaluation requires the seeded fixture.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="tbl">
              <thead>
                <tr><th>Matcher</th><th className="text-right">Precision</th><th className="text-right">Recall</th>
                  <th className="text-right">Auto matches</th><th className="text-right">Match rate</th>
                  <th className="text-right">Exceptions</th><th className="text-right">Forced</th></tr>
              </thead>
              <tbody>
                {Object.entries(evaluation.baselines).map(([name, b]) => (
                  <tr key={name} data-testid={`baseline-row-${name}`}>
                    <td className="font-medium">{name.replaceAll("_", " ")}</td>
                    <td className="text-right mono-num">{b.auto_match_precision?.toFixed(4)}</td>
                    <td className="text-right mono-num">{b.auto_match_recall?.toFixed(4)}</td>
                    <td className="text-right mono-num">{b.auto_matches}</td>
                    <td className="text-right mono-num">{(b.overall_match_rate * 100).toFixed(2)}%</td>
                    <td className="text-right mono-num">{b.exception_count}</td>
                    <td className="text-right mono-num">{b.forced_match_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>
    </div>
  );
}
