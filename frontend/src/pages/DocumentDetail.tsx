import { useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import {
  getDocument, getSummaries, getObligations, getRisks, getDeadlines, getActionItems,
} from "../api/extractions";
import CategoryTable from "../components/CategoryTable";

const STATUS_MESSAGES: Record<string, string> = {
  pending: "This document is still being processed. Extraction results will appear here once complete.",
  processing: "This document is still being processed. Extraction results will appear here once complete.",
};

export default function DocumentDetail() {
  const { id } = useParams();
  const docId = Number(id);

  const { data: document } = useQuery({ queryKey: ["document", docId], queryFn: () => getDocument(docId) });
  const { data: summaries } = useQuery({ queryKey: ["summaries", docId], queryFn: () => getSummaries(docId), enabled: !!document });
  const { data: obligations } = useQuery({ queryKey: ["obligations", docId], queryFn: () => getObligations(docId), enabled: !!document });
  const { data: risks } = useQuery({ queryKey: ["risks", docId], queryFn: () => getRisks(docId), enabled: !!document });
  const { data: deadlines } = useQuery({ queryKey: ["deadlines", docId], queryFn: () => getDeadlines(docId), enabled: !!document });
  const { data: actions } = useQuery({ queryKey: ["actions", docId], queryFn: () => getActionItems(docId), enabled: !!document });

  const TABS = [
    { key: "Summary", count: undefined },
    { key: "Obligations", count: obligations?.length },
    { key: "Risks", count: risks?.length },
    { key: "Deadlines", count: deadlines?.length },
    { key: "Actions", count: actions?.length },
    { key: "Sections", count: document?.sections.length },
  ] as const;

  const [tab, setTab] = useState<(typeof TABS)[number]["key"]>("Summary");
  const [highlightedSectionId, setHighlightedSectionId] = useState<number | null>(null);
  const sectionRefs = useRef<Record<number, HTMLDivElement | null>>({});

  function jumpToSection(sectionId: number) {
    setTab("Sections");
    setHighlightedSectionId(sectionId);
    setTimeout(() => sectionRefs.current[sectionId]?.scrollIntoView({ behavior: "smooth", block: "start" }), 0);
    setTimeout(() => setHighlightedSectionId(null), 1500);
  }

  const statusMessage = document && document.status !== "done" ? STATUS_MESSAGES[document.status] : undefined;

  if (!document) {
    return <p className="p-6 text-slate-500">Loading…</p>;
  }

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-mono text-xs text-slate-400">
            <Link to="/dashboard" className="hover:text-teal">Documents</Link> / {document.filename}
          </p>
          <h1 className="mt-0.5 font-display text-xl font-semibold text-ink">{document.filename}</h1>
        </div>
      </div>

      {statusMessage && <p className="mt-3 rounded-md bg-amber-50 px-4 py-2 text-sm text-amber">{statusMessage}</p>}
      {document.status === "failed" && (
        <p className="mt-3 rounded-md bg-coral-50 px-4 py-2 text-sm text-coral">
          Processing failed{document.error_message ? `: ${document.error_message}` : "."}
        </p>
      )}

      <div className="mt-4 flex gap-1 overflow-x-auto border-b border-ink/10">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`relative flex items-center gap-1.5 whitespace-nowrap px-3.5 py-2.5 text-sm font-medium transition ${
              tab === t.key ? "text-ink" : "text-slate-400 hover:text-ink"
            }`}
          >
            {t.key}
            {t.count !== undefined && (
              <span className={`rounded-full px-1.5 py-0.5 font-mono text-[10px] ${tab === t.key ? "bg-teal-50 text-teal-600" : "bg-parchment-200 text-slate-400"}`}>
                {String(t.count).padStart(2, "0")}
              </span>
            )}
            {tab === t.key && <span className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-teal transition-all" />}
          </button>
        ))}
      </div>

      <div className="mt-4 overflow-hidden rounded-xl border border-ink/10 bg-white shadow-card">
        {tab === "Summary" && (
          <div className="space-y-3 p-6">
            {(summaries ?? []).map((s: { id: number; text: string }) => (
              <p key={s.id} className="leading-relaxed text-slate-600">{s.text}</p>
            ))}
            {summaries?.length === 0 && <p className="text-slate-500">No summary yet.</p>}
          </div>
        )}
        {tab === "Obligations" && <CategoryTable rows={obligations ?? []} sections={document.sections} onSectionClick={jumpToSection} />}
        {tab === "Risks" && <CategoryTable rows={risks ?? []} sections={document.sections} onSectionClick={jumpToSection} />}
        {tab === "Deadlines" && (
          <CategoryTable
            rows={(deadlines ?? []).map((d: { id: number; description: string; section_id: number; responsible_role: string | null; due_date: string | null }) => ({ id: d.id, text: d.description, section_id: d.section_id, responsible_role: d.responsible_role, extra: d.due_date }))}
            sections={document.sections}
            onSectionClick={jumpToSection}
          />
        )}
        {tab === "Actions" && (
          <CategoryTable
            rows={(actions ?? []).map((a: { id: number; text: string; section_id: number; responsible_role: string | null; priority: string | null; timeframe: string | null }) => ({ ...a, extra: a.timeframe }))}
            sections={document.sections}
            onSectionClick={jumpToSection}
          />
        )}
        {tab === "Sections" && (
          <div className="divide-y divide-ink/5 bg-parchment-100">
            {document.sections.length === 0 && <p className="p-10 text-center text-sm text-slate-500">No sections extracted yet.</p>}
            {document.sections.map((s) => (
              <div
                key={s.id}
                ref={(el) => { sectionRefs.current[s.id] = el; }}
                className={`p-6 transition-colors duration-500 ${highlightedSectionId === s.id ? "bg-teal-50" : ""}`}
              >
                <div className="flex items-center gap-2">
                  <span className="rounded bg-ink px-1.5 py-0.5 font-mono text-[10px] text-parchment">{s.order_idx + 1}</span>
                  <h3 className="font-display text-base font-semibold text-ink">{s.heading}</h3>
                </div>
                <div className="mt-2 space-y-2 text-sm leading-relaxed text-slate-600 [&_strong]:font-semibold [&_strong]:text-ink [&_ul]:list-disc [&_ul]:pl-5">
                  <ReactMarkdown>{s.raw_text}</ReactMarkdown>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
