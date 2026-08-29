import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getEvalRuns } from "../api/eval";

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
  const { data: runs } = useQuery({ queryKey: ["eval", docId], queryFn: () => getEvalRuns(docId) });

  return (
    <div>
      <p className="font-mono text-xs uppercase tracking-wider text-slate-400">Accuracy</p>
      <h1 className="mt-0.5 font-display text-2xl font-semibold text-ink">Evaluation results</h1>

      {(runs ?? []).length === 0 && (
        <div className="mt-6 rounded-xl border border-dashed border-ink/15 bg-white/50 p-10 text-center">
          <p className="text-sm text-slate-500">
            No eval runs yet — run <code className="rounded bg-ink/5 px-1.5 py-0.5 font-mono text-xs">scripts/eval.py</code> against this document.
          </p>
        </div>
      )}

      <div className="mt-6 space-y-3">
        {(runs ?? []).map((r) => (
          <div key={r.id} className="rounded-xl border border-ink/10 bg-white p-6 shadow-card">
            <p className="font-mono text-xs text-slate-400">{r.ground_truth_ref}</p>
            <div className="mt-3 grid grid-cols-3 gap-4">
              <Metric label="Precision" value={r.precision} />
              <Metric label="Recall" value={r.recall} />
              <Metric label="F1" value={r.f1} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
