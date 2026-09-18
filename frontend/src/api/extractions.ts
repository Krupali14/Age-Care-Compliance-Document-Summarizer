import { apiFetch } from "./client";

export interface DocumentDetailData {
  id: number;
  filename: string;
  status: string;
  error_message: string | null;
  sections: { id: number; heading: string; order_idx: number; page_ref: string | null; raw_text: string }[];
}

export async function getDocument(id: number): Promise<DocumentDetailData> {
  return (await apiFetch(`/api/documents/${id}`)).json();
}

export async function getSummaries(id: number) {
  return (await apiFetch(`/api/summarize/${id}`)).json();
}

export async function getObligations(id: number) {
  return (await apiFetch(`/api/obligations/${id}`)).json();
}

export async function getRisks(id: number) {
  return (await apiFetch(`/api/risks/${id}`)).json();
}

export interface Deadline {
  id: number;
  section_id: number;
  description: string;
  /** The wording the document used: an ISO date, or a timeframe like "within 4 hours". */
  due_date: string | null;
  /** That wording resolved to a moment in time, relative timeframes counted from upload. */
  due_at: string | null;
  bucket: string;
  status: string;
  responsible_role: string | null;
}

export async function getDeadlines(id: number): Promise<Deadline[]> {
  return (await apiFetch(`/api/deadlines/${id}`)).json();
}

export async function updateDeadlineStatus(deadlineId: number, status: string) {
  return (
    await apiFetch(`/api/deadlines/item/${deadlineId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    })
  ).json();
}

export async function getActionItems(id: number) {
  return (await apiFetch(`/api/actions/${id}`)).json();
}
