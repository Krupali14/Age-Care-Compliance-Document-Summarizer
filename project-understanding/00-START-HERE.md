# Project Understanding

Everything needed to understand the Aged Care Compliance Document Summariser —
what it is, how it is built, why it is built that way, and how to work on it.

Written to be read by someone who has never seen the repository.

---

## Read in this order

| # | File | What it answers | Read if you are… |
|---|---|---|---|
| 01 | [What this is](01-what-this-is.md) | The problem, the users, the scope | anyone — start here |
| 02 | [Architecture](02-architecture.md) | The pieces and how they fit | a developer, an assessor |
| 03 | [Data model](03-data-model.md) | Every table and relationship | working on the backend |
| 04 | [API reference](04-api-reference.md) | Every endpoint, request, response | integrating or testing |
| 05 | [Processing pipeline](05-processing-pipeline.md) | Upload → parse → extract → store | the core of the system |
| 06 | [AI and retrieval](06-ai-and-retrieval.md) | Prompts, batching, how the chat finds answers | the interesting part |
| 07 | [Frontend guide](07-frontend-guide.md) | Routes, components, state, design system | working on the UI |
| 08 | [Evaluation](08-evaluation.md) | How quality is measured | assessing the output |
| 09 | [Security](09-security.md) | Auth, isolation, limits, what is not covered | reviewing for production |
| 10 | [Testing](10-testing.md) | What is tested and how to run it | changing anything |
| 11 | [Running locally](11-running-locally.md) | Setup, env vars, troubleshooting | getting started |
| 12 | [Design decisions](12-design-decisions.md) | Why it is this way and not another way | reviewing or extending |
| 13 | [Glossary](13-glossary.md) | Aged-care and technical terms | new to the domain |
| 14 | [Known limitations](14-known-limitations.md) | What it does not do, and what is next | planning work |

## Shortest useful path

- **"Just show me it working"** → [11 Running locally](11-running-locally.md)
- **"Explain it in five minutes"** → [01](01-what-this-is.md) then [02](02-architecture.md)
- **"Is the AI any good?"** → [06](06-ai-and-retrieval.md) then [08](08-evaluation.md)
- **"Is it production ready?"** → [09](09-security.md), [10](10-testing.md), [14](14-known-limitations.md)

## Related material elsewhere in the repository

These are the deep-dive engineering documents. This folder summarises and
cross-references them rather than repeating them.

- `docs/PROCESSING_PIPELINE.md` — the full performance write-up, with measurements
- `docs/EVALUATION.md` — the full evaluation reference
- `docs/VSCODE_SETUP.md` — editor setup and lint/type errors
- `README.md` — quick start
- `samples/` — six realistic aged-care policy PDFs for demonstration

## One-paragraph version

An aged-care provider is answerable to the Aged Care Act 2024 and the Strengthened
Aged Care Quality Standards. The documents that describe those duties run to
hundreds of pages. This application takes such a document, reads it, and returns the
obligations, risks, deadlines and action items it contains — each one linked back to
the section it came from — plus an assistant that answers questions about the
document with citations. A 654-page Act parses in 0.77 seconds and extracts in a few
minutes; a 24-page policy is done in under half a minute.
