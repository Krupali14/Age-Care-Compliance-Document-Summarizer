import { useEffect, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getEvalRuns, runAutoEval, EvalRun } from "../api/eval";
import { getDocument } from "../api/extractions";

const AUTO_REF = "auto";

// An automatic run and a ground-truth run measure different things, so they are
// never labelled the same way. Calling a self-check "precision" would imply the
// answers had been compared against something they weren't.
const LABELS: Record<string, { a: string; b: string; c: string; note: string }> = {
  [AUTO_REF]: {
    a: "Grounding",
    b: "Coverage",
    c: "Overall",
    note: "Scored against the document itself. Grounding is the share of findings whose wording is carried by the section they cite — the check against invented content. Coverage is the share of readable sections that produced a finding; sections of definitions legitimately produce none.",
  },
  default: {
    a: "Precision",
    b: "Recall",
    c: "F1",
    note: "Scored against a hand-annotated ground-truth file.",
  },
};

function Metric({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100);
  const tone = pct >= 80 ? "text-sage" : pct >= 50 ? "text-amber" : "text-coral";
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
      <p className={`mt-1 font-display text-3xl font-semibold ${tone}`}>{pct}%</p>
    </div>
  );
}

export default function EvalPage() {
  const { id } = useParams();
  const docId = Number(id);
  const queryClient = useQueryClient();

  const { data: doc } = useQuery({ queryKey: ["document", docId], queryFn: () => getDocument(docId) });
  const { data: runs, isLoading } = useQuery({ queryKey: ["eval", docId], queryFn: () => getEvalRuns(docId) });

  const evaluate = useMutation({
    mutationFn: () => runAutoEval(docId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["eval", docId] }),
  });

  // Evaluate once, the first time this document's results are opened. The ref stops
  // a re-render — or the refetch this mutation triggers — from firing it again.
  const started = useRef(false);
  const { mutate } = evaluate;
  useEffect(() => {
    if (started.current || isLoading || !runs || !doc) return;
    if (runs.length > 0 || doc.status !== "done") return;
    started.current = true;
    mutate();
  }, [runs, isLoading, doc, mutate]);

  const canEvaluate = doc?.status === "done";
  const hasRuns = (runs ?? []).length > 0;

  return (
    <div>
      <p className="font-mono text-xs text-slate-400">
        <Link to={`/dashboard/documents/${docId}`} className="hover:text-teal">Document</Link> / Evaluation
      </p>
      <div className="mt-0.5 flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-2xl font-semibold text-ink">Evaluation results</h1>
        <button
          onClick={() => mutate()}
          disabled={evaluate.isPending || !canEvaluate}
          className="rounded-md border border-ink/15 px-3 py-1.5 text-xs font-medium text-ink transition hover:bg-white disabled:opacity-40"
        >
          {evaluate.isPending ? "Evaluating…" : hasRuns ? "Re-evaluate" : "Evaluate"}
        </button>
      </div>

      {doc && !canEvaluate && (
        <p className="mt-4 rounded-md bg-amber-50 px-4 py-2 text-sm text-amber">
          {doc.status === "failed"
            ? "This document could not be processed, so there is nothing to evaluate."
            : doc.status === "unsupported"
              ? "This document isn't compliance material, so there is nothing to evaluate."
              : "Evaluation runs once processing has finished."}
        </p>
      )}

      {evaluate.isError && (
        <p className="mt-4 rounded-md bg-coral-50 px-4 py-2 text-sm text-coral">
          Evaluation failed: {(evaluate.error as Error).message}
        </p>
      )}

      {evaluate.isPending && !hasRuns && <p className="mt-6 text-sm text-slate-500">Scoring this document…</p>}

      {!evaluate.isPending && !hasRuns && canEvaluate && (
        <p className="mt-6 text-sm text-slate-500">No evaluation yet.</p>
      )}

      <div className="mt-6 space-y-3">
        {(runs ?? []).map((r: EvalRun, i: number) => {
          const labels = LABELS[r.ground_truth_ref] ?? LABELS.default;
          return (
            <div key={r.id} className="rounded-xl border border-ink/10 bg-white p-6 shadow-card">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-mono text-xs text-slate-400">
                  {r.ground_truth_ref === AUTO_REF ? "Automatic self-check" : r.ground_truth_ref}
                  {i === 0 && (
                    <span className="ml-2 rounded-full bg-teal-50 px-2 py-0.5 text-teal-600">latest</span>
                  )}
                </p>
                <p className="font-mono text-xs text-slate-400">{new Date(r.created_at).toLocaleString()}</p>
              </div>
              <div className="mt-3 grid grid-cols-3 gap-4">
                <Metric label={labels.a} value={r.precision} />
                <Metric label={labels.b} value={r.recall} />
                <Metric label={labels.c} value={r.f1} />
              </div>
              {i === 0 && <p className="mt-4 text-xs leading-relaxed text-slate-500">{labels.note}</p>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
