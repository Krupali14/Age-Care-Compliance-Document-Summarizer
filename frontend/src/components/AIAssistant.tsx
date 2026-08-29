import { useState } from "react";
import { askQuestion, type ChatSource } from "../api/chat";

interface Message {
  role: "user" | "assistant";
  text: string;
  sources?: ChatSource[];
}

const SUGGESTED_QUESTIONS = [
  "What are the key compliance obligations?",
  "What are the major risks?",
  "What deadlines are mentioned?",
  "What actions are required?",
  "Summarize the incident.",
];

function SparkIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className}>
      <path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M18 6l-2.5 2.5M8.5 15.5 6 18" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

export default function AIAssistant({
  docId,
  onSourceClick,
  onCollapse,
}: {
  docId: number;
  onSourceClick: (sectionId: number) => void;
  onCollapse?: () => void;
}) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);

  async function send(q: string) {
    if (!q.trim() || loading) return;
    setMessages((m) => [...m, { role: "user", text: q }]);
    setQuestion("");
    setLoading(true);
    try {
      const res = await askQuestion(docId, q);
      setMessages((m) => [...m, { role: "assistant", text: res.answer, sources: res.sources }]);
    } catch {
      setMessages((m) => [...m, { role: "assistant", text: "Something went wrong answering that question. Try again." }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-full flex-col bg-parchment-100">
      <div className="flex shrink-0 items-center justify-between border-b border-ink/10 bg-white px-4 py-3">
        <div className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-teal-50 text-teal-600">
            <SparkIcon className="h-4 w-4" />
          </span>
          <div>
            <h2 className="text-sm font-semibold text-ink">AI Assistant</h2>
            <p className="text-[11px] text-slate-400">Document intelligence</p>
          </div>
        </div>
        <div className="flex items-center gap-0.5">
          {messages.length > 0 && (
            <button
              onClick={() => setMessages([])}
              title="New conversation"
              className="rounded-md p-1.5 text-slate-400 transition hover:bg-parchment-200 hover:text-ink"
            >
              <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4"><path d="M3 12a9 9 0 1 1 3 6.7M3 21v-5h5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></svg>
            </button>
          )}
          {onCollapse && (
            <button
              onClick={onCollapse}
              title="Collapse panel"
              className="rounded-md p-1.5 text-slate-400 transition hover:bg-parchment-200 hover:text-ink"
            >
              <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4"><path d="M15 6l-6 6 6 6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
        {messages.length === 0 && (
          <div className="flex h-full flex-col">
            <div className="flex flex-col items-center pt-6 text-center">
              <span className="flex h-11 w-11 items-center justify-center rounded-full bg-teal-50 text-teal-600">
                <SparkIcon className="h-5 w-5" />
              </span>
              <p className="mt-3 text-sm font-medium text-ink">Ask about this document</p>
              <p className="mt-1 max-w-[220px] text-xs leading-relaxed text-slate-400">
                Every answer cites the exact section it came from.
              </p>
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`animate-fade-up ${m.role === "user" ? "flex justify-end" : ""}`} style={{ animationDuration: "0.25s" }}>
            <div className={m.role === "user" ? "max-w-[85%]" : "max-w-full"}>
              {m.role === "assistant" ? (
                <div className="flex gap-2">
                  <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-teal-50 text-teal-600">
                    <SparkIcon className="h-3 w-3" />
                  </span>
                  <div className="min-w-0">
                    <div className="rounded-xl rounded-tl-sm border border-ink/10 bg-white px-3.5 py-2.5 text-sm leading-relaxed text-ink shadow-sm">
                      {m.text}
                    </div>
                    {m.sources && m.sources.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {m.sources.map((s) => (
                          <button
                            key={s.id}
                            onClick={() => onSourceClick(s.id)}
                            className="inline-flex items-center gap-1 rounded-full border border-teal/20 bg-teal-50 px-2.5 py-1 font-mono text-[11px] text-teal-600 transition hover:border-teal hover:bg-teal hover:text-white"
                          >
                            § {s.heading}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <span className="inline-block rounded-xl rounded-tr-sm bg-ink px-3.5 py-2.5 text-sm leading-relaxed text-parchment shadow-sm">
                  {m.text}
                </span>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-teal-50 text-teal-600">
              <SparkIcon className="h-3 w-3" />
            </span>
            <div className="flex items-center gap-1 rounded-xl rounded-tl-sm border border-ink/10 bg-white px-3.5 py-2.5 shadow-sm">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-teal" />
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-teal [animation-delay:150ms]" />
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-teal [animation-delay:300ms]" />
            </div>
          </div>
        )}
      </div>

      <div className="shrink-0 border-t border-ink/10 bg-white px-3 pt-2.5">
        <div className="flex flex-wrap gap-1.5 pb-2.5">
          {SUGGESTED_QUESTIONS.map((q) => (
            <button
              key={q}
              onClick={() => send(q)}
              disabled={loading}
              className="rounded-full border border-ink/10 bg-parchment-100 px-3 py-1.5 text-xs font-medium text-slate-500 transition hover:border-teal/30 hover:bg-teal-50 hover:text-teal-600 disabled:opacity-40"
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      <div className="shrink-0 border-t border-ink/10 bg-white p-3">
        <div className="flex items-center gap-2 rounded-lg border border-ink/15 bg-parchment-100 px-1.5 py-1.5 transition focus-within:border-teal focus-within:bg-white">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send(question)}
            placeholder="Ask a question…"
            className="flex-1 bg-transparent px-2 py-1 text-sm text-ink placeholder:text-slate-400 focus:outline-none"
          />
          <button
            onClick={() => send(question)}
            disabled={loading || !question.trim()}
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-teal text-white transition hover:bg-teal-600 disabled:opacity-30"
          >
            <svg viewBox="0 0 24 24" fill="none" className="h-3.5 w-3.5"><path d="M4 12h16M14 6l6 6-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
          </button>
        </div>
      </div>
    </div>
  );
}
