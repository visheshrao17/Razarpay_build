import React, { useCallback, useEffect, useState, useRef } from "react";
import { useParams, useSearchParams, Link } from "react-router-dom";
import { toast } from "sonner";
import { runs, exceptions as excApi, formatApiError } from "../api/client";
import { Badge, severityTone, statusTone, ConfidenceBar, Money, Mono, Section, Skeleton, EmptyState, Modal } from "../components/ui";
import { Sparkle, Lightning } from "@phosphor-icons/react";

const CODES = ["", "MISSING_BANK_ENTRY", "MISSING_ORDER", "AMOUNT_MISMATCH", "FEE_VARIANCE",
  "TAX_VARIANCE", "DUPLICATE", "TIMING_DIFFERENCE", "PARTIAL_REFUND", "DISPUTE_ADJUSTMENT",
  "AMBIGUOUS_MATCH", "IDENTIFIER_CONFLICT", "INVALID_SOURCE", "UNEXPECTED_ADJUSTMENT"];
const STATUSES = ["", "OPEN", "IN_REVIEW", "RESOLVED", "REJECTED", "UNRESOLVED"];
const SEVERITIES = ["", "critical", "high", "medium", "low"];
const ACTIONS = ["approve_match", "reject_match", "split_match", "request_data", "leave_unresolved"];
const AI_MODELS = ["openrouter", "gpt-5.4", "claude-sonnet-4-6", "gemini-3.1-pro-preview"];

