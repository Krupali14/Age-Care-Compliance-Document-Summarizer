# 13 — Glossary

## Aged-care and regulatory terms

**Aged Care Act 2024** — The Commonwealth Act governing aged care in Australia,
replacing the Aged Care Act 1997. The compilation in `docs/` is 654 pages. It
defines registration, provider duties, the Statement of Rights, and the penalties
for breach.

**Aged Care Rules 2025** — Subordinate legislation made under the Act, carrying the
operational detail the Act delegates.

**Aged Care Quality and Safety Commission** — The regulator. Registers providers,
conducts audits, issues compliance notices, and can revoke registration.

**Strengthened Aged Care Quality Standards** — The standards published August 2025,
against which providers are assessed. Structured as Standards → Outcomes →
Expectation statements, which is why headings like `1.1.2` and `2.2.1` appear
throughout the extracted sections.

**Registered provider** — An organisation registered to deliver funded aged care.
Most obligations in the Act attach to this term.

**SIRS — Serious Incident Response Scheme** — The mandatory incident reporting
regime. Certain incidents must be notified to the Commission within fixed
timeframes, which is why "within 24 hours" recurs in the extracted deadlines.

**Priority 1 incident** — The more serious SIRS category: notifiable to the
Commission **within 24 hours**. Priority 2 incidents are notifiable within 30 days.

**Reportable incident** — An incident that triggers SIRS: unreasonable use of force,
unlawful or inappropriate sexual contact, psychological or emotional abuse, neglect,
unexpected death, stealing or financial coercion, inappropriate use of restrictive
practices, unexplained absence from care.

**Restrictive practice** — Any practice restricting a person's rights or freedom of
movement — chemical, physical, mechanical, environmental, or seclusion. Heavily
regulated; requires authorisation, consent and review.

**Statement of Rights** — The rights of a person receiving aged care, set out in the
Act. Providers must act compatibly with it.

**Open disclosure** — The obligation to tell a person harmed what happened, apologise,
and commit to informing them of the investigation's findings.

**Clinical governance** — The framework through which a provider is accountable for
the quality and safety of clinical care.

**Penalty unit** — The unit in which Commonwealth fines are expressed. "250 penalty
units" is a real quantum in the Act.

**Compilation** — A consolidated version of an Act incorporating all amendments to a
given date. The `C2026C00301.pdf` in `docs/` is one.

---

## Application terms

**Document** — One uploaded file and everything derived from it.

**Section** — One parsed unit of a document: a heading plus its body. Detected
structurally (`Part 5`, `3.2 Incident reporting`), split at 6000 characters, and the
unit everything else cites.

**Finding** — Collective term for an obligation, risk, deadline or action item. Not
a table; a concept spanning four tables.

**Extraction** — The model call turning a section's text into a summary plus
findings.

**Batch** — Up to 8 sections or 6000 characters sent in one extraction call.

**Relevance gate** — The single cheap call deciding whether an upload is compliance
material at all, before any extraction spend.

**Extractable section** — A section of 40+ characters. Shorter ones are contents
fragments and page numbers; stored, never extracted.

**Passage** — A retrievable unit for the assistant: either a section or a formatted
finding. A 1304-section Act yields 3,777 passages.

**Grounding** — Share of findings whose wording is carried by the section they cite.
The check against invented content.

**Coverage** — Share of extractable sections that produced at least one finding. The
check against silent gaps.

**Auto-eval / self-check** — Scoring a document against itself; needs no annotation.
Stored with `ground_truth_ref = "auto"`.

**Ground-truth run** — Scoring against hand-annotated answers, giving true precision,
recall and F1.

---

## Technical terms

**BM25** — The ranking function used for retrieval. Scores a passage by how rare the
query's terms are in this document (idf), how often they occur (tf, with
saturation), and the passage's length (discounted, not rewarded).

**idf — inverse document frequency** — How rare a term is across the corpus. On an
aged-care Act, "care" has almost none and "deadline" has a lot.

**Structured output** — Constraining the model to a JSON schema.
`method="json_schema"` is OpenAI's strict mode, which actually enforces required
fields; the default `function_calling` treats the schema as a hint.

**Text layer** — The embedded, selectable text in a born-digital PDF. Its presence
is what lets parsing skip OCR entirely.

**docling** — The document-conversion library used for scanned PDFs and DOCX. Runs
layout analysis and OCR; accurate and slow.

**pypdfium2** — Python bindings to PDFium, used to read the text layer directly.

**TPM — tokens per minute** — The provider's rate ceiling. The limiter exists to
stay under it.

**Live region** — An `aria-live` element. A screen reader announces changes inside
it without moving focus; how errors and answers are announced here.

**Focus trap** — Keeping keyboard focus inside an open dialog. Implemented in
`ConfirmModal`.

**StrictMode** — React's development double-invocation of renders and state
initializers, which surfaces impure code. It caught a side effect wrongly placed in
a `useState` initializer here.

**Alembic** — SQLAlchemy's migration tool. Runs `upgrade head` on backend start.

**BackgroundTasks** — FastAPI's mechanism for work that runs after the response is
sent. How extraction happens without blocking the upload.
