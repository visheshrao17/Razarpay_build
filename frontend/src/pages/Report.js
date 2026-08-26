import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { toast } from "sonner";
import { runs, formatApiError } from "../api/client";
import { Section, Skeleton, Mono } from "../components/ui";
import { DownloadSimple, FileCsv, FileMd, FileText } from "@phosphor-icons/react";

function download(content, filename, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function Report() {
  const { runId } = useParams();
  const [report, setReport] = useState(null);
  const [markdown, setMarkdown] = useState(null);
  const [busy, setBusy] = useState("");

  useEffect(() => {
    runs.report(runId, "json").then((r) => setReport(r.data)).catch((e) => toast.error(formatApiError(e)));
    runs.report(runId, "markdown").then((r) => setMarkdown(r.data)).catch(() => setMarkdown(""));
  }, [runId]);

  const exportAs = async (format) => {
    setBusy(format);
    try {
      const { data } = await runs.report(runId, format);
      if (format === "json") download(JSON.stringify(data, null, 2), `${runId}_close_report.json`, "application/json");
      if (format === "markdown") download(data, `${runId}_close_report.md`, "text/markdown");
      if (format === "csv") download(data, `${runId}_close_report.csv`, "text/csv");
      toast.success(`Close report exported (${format})`);
    } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(""); }
  };

  return (
    <div className="space-y-6" data-testid="report-page">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-950">Close report</h1>
          <p className="text-sm text-slate-500 mt-1">
            Hash-signed, regenerable from database records. Unresolved exceptions remain visible after export.
          </p>
          {report && (
            <p className="text-xs text-slate-500 mt-1">
              Report hash <Mono className="text-blue-700">{report.report_hash}</Mono>
            </p>
          )}
        </div>
        <div className="flex gap-2">
          <button className="btn-secondary" onClick={() => exportAs("markdown")} disabled={busy === "markdown"}
            data-testid="export-markdown-btn"><FileMd size={16} /> Markdown</button>
          <button className="btn-secondary" onClick={() => exportAs("csv")} disabled={busy === "csv"}
            data-testid="export-csv-btn"><FileCsv size={16} /> CSV</button>
          <button className="btn-primary" onClick={() => exportAs("json")} disabled={busy === "json"}
            data-testid="export-json-btn"><DownloadSimple size={16} /> JSON</button>
        </div>
      </div>

      {report && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="card p-4"><div className="label !mb-0">Audit events covered</div>
            <div className="mono-num text-lg font-semibold mt-1">{report.audit_event_range?.count}</div>
            <div className="text-[11px] text-slate-500 mono-num">{report.audit_event_range?.first} → {report.audit_event_range?.last}</div></div>
          <div className="card p-4"><div className="label !mb-0">Matched records</div>
            <div className="mono-num text-lg font-semibold mt-1">{report.matched_records?.length}</div></div>
          <div className="card p-4"><div className="label !mb-0">Exceptions listed</div>
            <div className="mono-num text-lg font-semibold mt-1">{report.exceptions?.length}</div></div>
          <div className="card p-4"><div className="label !mb-0">Reviewer actions</div>
            <div className="mono-num text-lg font-semibold mt-1">{report.reviewer_actions?.length}</div></div>
        </div>
      )}

      <Section title="Report preview (Markdown)" testId="report-preview-section">
        {markdown === null ? (
          <div className="p-4 space-y-2"><Skeleton /><Skeleton /><Skeleton /></div>
        ) : (
          <pre className="p-5 text-xs mono-num text-slate-700 whitespace-pre-wrap max-h-[65vh] overflow-auto bg-slate-50 rounded-b-lg"
            data-testid="report-markdown-preview">{markdown || "Execute the run to generate a report."}</pre>
        )}
      </Section>
    </div>
  );
}
