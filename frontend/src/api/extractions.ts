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

export async function getDeadlines(id: number) {
  return (await apiFetch(`/api/deadlines/${id}`)).json();
}

export async function getActionItems(id: number) {
  return (await apiFetch(`/api/actions/${id}`)).json();
}
