import { apiFetch } from "./client";

export interface EvalRun {
  id: number;
  precision: number;
  recall: number;
  f1: number;
  ground_truth_ref: string;
  created_at: string;
}

export async function getEvalRuns(docId: number): Promise<EvalRun[]> {
  return (await apiFetch(`/api/documents/${docId}/eval`)).json();
}

/** Score the document against itself — needs no ground-truth file. */
export async function runAutoEval(docId: number): Promise<EvalRun> {
  return (await apiFetch(`/api/documents/${docId}/eval/auto`, { method: "POST" })).json();
}
