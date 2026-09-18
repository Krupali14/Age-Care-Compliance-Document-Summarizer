import { apiFetch } from "./client";

export interface CheckSummary {
  id: number;
  filename: string;
  status: string;
  error_message: string | null;
  uploaded_at: string | null;
  incident_at: string | null;
  /** "stated" when the case study gave the incident time, "upload_time" when it did not. */
  incident_source: string | null;
  counts: Record<string, number>;
}

export interface CheckFinding {
  id: number;
  kind: string;
  section_id: number | null;
  requirement: string;
  verdict: string;
  evidence: string | null;
  note: string | null;
  due_at: string | null;
  bucket: string | null;
}

export interface CheckDetail extends CheckSummary {
  document_id: number;
  findings: CheckFinding[];
}

export async function listChecks(docId: number): Promise<CheckSummary[]> {
  return (await apiFetch(`/api/compliance-checks/${docId}`)).json();
}

export async function getCheck(checkId: number): Promise<CheckDetail> {
  return (await apiFetch(`/api/compliance-checks/item/${checkId}`)).json();
}

// The POST route only returns {id, filename, status} — the panel reads created.id
// off this and lets the checks list refetch pick up the rest.
export async function createCheck(docId: number, file: File): Promise<{ id: number; filename: string; status: string }> {
  const body = new FormData();
  body.append("file", file);
  // No Content-Type header: the browser sets the multipart boundary itself.
  return (await apiFetch(`/api/compliance-checks/${docId}`, { method: "POST", body })).json();
}

export async function deleteCheck(checkId: number): Promise<void> {
  await apiFetch(`/api/compliance-checks/item/${checkId}`, { method: "DELETE" });
}
