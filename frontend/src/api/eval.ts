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
