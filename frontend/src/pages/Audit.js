import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { toast } from "sonner";
import { runs, formatApiError } from "../api/client";
import { Badge, Mono, Section, Skeleton, EmptyState } from "../components/ui";

const ACTOR_TONE = { system: "slate", matcher: "blue", ai: "amber", reviewer: "green" };
const ACTORS = ["", "system", "matcher", "ai", "reviewer"];

export default function Audit() {
  const { runId } = useParams();
  const [data, setData] = useState(null);
  const [actor, setActor] = useState("");

  useEffect(() => {
    setData(null);
    runs.audit(runId, { actor: actor || undefined, limit: 400 })
      .then((r) => setData(r.data)).catch((e) => toast.error(formatApiError(e)));
  }, [runId, actor]);

  return (
    <div className="space-y-6" data-testid="audit-page">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-950">Audit timeline</h1>
          <p className="text-sm text-slate-500 mt-1">
            Append-only, hash-chained. Corrections create new events; nothing is deleted.
          </p>
        </div>
        <select className="input !w-40" value={actor} onChange={(e) => setActor(e.target.value)} data-testid="audit-actor-filter">
          {ACTORS.map((a) => <option key={a} value={a}>{a || "All actors"}</option>)}
        </select>
      </div>
      <Section title={`Events ${data ? `(${data.total})` : ""}`} testId="audit-timeline-section">
        {!data ? (
          <div className="p-4 space-y-2"><Skeleton /><Skeleton /><Skeleton /></div>
        ) : data.events.length === 0 ? (
          <EmptyState title="No audit events." hint="Execute the run to populate the trail." testId="audit-empty" />
        ) : (
          <div className="p-5 max-h-[70vh] overflow-auto">
            {data.events.map((a) => (
              <div key={a.audit_event_id} className="relative pl-6 pb-5 border-l border-slate-200 last:pb-0"
                data-testid={`audit-event-${a.audit_event_id}`}>
                <span className={`absolute -left-[6px] top-1 w-3 h-3 rounded-full border-2 border-white ${
                  a.actor === "reviewer" ? "bg-green-600" : a.actor === "ai" ? "bg-amber-500" :
                  a.actor === "matcher" ? "bg-blue-700" : "bg-slate-400"}`} />
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge tone={ACTOR_TONE[a.actor]}>{a.actor}</Badge>
                  <span className="text-sm font-medium text-slate-800">{a.step}</span>
                  {a.decision && <span className="text-xs text-slate-500">· {a.decision}</span>}
                  {a.human_gate && <Badge tone="green">human gate</Badge>}
                  {a.confidence != null && <span className="text-xs mono-num text-slate-500">conf {a.confidence}</span>}
                  <span className="text-xs text-slate-400 mono-num ml-auto">{a.timestamp}</span>
                </div>
                <div className="text-sm text-slate-600 mt-0.5">{a.outcome}</div>
                <div className="text-[11px] text-slate-400 mt-0.5 flex gap-3 flex-wrap">
                  {a.match_id && <span>match <Mono className="!text-[11px]">{a.match_id}</Mono></span>}
                  {a.exception_id && <span>exception <Mono className="!text-[11px]">{a.exception_id}</Mono></span>}
                  {a.source_record_ids?.length > 0 && <span>records <Mono className="!text-[11px]">{a.source_record_ids.slice(0, 4).join(", ")}</Mono></span>}
                  {a.model_version !== "none" && <span>model {a.model_version}</span>}
                  <span className="mono-num">hash {a.event_hash?.slice(0, 16)}… ← {a.previous_event_hash?.slice(0, 12)}…</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </Section>
    </div>
  );
}
