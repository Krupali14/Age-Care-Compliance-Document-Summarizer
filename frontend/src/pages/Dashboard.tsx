import { useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { deleteDocument, listDocuments, uploadDocument, type DocumentSummary } from "../api/documents";
import ConfirmModal from "../components/ConfirmModal";

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-slate-100 text-slate-500",
  processing: "bg-amber-50 text-amber",
  done: "bg-sage-50 text-sage",
  failed: "bg-coral-50 text-coral",
  unsupported: "bg-amber-50 text-amber",
};

const STATUS_LABELS: Record<string, string> = {
  pending: "Queued",
  processing: "Reading",
  done: "Ready",
  failed: "Failed",
  unsupported: "Not supported",
};

function FileIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5 text-teal">
      <path d="M6 2h9l5 5v15a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M15 2v5h5" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  );
}

export default function Dashboard() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const fileInput = useRef<HTMLInputElement>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<DocumentSummary | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const { data: documents, isLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: listDocuments,
    refetchInterval: (query) => {
      const docs = query.state.data;
      const anyActive = docs?.some((d) => d.status === "pending" || d.status === "processing");
      return anyActive ? 4000 : false;
    },
  });

  async function handleUpload(file: File | undefined) {
    if (!file) return;
    setUploadError(null);
    try {
      await uploadDocument(file);
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    } catch (err) {
      // The API names the actual problem — wrong format, empty file, over the size
      // limit — and the user can only act on it if they are told which.
      setUploadError(err instanceof Error && err.message ? err.message : "Upload failed. Try again.");
    } finally {
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  async function handleDeleteConfirm() {
    if (!deleteTarget) return;
    setDeleteError(null);
    try {
      await deleteDocument(deleteTarget.id);
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    } catch (err) {
      setDeleteError(err instanceof Error && err.message ? err.message : "Could not delete this document.");
    } finally {
      setDeleteTarget(null);
    }
  }

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink">Documents</h1>
          <p className="mt-1 text-sm text-slate-500">Everything your team has uploaded, structured and ready to review.</p>
        </div>
        <label className="cursor-pointer rounded-md bg-ink px-4 py-2.5 text-sm font-semibold text-parchment shadow-card transition hover:-translate-y-0.5 hover:shadow-card-hover">
          Upload document
          <input ref={fileInput} type="file" accept=".pdf,.docx" className="hidden" onChange={(e) => handleUpload(e.target.files?.[0])} />
        </label>
      </div>
      {uploadError && <p className="mt-3 rounded-md bg-coral-50 px-3 py-2 text-sm text-coral">{uploadError}</p>}
      {deleteError && <p className="mt-3 rounded-md bg-coral-50 px-3 py-2 text-sm text-coral">{deleteError}</p>}

      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          handleUpload(e.dataTransfer.files?.[0]);
        }}
        className={`mt-6 rounded-xl border-2 border-dashed p-8 text-center transition ${
          dragOver ? "border-teal bg-teal-50" : "border-ink/10 bg-white/50"
        }`}
      >
        <p className="text-sm text-slate-500">
          Drag a PDF or DOCX here, or use <span className="font-medium text-ink">Upload document</span> above.
        </p>
      </div>

      <div className="mt-6">
        {isLoading && <p className="text-slate-500">Loading…</p>}
        {!isLoading && documents?.length === 0 && (
          <div className="rounded-xl border border-dashed border-ink/15 bg-white/50 p-12 text-center">
            <p className="font-display text-lg font-semibold text-ink">No documents yet</p>
            <p className="mt-1 text-sm text-slate-500">Upload your first compliance report to see it structured here.</p>
          </div>
        )}

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {documents?.map((doc, i) => (
            <div
              key={doc.id}
              style={{ animationDelay: `${i * 40}ms` }}
              className="group relative animate-fade-up cursor-pointer overflow-hidden rounded-xl border border-ink/10 bg-white p-5 shadow-card transition hover:-translate-y-1 hover:shadow-card-hover"
              onClick={() => navigate(`/dashboard/documents/${doc.id}`)}
            >
              {doc.status === "processing" && (
                <div className="absolute inset-x-0 top-0 h-0.5 overflow-hidden bg-amber-50">
                  <div className="h-full w-1/3 animate-shimmer bg-gradient-to-r from-transparent via-amber to-transparent bg-[length:200%_100%]" />
                </div>
              )}

              <div className="flex items-start justify-between">
                <FileIcon />
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setDeleteTarget(doc);
                  }}
                  aria-label={`Delete ${doc.filename}`}
                  className="rounded p-1 text-slate-400 opacity-0 transition hover:bg-coral-50 hover:text-coral group-hover:opacity-100"
                >
                  <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4"><path d="M6 7h12M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2m2 0-1 13a1 1 0 0 1-1 1H8a1 1 0 0 1-1-1L6 7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" /></svg>
                </button>
              </div>

              <p className="mt-3 truncate font-mono text-sm text-ink" title={doc.filename}>{doc.filename}</p>

              <span className={`mt-3 inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${STATUS_STYLES[doc.status]}`}>
                {doc.status === "processing" && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber" />}
                {STATUS_LABELS[doc.status]}
              </span>
            </div>
          ))}
        </div>
      </div>

      {deleteTarget && (
        <ConfirmModal
          title="Delete document"
          message={`Delete "${deleteTarget.filename}"? This can't be undone.`}
          confirmLabel="Delete"
          onConfirm={handleDeleteConfirm}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
    </div>
  );
}
