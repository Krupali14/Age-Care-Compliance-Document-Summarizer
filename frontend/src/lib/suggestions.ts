/**
 * Question suggestions for the assistant, derived from the document itself.
 *
 * Two things were wrong with the fixed list this replaces. It was the same four
 * strings for every document — offering "What are the major risks?" for a document
 * with no risks in it — and it lived in a strip pinned above the composer, which
 * cost the answer area its height for the whole conversation.
 *
 * These are built from what extraction actually found, so a document with no
 * deadlines is never asked about deadlines, and they are rendered in the scroll
 * flow rather than in fixed chrome.
 */

export interface DocumentContext {
  obligations: number;
  risks: number;
  deadlines: number;
  actions: number;
  /** Headings of the sections the last answer cited, most relevant first. */
  citedHeadings?: string[];
}

/** Openers, for a conversation that has not started. */
export function openingQuestions(context: DocumentContext): string[] {
  const questions: string[] = [];
  if (context.obligations > 0) questions.push("What are the key compliance obligations?");
  if (context.risks > 0) questions.push("What are the major risks?");
  if (context.deadlines > 0) questions.push("What deadlines are mentioned?");
  if (context.actions > 0) questions.push("What actions are required?");

  // A document can legitimately carry none of the four — a definitions-heavy
  // policy, say — and an empty state with nothing to click is worse than a
  // general starter.
  if (questions.length === 0) {
    return ["What is this document about?", "What does it require the provider to do?"];
  }
  return questions;
}

/**
 * Follow-ups for a conversation in progress.
 *
 * Ordered so the most specific come first: a question about a section the last
 * answer actually cited is worth more than another category sweep. Anything
 * already asked is dropped, so the list moves on as the conversation does.
 */
export function followUpQuestions(context: DocumentContext, asked: string[]): string[] {
  const alreadyAsked = new Set(asked.map((q) => q.trim().toLowerCase()));
  const candidates: string[] = [];

  for (const heading of (context.citedHeadings ?? []).slice(0, 2)) {
    const trimmed = heading.trim();
    if (trimmed) candidates.push(`What does "${shorten(trimmed)}" require?`);
  }

  if (context.risks > 0) candidates.push("Which of these risks are rated high?");
  if (context.deadlines > 0) candidates.push("Which deadline comes first?");
  if (context.obligations > 0) candidates.push("Who is responsible for each obligation?");
  if (context.actions > 0) candidates.push("What actions are required?");
  candidates.push("What are the consequences of non-compliance?");
  candidates.push("Summarise this document in five points.");

  const unasked = candidates.filter((q) => !alreadyAsked.has(q.trim().toLowerCase()));
  return unique(unasked).slice(0, 3);
}

/** Section headings can be a full sentence; a chip cannot. */
function shorten(heading: string, max = 46): string {
  if (heading.length <= max) return heading;
  return `${heading.slice(0, max).trimEnd()}…`;
}

function unique(values: string[]): string[] {
  return [...new Set(values)];
}
