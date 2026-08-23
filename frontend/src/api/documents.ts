import { apiFetch } from "./client";

export interface DocumentSummary {
  id: number;
  filename: string;
  status: "pending" | "processing" | "done" | "failed";
  uploaded_at: string;
}

export async function listDocuments(): Promise<DocumentSummary[]> {
  const resp = await apiFetch("/api/documents");
  return resp.json();
}

export async function uploadDocument(file: File): Promise<DocumentSummary> {
  const form = new FormData();
  form.set("file", file);
  const resp = await apiFetch("/api/upload", { method: "POST", body: form });
  return resp.json();
}

export async function deleteDocument(id: number): Promise<void> {
  await apiFetch(`/api/documents/${id}`, { method: "DELETE" });
}