function ExceptionDetail({ exceptionId, onClose, onChanged }) {
  const [detail, setDetail] = useState(null);
  const [action, setAction] = useState("approve_match");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState("");
  const [aiModel, setAiModel] = useState("openrouter");
  const { runId } = useParams();

  const autoExplainTriggered = useRef(false);
  const load = useCallback(() => {
    excApi.detail(exceptionId).then((r) => {
      setDetail(r.data);
      // Auto-trigger AI explanation if not yet generated
      if (!autoExplainTriggered.current && !r.data.exception.ai_explanation) {
        autoExplainTriggered.current = true;
        setBusy("explain");
        excApi.explain(exceptionId, "openrouter")
          .then(() => {
            excApi.detail(exceptionId).then((r2) => setDetail(r2.data));
            toast.success("AI explanation auto-generated");
          })
          .catch((e) => toast.error("AI explain failed: " + formatApiError(e)))
          .finally(() => setBusy(""));
      }
    }).catch((e) => toast.error(formatApiError(e)));
  }, [exceptionId]);
  useEffect(() => { load(); }, [load]);

  const resolve = async () => {
    if (!note.trim()) { toast.error("A reviewer note is required for the audit log"); return; }
    setBusy("resolve");
    try {
      const { data } = await excApi.resolve(exceptionId, { action, note });
      toast.success(`${data.previous_status} → ${data.new_status} (audit ${data.audit_event_id})`);
      onChanged();
      load();
    } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(""); }
  };

  const explain = async () => {
    setBusy("explain");
    try {
      await excApi.explain(exceptionId, aiModel);
      toast.success("AI explanation generated and validated");
      load();
    } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(""); }
  };

  if (!detail) return <Skeleton className="h-40" />;
  const e = detail.exception;
  const ai = e.ai_explanation;

  return (
    <div className="space-y-4" data-testid="exception-detail">
      <div className="flex items-center gap-2 flex-wrap">
        <Badge tone={severityTone[e.severity]} testId="exception-detail-code">{e.exception_code}</Badge>
        <Badge tone={statusTone[e.status]} testId="exception-detail-status">{e.status}</Badge>
        <span className="text-xs text-slate-500">recommended: {e.recommended_action}</span>
        <span className="ml-auto"><Money minor={e.amount_at_risk_minor} className="text-sm font-semibold" /></span>
      </div>
      <p className="text-sm text-slate-700 leading-relaxed" data-testid="exception-detail-explanation">{e.explanation}</p>
      <div className="text-xs text-slate-500">
        Records: {e.record_ids.map((r) => <Mono key={r} className="mr-2 text-blue-700">{r}</Mono>)}
      </div>
      {e.match_id && (
        <Link to={`/runs/${runId}/matches/${e.match_id}`} className="text-xs text-blue-700 hover:underline"
          data-testid="exception-goto-match">View linked match {e.match_id} →</Link>
      )}

      {detail.records.length > 0 && (
        <div className="border border-slate-200 rounded-md overflow-auto max-h-56">
          <table className="tbl">
            <thead><tr><th>Record</th><th>Type</th><th>Key fields</th><th className="text-right">Amount</th></tr></thead>
            <tbody>
              {detail.records.map((r) => (
                <tr key={r.source_record_id}>
                  <td><Mono>{r.source_record_id}</Mono></td>
                  <td className="text-xs">{r.source_type}</td>
                  <td className="text-xs text-slate-500 max-w-[260px] truncate">
                    {r.narration || r.payment_id || r.razorpay_payment_id || r.internal_order_id || r.utr || "—"}
                  </td>
                  <td className="text-right">
                    <Money minor={r.net_amount_minor ?? r.credit_amount_minor ?? r.gross_amount_minor} className="text-xs" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className={`border rounded-lg p-4 ${ai && !ai._fallback ? 'bg-gradient-to-br from-blue-50 to-indigo-50 border-blue-200' : 'bg-blue-50 border-blue-100'}`} data-testid="ai-explanation-panel">
        <div className="flex items-center justify-between gap-2 mb-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-blue-800 flex items-center gap-1">
            <Sparkle size={14} weight="fill" /> {ai && !ai._fallback ? '🤖 LLM Analysis' : 'AI explanation (evidence-grounded)'}
          </span>
          <div className="flex items-center gap-2">
            <select className="input !w-52 !py-1 text-xs" value={aiModel} onChange={(ev) => setAiModel(ev.target.value)}
              data-testid="ai-model-select">
              {AI_MODELS.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
            <button className="btn-primary !py-1 !px-3 text-xs" onClick={explain} disabled={busy === "explain"}
              data-testid="generate-ai-explanation-btn">
              {busy === "explain" ? "Analyzing…" : ai ? "Regenerate" : "Explain"}
            </button>
          </div>
        </div>
        {ai ? (
          <div className="space-y-3 text-sm">
            <div className={`p-3 rounded-md ${ai._fallback ? 'bg-slate-100' : 'bg-white/70 border border-blue-100'}`}>
              <p className="text-slate-800 leading-relaxed" data-testid="ai-summary">{ai.summary}</p>
            </div>
            <div className="flex items-center gap-3 flex-wrap text-xs">
              {ai.abstain && <Badge tone="amber" testId="ai-abstain-badge">ABSTAINED</Badge>}
              {ai._fallback ? (
                <Badge tone="slate" testId="ai-fallback-badge">⚠ deterministic fallback (no LLM)</Badge>
              ) : (
                <Badge tone="emerald" testId="ai-llm-badge">✓ LLM-generated</Badge>
              )}
              <span className="text-slate-500">confidence <span className="mono-num font-bold">{Number(ai.confidence).toFixed(2)}</span></span>
              <span className="text-slate-500">action: <strong>{ai.recommended_action}</strong></span>
              {ai._model && <span className="text-blue-600 font-medium">model: {ai._model}</span>}
              {ai._prompt_version && <span className="text-slate-400">prompt: {ai._prompt_version}</span>}
            </div>
            {ai.possible_causes?.length > 0 && (
              <div className="text-xs text-slate-600">
                <span className="font-semibold">Possible causes:</span> {ai.possible_causes.map((c, i) => (
                  <span key={c} className="inline-block bg-amber-50 border border-amber-200 rounded px-1.5 py-0.5 mr-1 mt-1">{c.replace(/_/g, ' ')}</span>
                ))}
              </div>
            )}
            {ai.evidence_fields?.length > 0 && (
              <div className="text-xs text-slate-600">
                <span className="font-semibold">Evidence fields:</span> {ai.evidence_fields.join(", ")}
              </div>
            )}
            <div className="text-xs text-slate-500">
              <span className="font-semibold">Cited records:</span> {(ai.evidence_ids || []).map((r) => <Mono key={r} className="mr-2 text-blue-700">{r}</Mono>)}
            </div>
            {ai.unsupported_claims?.length > 0 && (
              <div className="text-xs text-red-600">
                <span className="font-semibold">⚠ Unsupported claims:</span> {ai.unsupported_claims.join(", ")}
              </div>
            )}
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <div className="animate-pulse flex items-center gap-2 text-xs text-blue-600">
              <Sparkle size={14} className="animate-spin" /> Auto-generating AI explanation…
            </div>
          </div>
        )}
      </div>

      <div className="border-t border-slate-200 pt-4">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">Human review</div>
        {e.status === "RESOLVED" || e.status === "REJECTED" ? (
          <div className="text-sm text-slate-600" data-testid="exception-resolved-info">
            {e.resolution_action} by <b>{e.resolved_by}</b> — “{e.resolution_note}”
          </div>
        ) : (
          <div className="flex gap-2 flex-wrap items-start">
            <select className="input !w-44" value={action} onChange={(ev) => setAction(ev.target.value)}
              data-testid="resolve-action-select">
              {ACTIONS.map((a) => <option key={a} value={a}>{a}</option>)}
            </select>
            <input className="input flex-1 min-w-[220px]" placeholder="Reviewer note (required, audited)"
              value={note} onChange={(ev) => setNote(ev.target.value)} data-testid="resolve-note-input" />
            <button className="btn-primary" onClick={resolve} disabled={busy === "resolve"}
              data-testid="resolve-submit-btn">
              {busy === "resolve" ? "Recording…" : "Record decision"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function Exceptions() {
  const { runId } = useParams();
  const [params] = useSearchParams();
  const [data, setData] = useState(null);
  const [code, setCode] = useState("");
  const [status, setStatus] = useState("");
  const [severity, setSeverity] = useState("");
  const [focus, setFocus] = useState(params.get("focus") || null);

  const load = useCallback(() => {
    runs.exceptions(runId, { code: code || undefined, status: status || undefined, severity: severity || undefined })
      .then((r) => setData(r.data)).catch((e) => toast.error(formatApiError(e)));
  }, [runId, code, status, severity]);
  useEffect(() => { load(); }, [load]);

  return (
    <div className="space-y-6" data-testid="exceptions-page">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-950">Exception queue</h1>
          <p className="text-sm text-slate-500 mt-1">Sorted by severity, then amount at risk. Every action is logged to the append-only audit trail.</p>
        </div>
        <div className="flex gap-3 flex-wrap">
          <select className="input !w-52" value={code} onChange={(e) => setCode(e.target.value)} data-testid="exceptions-code-filter">
            {CODES.map((c) => <option key={c} value={c}>{c || "All codes"}</option>)}
          </select>
          <select className="input !w-36" value={severity} onChange={(e) => setSeverity(e.target.value)} data-testid="exceptions-severity-filter">
            {SEVERITIES.map((s) => <option key={s} value={s}>{s || "All severities"}</option>)}
          </select>
          <select className="input !w-40" value={status} onChange={(e) => setStatus(e.target.value)} data-testid="exceptions-status-filter">
            {STATUSES.map((s) => <option key={s} value={s}>{s || "All statuses"}</option>)}
          </select>
        </div>
      </div>

      <Section title={`Exceptions ${data ? `(${data.total})` : ""}`} testId="exceptions-table-section">
        {!data ? (
          <div className="p-4 space-y-2"><Skeleton /><Skeleton /><Skeleton /></div>
        ) : data.exceptions.length === 0 ? (
          <EmptyState title="No exceptions in this view." hint="All records for this filter have been matched or resolved." testId="exceptions-empty" />
        ) : (
          <div className="overflow-x-auto max-h-[65vh] overflow-y-auto">
            <table className="tbl">
              <thead>
                <tr><th>Exception</th><th>Code</th><th>Severity</th><th>Status</th>
                  <th className="text-right">Amount at risk</th><th>Confidence</th><th>Records</th><th></th></tr>
              </thead>
              <tbody>
                {data.exceptions.map((e) => (
                  <tr key={e.exception_id} data-testid={`exception-row-${e.exception_id}`}>
                    <td><Mono>{e.exception_id}</Mono></td>
                    <td><Badge tone={severityTone[e.severity]}>{e.exception_code}</Badge></td>
                    <td className="text-xs capitalize">{e.severity}</td>
                    <td><Badge tone={statusTone[e.status]}>{e.status}</Badge></td>
                    <td className="text-right"><Money minor={e.amount_at_risk_minor} /></td>
                    <td><ConfidenceBar value={e.confidence} /></td>
                    <td className="text-xs text-slate-500 max-w-[200px] truncate">{e.record_ids.join(", ")}</td>
                    <td>
                      <button className="btn-secondary !py-1 !px-2.5 text-xs" onClick={() => setFocus(e.exception_id)}
                        data-testid={`review-exception-btn-${e.exception_id}`}>
                        Review
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      <Modal open={!!focus} onClose={() => setFocus(null)} title={`Review ${focus || ""}`} testId="exception-modal">
        {focus && <ExceptionDetail exceptionId={focus} onClose={() => setFocus(null)} onChanged={load} />}
      </Modal>
    </div>
  );
}
