# 01 — What this is

## The problem

An Australian residential aged-care provider is answerable to:

- the **Aged Care Act 2024** and the Aged Care Rules 2025,
- the **Strengthened Aged Care Quality Standards** (published August 2025),
- the **Aged Care Quality and Safety Commission**, which audits against both.

The material that defines those duties is enormous. The Act's compilation in this
repository is 654 pages and 858,000 characters. The Strengthened Standards are 49
pages. A provider's own policies add dozens more documents.

Buried in that text are the things a provider actually has to *do*: report a
Priority 1 incident within 24 hours, complete a post-fall neurological assessment,
review restrictive-practice authorisations before they lapse. Each of those is one
sentence somewhere in hundreds of pages, and missing one is a compliance failure.

Reading it all is the job nobody has time for.

## What the application does

Upload a compliance document — PDF or DOCX — and it returns:

| Output | What it is |
|---|---|
| **Summary** | Section-by-section Markdown bullets, key facts bolded |
| **Obligations** | Things the provider or its workers are required to do, with the responsible role |
| **Risks** | Hazards the document identifies, each rated high / medium / low |
| **Deadlines** | Dates and timeframes, with past dates filtered out |
| **Action items** | Concrete steps, with responsible role and timeframe |
| **Sections** | The parsed document itself, so any finding can be checked against its source |
| **AI assistant** | Free-text questions answered from the document, every answer citing its section |
| **Evaluation** | A quality score for the extraction — see [08](08-evaluation.md) |

Every finding stores the `section_id` it came from. Nothing in the interface is a
claim the user cannot trace back to a paragraph of the original.

## Who uses it

| User | What they need |
|---|---|
| **Quality/compliance manager** | The obligation and deadline registers, for the audit calendar |
| **Clinical governance lead** | The risk list, and the ability to ask "who signs off on X?" |
| **Facility manager** | The summary — enough to know what a new instrument changes |
| **Auditor / assessor** | The citations, to verify a finding against the source |

## What it explicitly is not

- **Not legal advice.** Its output is a reading aid. Every screen that shows an AI
  finding is expected to be verified against the original.
- **Not a compliance register.** It extracts; it does not track completion,
  assign owners, or send reminders.
- **Not a document store.** Uploaded files are kept only so they can be reprocessed.
- **Not multi-tenant in the organisational sense.** An account is one person; there
  are no teams, roles or sharing.

## Scope boundaries enforced in the product

The application refuses work outside its remit rather than doing it badly:

- **File types** — PDF and DOCX only, checked by extension *and* magic bytes.
- **Size** — 25 MB by default (`MAX_UPLOAD_MB`).
- **Subject matter** — a relevance gate asks the model whether the upload is
  compliance material at all. An invoice or a résumé is marked `unsupported` with a
  one-sentence reason, and costs one model call rather than two hundred.

## The shape of a session

```
Register / sign in
   └─ Dashboard: upload a document
        └─ card shows Queued → Reading → Ready   (polled, no reload)
             └─ Document: Summary · Obligations · Risks · Deadlines · Actions · Sections
                  ├─ AI assistant beside it, answers cite sections
                  └─ Evaluation results: how good was this extraction?
```

## Domain vocabulary

Aged-care terms used throughout — SIRS, Priority 1 incident, restrictive practice,
registered provider — are defined in [13 Glossary](13-glossary.md).
