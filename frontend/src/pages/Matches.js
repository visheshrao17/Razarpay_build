import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { toast } from "sonner";
import { runs, formatApiError } from "../api/client";
import { Badge, decisionTone, ConfidenceBar, Mono, Section, Skeleton, EmptyState } from "../components/ui";

const PLANES = ["", "order_settlement", "settlement_bank", "refund"];
const DECISIONS = ["", "auto_matched", "review", "approved", "rejected"];

export default function Matches() {
  const { runId } = useParams();
  const [data, setData] = useState(null);
  const [plane, setPlane] = useState("");
  const [decision, setDecision] = useState("");

  useEffect(() => {
    setData(null);
    runs.matches(runId, { plane: plane || undefined, decision: decision || undefined, limit: 300 })
      .then((r) => setData(r.data))
      .catch((e) => toast.error(formatApiError(e)));
  }, [runId, plane, decision]);

  return (
    <div className="space-y-6" data-testid="matches-page">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-950">Match decisions</h1>
          <p className="text-sm text-slate-500 mt-1">Every decision carries evidence, a confidence score and a rules version.</p>
        </div>
        <div className="flex gap-3">
          <select className="input !w-44" value={plane} onChange={(e) => setPlane(e.target.value)} data-testid="matches-plane-filter">
            {PLANES.map((p) => <option key={p} value={p}>{p || "All planes"}</option>)}
          </select>
          <select className="input !w-40" value={decision} onChange={(e) => setDecision(e.target.value)} data-testid="matches-decision-filter">
            {DECISIONS.map((d) => <option key={d} value={d}>{d || "All decisions"}</option>)}
          </select>
        </div>
      </div>
      <Section title={`Matches ${data ? `(${data.total})` : ""}`} testId="matches-table-section">
        {!data ? (
          <div className="p-4 space-y-2"><Skeleton /><Skeleton /><Skeleton /></div>
        ) : data.matches.length === 0 ? (
          <EmptyState title="No matches for this filter." hint="Adjust filters or execute the run." testId="matches-empty" />
        ) : (
          <div className="overflow-x-auto max-h-[65vh] overflow-y-auto">
            <table className="tbl">
              <thead>
                <tr><th>Match</th><th>Plane</th><th>Type</th><th>Decision</th><th>Confidence</th>
                  <th>Source A</th><th>Source B</th><th>Reviewer</th></tr>
              </thead>
              <tbody>
                {data.matches.map((m) => (
                  <tr key={m.match_id} data-testid={`match-row-${m.match_id}`}>
                    <td>
                      <Link to={`/runs/${runId}/matches/${m.match_id}`}
                        className="text-blue-700 hover:underline mono-num text-[13px]"
                        data-testid={`match-link-${m.match_id}`}>
                        {m.match_id}
                      </Link>
                    </td>
                    <td className="text-xs">{m.plane}</td>
                    <td className="text-xs">{m.match_type}</td>
                    <td><Badge tone={decisionTone[m.decision]}>{m.decision}</Badge></td>
                    <td><ConfidenceBar value={m.confidence} /></td>
                    <td><Mono>{m.source_a_ids.slice(0, 2).join(", ")}{m.source_a_ids.length > 2 ? ` +${m.source_a_ids.length - 2}` : ""}</Mono></td>
                    <td><Mono>{m.source_b_ids.slice(0, 2).join(", ")}{m.source_b_ids.length > 2 ? ` +${m.source_b_ids.length - 2}` : ""}</Mono></td>
                    <td className="text-xs text-slate-500">{m.reviewer_id || "—"}</td>
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
