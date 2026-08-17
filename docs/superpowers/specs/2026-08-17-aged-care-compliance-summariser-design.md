# Aged Care Compliance Document Summariser — Design

Capstone project (student Krupaliben Golani, project #13). Scaffold exists
(FastAPI backend, React frontend, Postgres, Docker); no NLP/LLM logic yet.
This design covers building the full pipeline against the scope doc's
functional/non-functional requirements.

## Goals

- Upload PDF/DOCX aged-care compliance documents.
- Parse + chunk by section, extract: summary, obligations, risks, deadlines,
  action items — each traceable to its source section.
- Display results in a dashboard.
- Evaluate extraction accuracy against manually annotated ground truth
  (precision/recall/F1).
- Stretch: RAG chatbot over a document's stored sections.

## Non-goals

- Multi-role auth (single role, simple login only).
- Real confidential resident data (public/synthetic/anonymised docs only,
  per scope doc).
- Queue infra (Celery/Redis) — FastAPI `BackgroundTasks` is enough at this
  scale.

## Architecture

```
Upload (PDF/DOCX) → docling parse → section-based chunks (heading + text + page/section ref)
  → per-chunk LLM call (LangChain ChatOpenAI, structured output/pydantic schema)
    → {summary, obligations[], risks[], deadlines[], actions[]} each tagged w/ source_section
  → merge chunk results per doc → persist to Postgres
  → dashboard reads persisted structured data
```

One LLM call per section chunk (not per whole doc) — keeps context bounded
and keeps source-section attribution honest, satisfying the "source
references for verification" NFR.

## Processing flow

```
POST /upload → save file → create `documents` row (status=pending)
→ FastAPI BackgroundTasks:
    docling.DocumentConverter().convert(file) → structured doc (headings, text, page refs)
    → split into `sections` rows
    → for each section: llm.with_structured_output(schema) →
         persist obligations/risks/deadlines/actions/summary rows
    → status=done (or failed w/ error message, per-section try/except
      so one bad section doesn't fail the whole document)
```

## LLM integration

```python
# app/services/llm.py
from langchain_openai import ChatOpenAI

def get_llm():
    return ChatOpenAI(
        base_url=os.environ["LLM_BASE_URL"],  # NVIDIA NIM in dev, unset -> OpenAI in prod
        api_key=os.environ["LLM_API_KEY"],
        model=os.environ["LLM_MODEL"],
    )
```

`.env` additions: `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`. Dev points at
NVIDIA NIM's OpenAI-compatible endpoint; prod swaps to OpenAI values with no
code change. Structured output via `.with_structured_output(pydantic_schema)`
— one schema per section covering summary + obligations + risks + deadlines
+ actions, one call per section.

Doc parsing/chunking uses **docling** (layout-aware PDF/DOCX conversion),
replacing the PyMuPDF/python-docx line from the original resource list —
docling gives structured heading/section detection directly, which
section-based chunking depends on.

## Data model (Postgres, SQLAlchemy + Alembic)

```
users(id, email, hashed_password, created_at)
documents(id, user_id, filename, file_type, status[pending/processing/done/failed], uploaded_at)
sections(id, document_id, heading, order_idx, page_ref, raw_text)
summaries(id, document_id, text, model_used, created_at)
obligations(id, document_id, section_id, text, responsible_role, priority)
risks(id, document_id, section_id, text, severity[high/medium/low])
deadlines(id, document_id, section_id, description, due_date, responsible_role)
action_items(id, document_id, section_id, text, responsible_role, timeframe, priority, source_section)
eval_runs(id, document_id, precision, recall, f1, ground_truth_ref, created_at)
```

Every extracted item FKs to `sections` for source traceability. `documents.status`
drives the async processing indicator in the dashboard.

## API

```
POST /auth/register, /auth/login          (JWT, single role)   [new]
POST /upload                               → create doc, kick background processing
GET  /documents                            → list w/ status
GET  /documents/{id}                       → doc detail (sections)
GET  /summarize/{doc_id}
GET  /obligations/{doc_id}
GET  /risks/{doc_id}
GET  /deadlines/{doc_id}
GET  /actions/{doc_id}
GET  /documents/{id}/eval                  → precision/recall/F1 if ground truth exists  [new]
POST /chat/{doc_id}                        → RAG Q&A over stored sections  [new, phase 6]
```

Existing router stubs (`upload`, `summarize`, `obligations`, `risks`,
`deadlines`, `actions`) get real implementations; `auth`, `eval`, `chat` are
new routers.

## Frontend

```
Landing.tsx          → login/register
Dashboard.tsx         → doc list + upload button + status badges
DashboardLayout.tsx   → nav shell (existing)
DocumentDetail.tsx    → tabs: Summary | Obligations | Risks | Deadlines | Actions
                        (row click → highlight source section, traceability)
EvalPage.tsx          → P/R/F1 per doc, once a ground-truth eval run exists
ChatPanel.tsx         → phase 6, embedded in DocumentDetail
```

React Query for server state — no Redux, app is small and server-state only.
Category tables (obligations/risks/deadlines/actions) share one component:
same shape (text + role + priority/severity + source link).

## Evaluation

```
scripts/eval.py:
  ground_truth/<doc_id>.json → manually annotated {obligations, risks, deadlines, actions}
  load LLM-extracted rows from DB for same doc
  fuzzy-match predicted vs ground truth per category (rapidfuzz token overlap,
    or sentence-transformers cosine sim if token overlap proves too strict)
  compute precision/recall/F1 per category → write `eval_runs` row + print report
```

5–10 synthetic/public docs hand-annotated (per scope doc's resource list).
Exact string match is too strict for LLM-generated text, hence fuzzy match.

## Responsible AI

Every summary/extraction view renders a fixed disclaimer ("AI-generated,
verify against source document") client-side — static text, no DB storage
needed. Matches the scope doc's "Responsible Model" NFR: system is
decision-support, not a final compliance ruling.

## Reliability

Per-section try/except during background processing — one failing section
sets that section's rows to empty/error state rather than failing the whole
document. `documents.status = failed` only on unrecoverable errors (e.g.
docling can't parse the file at all, unsupported format).

## Phased build order

1. Auth + doc upload + docling parsing + sections storage
2. LLM structured extraction (summary/obligations/risks/deadlines/actions) + persistence
3. Dashboard + document detail UI wired to real data
4. Eval harness + ground-truth annotation
5. Polish: error states, reliability (retry/failed status), NFR pass
6. Chatbot (RAG over sections) — stretch, last

## Key decisions

- **LLM**: LangChain `ChatOpenAI`, OpenAI-compatible `base_url` — NVIDIA NIM
  in dev, OpenAI in prod, swapped via `.env` only.
- **Extraction**: hybrid — docling for structural parsing, single LLM call
  per section for semantic extraction (not spaCy/regex).
- **Chunking**: section/heading-based (via docling), not fixed-token —
  required for source-section traceability.
- **Chatbot**: included, but last (stretch) phase.
- **Auth**: simple single-role login, no RBAC.
- **Eval**: manual annotation + fuzzy-match P/R/F1 script, matches scope doc directly.
