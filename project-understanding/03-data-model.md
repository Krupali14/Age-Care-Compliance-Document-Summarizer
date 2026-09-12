# 03 — Data model

PostgreSQL 16. Schema defined in `backend/app/models/`, migrated by Alembic
(`backend/alembic/versions/`: `0001_baseline`, `0002_initial_schema`).

## The shape

```
users
  └─1:N─ documents
            ├─1:N─ sections ──────────┐
            ├─1:N─ obligations ───────┤
            ├─1:N─ risks ─────────────┤ every finding also points at
            ├─1:N─ deadlines ─────────┤ the section it came from
            ├─1:N─ action_items ──────┘
            ├─1:N─ summaries
            └─1:N─ eval_runs
```

**The double link is the point.** Each finding carries *both* `document_id` and
`section_id`. `document_id` makes "all obligations in this document" one indexed
query; `section_id` is what makes every finding in the interface clickable back to
the paragraph it was taken from. Without the second, the product would be a list of
assertions with no provenance.

## Tables

### `users`

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `email` | String, unique, indexed | Stored lowercased; validated ≤ 254 chars |
| `hashed_password` | String | bcrypt via passlib. Plaintext is never stored or logged |
| `created_at` | DateTime | |

Registration lowercases the address and sign-in lowercases the input, so a
capitalised address finds its own account.

### `documents`

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `user_id` | FK → users.id, not null | The whole authorisation model |
| `filename` | String, not null | Basename only — `Path(name).name` strips `../` |
| `file_type` | String, not null | `pdf` or `docx` |
| `status` | String, not null | See the state machine below |
| `error_message` | String, nullable | User-facing text for `failed` / `unsupported` |
| `uploaded_at` | DateTime | |

`sections` cascade-delete with the document (`cascade="all, delete-orphan"`).

#### Status state machine

```
pending ──► processing ──┬──► done          extraction finished
                         ├──► unsupported   relevance gate said no
                         └──► failed        the file could not be parsed
```

- `pending` — the row exists, the bytes are on disk, the background task has not run
- `processing` — parsing or extracting; the UI polls every 4 s
- `done` — findings are queryable; the assistant is offered
- `unsupported` — not compliance material; `error_message` holds the model's own
  one-sentence reason; tabs and the assistant are hidden
- `failed` — the document could not be produced. Three distinct causes, each with
  its own `error_message`: the file was unreadable, extraction returned nothing at
  all (the AI service was unreachable or rate limited), or processing was
  interrupted by a server restart

`done`, `unsupported` and `failed` are terminal — polling stops.

### `sections`

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `document_id` | FK → documents.id, not null | |
| `heading` | String, not null | Detected structurally, or `"Document"` |
| `order_idx` | Integer, not null | Document order; drives display and summary order |
| `page_ref` | String, nullable | Page number, when the fast path found one |
| `raw_text` | Text, not null | The section's body, capped at 6000 chars by splitting |

Every parsed section is stored, including short ones, so the document reads
complete. Sections under 40 characters (`EXTRACTABLE_MIN_CHARS`) are stored but
never sent for extraction — they are contents fragments and stray page numbers.

### `obligations`

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `document_id`, `section_id` | FKs, both not null | |
| `text` | Text, not null | The duty, as extracted |
| `responsible_role` | String, nullable | Only when the document states it |
| `priority` | String, nullable | `high` / `medium` / `low` |

### `risks`

| Column | Type | Notes |
|---|---|---|
| `text` | Text, not null | |
| `severity` | String, **not null** | `high` / `medium` / `low` — the one required rating |

### `deadlines`

| Column | Type | Notes |
|---|---|---|
| `description` | Text, not null | |
| `due_date` | String, nullable | **Deliberately a string** — see below |
| `responsible_role` | String, nullable | |

`due_date` is text, not a `Date`, because a compliance deadline is often not a
calendar date at all: *"within 30 days of the incident"*, *"1 month after
commencement"*. Those are the useful ones, and a `Date` column cannot hold them.
`normalize_due_date()` keeps future dates and relative phrasing, and drops dates
already past — a commencement date from 2019 is not a deadline.

### `action_items`

| Column | Type | Notes |
|---|---|---|
| `text` | Text, not null | |
| `responsible_role`, `timeframe`, `priority` | String, nullable | |
| `source_section` | String, nullable | The heading text, denormalised for display |

### `summaries`

| Column | Type | Notes |
|---|---|---|
| `text` | Text, not null | Every section's bullets joined in document order |
| `model_used` | Text, not null | `"section-wise"` for this pipeline |
| `created_at` | DateTime | |

One row per processing run, not per section — the section-level summaries are
concatenated so the Summary tab reads as one continuous document.

### `eval_runs`

| Column | Type | Notes |
|---|---|---|
| `precision`, `recall`, `f1` | Float, not null | Column names are historical |
| `ground_truth_ref` | String, not null | `"auto"`, `"api"`, or a ground-truth file path |
| `created_at` | DateTime | |

> **A naming trap.** For an automatic self-check, `ground_truth_ref == "auto"` and
> the three numbers are **grounding, coverage and overall** — not precision, recall
> and F1. The columns were not renamed because a ground-truth run genuinely stores
> precision/recall/F1 in them. The UI reads `ground_truth_ref` and relabels
> accordingly; calling a self-check "precision" would claim a comparison that never
> happened. See [08 Evaluation](08-evaluation.md).

## Query patterns

```python
# Ownership — the single gate, in routers/documents.py
_get_owned_document(doc_id, db, user)   # 404 (never 403) if it is not yours

# A category for a document
db.query(Obligation).filter(Obligation.document_id == doc_id).all()

# Everything the assistant can retrieve over
document.sections                        # relationship
_findings(doc_id, db)                    # all four categories as (text, section_id, kind)
```

## Things the schema does not have, and why

| Absent | Why |
|---|---|
| Status `ENUM` | Strings; a new status must not need a migration in an application still finding its shape |
| Teams / organisations | Out of scope — an account is one person ([01](01-what-this-is.md)) |
| A `findings` supertable | Four tables with different columns model the domain honestly; a shared table would be mostly nullable |
| Soft deletes | Deleting a document is meant to delete it |
| `updated_at` | Nothing is edited after extraction; a reprocess creates new rows |
| Indexes beyond the PKs and `users.email` | Not yet earned. The largest document is ~2,700 findings, and `document_id` filters are fast at that size — index when a query is measurably slow, not before |
