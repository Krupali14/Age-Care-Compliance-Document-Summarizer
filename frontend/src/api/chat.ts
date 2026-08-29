import { apiFetch } from "./client";

export interface ChatSource {
  id: number;
  heading: string;
}

export interface ChatResponse {
  answer: string;
  sources: ChatSource[];
}

export async function askQuestion(docId: number, question: string): Promise<ChatResponse> {
  const resp = await apiFetch(`/api/chat/${docId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  return resp.json();
}
