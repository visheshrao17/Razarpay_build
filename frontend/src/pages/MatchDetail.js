import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { toast } from "sonner";
import { runs, formatApiError } from "../api/client";
import { Badge, decisionTone, severityTone, statusTone, ConfidenceBar, Money, Mono, Section, Skeleton } from "../components/ui";

function RecordCard({ rec, highlight }) {
  const labels = {
    settlement: ["Settlement line", "border-blue-200"],
    internal_ledger: ["Internal order", "border-green-200"],
    bank_statement: ["Bank entry", "border-amber-200"],
  };
  const [label, border] = labels[rec.source_type] || ["Record", "border-slate-200"];
  const fields = Object.entries(rec).filter(([k]) => !["source_type", "raw"].includes(k));
  return (
    <div className={`card !border-2 ${border} p-3`} data-testid={`record-card-${rec.source_record_id}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</span>
        <Mono className="text-blue-700">{rec.source_record_id}</Mono>
      </div>
      <dl className="space-y-1">
        {fields.map(([k, v]) => (
          <div key={k} className={`flex justify-between gap-3 text-xs px-1 rounded ${highlight?.includes(k) ? "bg-green-50" : ""}`}>
            <dt className="text-slate-500">{k}</dt>
            <dd className="text-slate-800 text-right">
              {k.endsWith("_minor") ? <Money minor={v} className="text-xs" /> : <Mono className="text-xs">{v === null || v === "" ? "—" : String(v)}</Mono>}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function Waterfall({ records }) {
  const line = records.find((r) => r.source_type === "settlement" && !r.adjustment_type);
  if (!line) return null;
  const steps = [
    { label: "Gross", value: line.gross_amount_minor },
    { label: "− Fee", value: -(line.fee_minor || 0) },
    { label: "− Tax", value: -(line.tax_minor || 0) },
    { label: "= Net", value: line.net_amount_minor },
  ];
  return (
    <div className="flex items-stretch gap-2 flex-wrap" data-testid="amount-waterfall">
      {steps.map((s, i) => (
        <div key={s.label} className={`flex-1 min-w-[110px] rounded-md border p-3 ${i === steps.length - 1 ? "border-blue-300 bg-blue-50" : "border-slate-200 bg-white"}`}>
          <div className="text-[11px] uppercase tracking-wide text-slate-500 font-semibold">{s.label}</div>
          <div className="mt-1"><Money minor={s.value} className="text-sm font-semibold" /></div>
        </div>
      ))}
    </div>
  );
}

export default function MatchDetail() {
  const { runId, matchId } = useParams();
  const [data, setData] = useState(null);

  useEffect(() => {
    runs.matchDetail(runId, matchId).then((r) => setData(r.data)).catch((e) => toast.error(formatApiError(e)));
  }, [runId, matchId]);

  if (!data) return <div className="space-y-4"><Skeleton className="h-24" /><Skeleton className="h-64" /></div>;
  const { match, records, exceptions, audit_events } = data;
  const aRecords = records.filter((r) => match.source_a_ids.includes(r.source_record_id));
  const bRecords = records.filter((r) => match.source_b_ids.includes(r.source_record_id) && !match.source_a_ids.includes(r.source_record_id));
  const matchedFields = match.evidence?.matched_on ? [match.evidence.matched_on, "gross_amount_minor"] : [];

  return (
    <div className="space-y-6" data-testid="match-detail-page">
      <div>
        <Link to={`/runs/${runId}/matches`} className="text-xs text-blue-700 hover:underline" data-testid="back-to-matches-link">← All matches</Link>
        <div className="flex items-center gap-3 mt-1 flex-wrap">
          <h1 className="text-3xl font-semibold tracking-tight text-slate-950 mono-num">{matchId}</h1>
          <Badge tone={decisionTone[match.decision]} testId="match-decision-badge">{match.decision}</Badge>
          <Badge tone="blue">{match.plane}</Badge>
          <Badge tone="slate">{match.match_type}</Badge>
        </div>
        <div className="flex items-center gap-4 mt-2">
          <ConfidenceBar value={match.confidence} testId="match-confidence" />
          <span className="text-xs text-slate-500">rules {match.rules_version}</span>
          {match.reviewer_id && <span className="text-xs text-slate-500">reviewed by {match.reviewer_id}</span>}
        </div>
      </div>

      <Section title="Amount waterfall" testId="waterfall-section">
        <div className="p-4"><Waterfall records={records} />
          {!records.some((r) => r.source_type === "settlement" && !r.adjustment_type) && (
            <p className="text-xs text-slate-500">Waterfall applies to settlement payment lines. See evidence below for aggregate amounts.</p>)}
        </div>
      </Section>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Section title={`Side A (${aRecords.length})`} testId="side-a-section">
          <div className="p-3 space-y-3 max-h-[50vh] overflow-auto">
            {aRecords.map((r) => <RecordCard key={r.source_record_id} rec={r} highlight={matchedFields} />)}
          </div>
        </Section>
        <Section title={`Side B (${bRecords.length})`} testId="side-b-section">
          <div className="p-3 space-y-3 max-h-[50vh] overflow-auto">
            {bRecords.map((r) => <RecordCard key={r.source_record_id} rec={r} highlight={matchedFields} />)}
          </div>
        </Section>
      </div>

      <Section title="Match evidence" testId="evidence-section">
        <pre className="p-4 text-xs mono-num text-slate-700 overflow-auto max-h-72 bg-slate-50 rounded-b-lg">
          {JSON.stringify(match.evidence, null, 2)}
        </pre>
      </Section>

      {exceptions.length > 0 && (
        <Section title="Linked exceptions" testId="linked-exceptions-section">
          <div className="p-4 space-y-2">
            {exceptions.map((e) => (
              <div key={e.exception_id} className="flex items-center justify-between text-sm border border-slate-200 rounded-md px-3 py-2">
                <div className="flex items-center gap-2">
                  <Badge tone={severityTone[e.severity]}>{e.exception_code}</Badge>
                  <Badge tone={statusTone[e.status]}>{e.status}</Badge>
                  <span className="text-xs text-slate-600 max-w-xl truncate">{e.explanation}</span>
                </div>
                <Link className="text-xs text-blue-700 hover:underline whitespace-nowrap"
                  to={`/runs/${runId}/exceptions?focus=${e.exception_id}`}
                  data-testid={`goto-exception-${e.exception_id}`}>
                  Review →
                </Link>
              </div>
            ))}
          </div>
        </Section>
      )}

      <Section title="Audit trail for this match" testId="match-audit-section">
        <div className="p-4 space-y-0">
          {audit_events.map((a) => (
            <div key={a.audit_event_id} className="relative pl-5 pb-4 border-l border-slate-200 last:pb-0">
              <span className="absolute -left-[5px] top-1 w-2.5 h-2.5 rounded-full bg-blue-700" />
              <div className="text-xs text-slate-500 mono-num">{a.timestamp}</div>
              <div className="text-sm text-slate-800"><b>{a.actor}</b> · {a.step} · {a.decision}</div>
              <div className="text-xs text-slate-600">{a.outcome}</div>
              <div className="text-[10px] text-slate-400 mono-num mt-0.5">hash {a.event_hash?.slice(0, 20)}…</div>
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
}
