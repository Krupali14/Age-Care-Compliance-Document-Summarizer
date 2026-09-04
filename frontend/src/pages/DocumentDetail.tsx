import { useEffect, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import {
  getDocument, getSummaries, getObligations, getRisks, getDeadlines, getActionItems,
} from "../api/extractions";
import CategoryTable from "../components/CategoryTable";
import AIAssistant from "../components/AIAssistant";
import NotFound from "./NotFound";

// Section summaries come back as Markdown bullets with **bold** key terms, so the
// duty, role, and date in each line are scannable rather than buried in prose.
function SummaryMarkdown({ text }: { text: string }) {
  return (
    <div className="text-[15px] leading-relaxed text-slate-600">
      <ReactMarkdown
        components={{
          ul: ({ children }) => <ul className="space-y-2">{children}</ul>,
          li: ({ children }) => (
            <li className="relative pl-5 before:absolute before:left-0 before:top-[0.6em] before:h-1.5 before:w-1.5 before:rounded-full before:bg-teal">
              {children}
            </li>
          ),
          ol: ({ children }) => <ol className="list-decimal space-y-2 pl-5">{children}</ol>,
          strong: ({ children }) => <strong className="font-semibold text-ink">{children}</strong>,
          em: ({ children }) => <em className="italic text-slate-500">{children}</em>,
          code: ({ children }) => (
            <code className="rounded bg-ink/5 px-1 py-0.5 font-mono text-[13px] text-ink">{children}</code>
          ),
          a: ({ href, children }) => (
            <a href={href} className="font-medium text-teal underline underline-offset-2">{children}</a>
          ),
          h1: ({ children }) => <p className="font-semibold text-ink">{children}</p>,
          h2: ({ children }) => <p className="font-semibold text-ink">{children}</p>,
          h3: ({ children }) => <p className="font-semibold text-ink">{children}</p>,
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-teal/40 pl-3 text-slate-500">{children}</blockquote>
          ),
          p: ({ children }) => <p className="leading-relaxed">{children}</p>,
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}

const STATUS_MESSAGES: Record<string, string> = {
  pending: "This document is still being processed. Extraction results will appear here once complete.",
  processing: "This document is still being processed. Extraction results will appear here once complete.",
};

function useIsDesktop() {
  const [isDesktop, setIsDesktop] = useState(() => window.matchMedia("(min-width: 1024px)").matches);
  useEffect(() => {
    const mql = window.matchMedia("(min-width: 1024px)");
    const handler = () => setIsDesktop(mql.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, []);
  return isDesktop;
}

export default function DocumentDetail() {
  const { id } = useParams();
  const docId = Number(id);
  const isDesktop = useIsDesktop();

  const { data: document, isError: documentMissing } = useQuery({
    queryKey: ["document", docId],
    queryFn: () => getDocument(docId),
    // A document that 404s will 404 again; retrying only prolongs "Loading…".
    retry: false,
  });
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
  const [aiOpen, setAiOpen] = useState(isDesktop);
  const [focusMode, setFocusMode] = useState(false);
  const [docWidthPct, setDocWidthPct] = useState(68);
  const sectionRefs = useRef<Record<number, HTMLDivElement | null>>({});
  const workspaceRef = useRef<HTMLDivElement>(null);
  const dragging = useRef(false);

  function jumpToSection(sectionId: number) {
    setTab("Sections");
    setHighlightedSectionId(sectionId);
    setTimeout(() => sectionRefs.current[sectionId]?.scrollIntoView({ behavior: "smooth", block: "start" }), 0);
    setTimeout(() => setHighlightedSectionId(null), 1500);
  }

  function startDrag(e: React.MouseEvent) {
    e.preventDefault();
    dragging.current = true;
    window.document.body.style.cursor = "col-resize";

    function onMove(ev: MouseEvent) {
      if (!dragging.current || !workspaceRef.current) return;
      const rect = workspaceRef.current.getBoundingClientRect();
      const pct = ((ev.clientX - rect.left) / rect.width) * 100;
      setDocWidthPct(Math.min(80, Math.max(50, pct)));
    }
    function onUp() {
      dragging.current = false;
      window.document.body.style.cursor = "";
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    }
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }

  const statusMessage = document && document.status !== "done" ? STATUS_MESSAGES[document.status] : undefined;
  // Nothing was extracted, so there is nothing for the assistant to cite. Offering
  // it anyway just produces a failed request.
  const canAssist = !!document && document.sections.length > 0;
  const showSplit = isDesktop && aiOpen && !focusMode && canAssist;

  const documentContent = documentMissing ? (
    <NotFound
      title="Document not found"
      message="This document doesn't exist, or it belongs to another account."
    />
  ) : !document ? (
    <p className="p-6 text-slate-500">Loading…</p>
  ) : (
    <>
      {!focusMode && (
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="font-mono text-xs text-slate-400">
              <Link to="/dashboard" className="hover:text-teal">Documents</Link> / {document.filename}
            </p>
            <h1 className="mt-0.5 font-display text-xl font-semibold text-ink">{document.filename}</h1>
          </div>
          <div className="flex items-center gap-2">
            <Link
              to={`/dashboard/documents/${docId}/eval`}
              className="rounded-md border border-ink/15 px-3 py-1.5 text-xs font-medium text-ink transition hover:bg-white"
            >
              Evaluation results
            </Link>
            <button
              onClick={() => setFocusMode(true)}
              title="Focus mode"
              className="rounded-md border border-ink/15 p-1.5 text-ink transition hover:bg-white"
            >
              <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4"><path d="M8 3H5a2 2 0 0 0-2 2v3M16 3h3a2 2 0 0 1 2 2v3M8 21H5a2 2 0 0 1-2-2v-3M16 21h3a2 2 0 0 0 2-2v-3" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></svg>
            </button>
          </div>
        </div>
      )}

      {focusMode && (
        <button
          onClick={() => setFocusMode(false)}
          className="mb-2 flex items-center gap-1.5 rounded-md border border-ink/15 px-3 py-1.5 text-xs font-medium text-ink transition hover:bg-white"
        >
          <svg viewBox="0 0 24 24" fill="none" className="h-3.5 w-3.5"><path d="M15 3h3a2 2 0 0 1 2 2v3M9 21H6a2 2 0 0 1-2-2v-3M21 9V6a2 2 0 0 0-2-2h-3M3 15v3a2 2 0 0 0 2 2h3" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></svg>
          Exit focus mode
        </button>
      )}

      {/* {!focusMode && (
        <div className="mt-3 flex items-start gap-2 rounded-md border border-amber/20 bg-amber-50 px-3.5 py-2 text-xs text-amber">
          <span className="mt-0.5 shrink-0">⚠</span>
          AI-generated. Verify against the original document before acting on this information.
        </div>
      )} */}

      {statusMessage && <p className="mt-3 rounded-md bg-amber-50 px-4 py-2 text-sm text-amber">{statusMessage}</p>}
      {document.status === "unsupported" && (
        <div className="mt-3 flex items-start gap-2.5 rounded-md border border-amber/30 bg-amber-50 px-4 py-3 text-sm text-amber">
          <span className="mt-0.5 shrink-0">⚠</span>
          <span>
            <strong className="font-semibold">This document can&rsquo;t be summarised.</strong>{" "}
            {document.error_message ?? "It doesn't look like an aged-care compliance document."} No
            obligations, risks or deadlines were extracted. Upload a compliance, policy or
            regulatory document instead.
          </span>
        </div>
      )}
      {document.status === "failed" && (
        <p className="mt-3 rounded-md bg-coral-50 px-4 py-2 text-sm text-coral">
          {document.error_message ?? "This document could not be processed."}
        </p>
      )}

      {document.status !== "unsupported" && (
      <>
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
          <div className="space-y-4 p-6">
            {(summaries ?? []).map((s: { id: number; text: string }) => (
              <SummaryMarkdown key={s.id} text={s.text} />
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
      </>
      )}
    </>
  );

  return (
    <div className="relative">
      <div ref={workspaceRef} className="flex flex-col lg:flex-row">
        <div style={showSplit ? { width: `${docWidthPct}%` } : undefined} className={showSplit ? "pr-6" : "w-full"}>
          {documentContent}
        </div>

        {showSplit && (
          <div
            onMouseDown={startDrag}
            className="group relative hidden w-1 shrink-0 cursor-col-resize lg:block"
          >
            <div className="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-ink/10 transition group-hover:w-1 group-hover:bg-teal" />
          </div>
        )}

        {showSplit && (
          <div style={{ width: `${100 - docWidthPct}%` }} className="hidden shrink-0 lg:block">
            <div className="sticky top-[4.5rem] h-[calc(100vh-6.5rem)] overflow-hidden rounded-xl border border-ink/10 shadow-card-hover">
              <AIAssistant docId={docId} onSourceClick={jumpToSection} onCollapse={() => setAiOpen(false)} />
            </div>
          </div>
        )}
      </div>

      {/* Reopen affordance: desktop collapsed panel, or focus mode */}
      {(!showSplit && isDesktop && canAssist) && (
        <button
          onClick={() => { setAiOpen(true); setFocusMode(false); }}
          className="fixed bottom-6 right-6 z-30 flex items-center gap-2 rounded-full bg-ink px-4 py-3 text-sm font-medium text-parchment shadow-stack transition hover:-translate-y-0.5 hover:shadow-xl"
        >
          <span className="h-2 w-2 animate-pulse rounded-full bg-teal" />
          Ask AI
        </button>
      )}

      {/* Mobile: floating trigger + bottom-sheet drawer */}
      {!isDesktop && canAssist && (
        <>
          <button
            onClick={() => setAiOpen(true)}
            className="fixed bottom-5 right-5 z-30 flex items-center gap-2 rounded-full bg-ink px-4 py-3 text-sm font-medium text-parchment shadow-stack"
          >
            <span className="h-2 w-2 animate-pulse rounded-full bg-teal" />
            Ask AI
          </button>
          {aiOpen && (
            <>
              <div className="fixed inset-0 z-40 bg-ink/40" onClick={() => setAiOpen(false)} />
              <div className="fixed inset-x-0 bottom-0 z-50 h-[75vh] animate-fade-up overflow-hidden rounded-t-2xl shadow-stack" style={{ animationDuration: "0.25s" }}>
                <AIAssistant docId={docId} onSourceClick={(id) => { jumpToSection(id); setAiOpen(false); }} onCollapse={() => setAiOpen(false)} />
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
