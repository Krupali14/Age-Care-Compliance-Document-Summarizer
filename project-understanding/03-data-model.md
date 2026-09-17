# 03 — Data model

PostgreSQL 16. Schema defined in `backend/app/models/`, migrated by Alembic
(`backend/alembic/versions/`: `0001_baseline`, `0002_initial_schema`,
`0003_deadline_status`, `0004_compliance_checks`).

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
            ├─1:N─ eval_runs
            └─1:N─ compliance_checks ─1:N─ check_findings
```

`compliance_checks` hangs off `documents` too, but it is not a finding category —
it is the record of one case study being checked against everything the other
categories already found. See below.

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
| `status` | String, not null, default `not_started` | `not_started` \| `in_progress` \| `completed` — migration `0003`. See `app/services/deadlines.STATUSES` |

`due_date` is text, not a `Date`, because a compliance deadline is often not a
calendar date at all: *"within 30 days of the incident"*, *"1 month after
commencement"*. Those are the useful ones, and a `Date` column cannot hold them.
`normalize_due_date()` keeps future dates and relative phrasing, and drops dates
already past — a commencement date from 2019 is not a deadline.

`status` is the one column on this table a user writes to directly, via
`PATCH /api/deadlines/item/{id}` ([04](04-api-reference.md)) — recording that a
deadline was actioned, not re-running extraction. `due_date` stays text either
way; turning it into a point in time is `resolve_due_at()`'s job, not the
column's — see [05](05-processing-pipeline.md#the-compliance-check) and
`app/services/deadlines.py`.

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

### `compliance_checks`

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `document_id` | FK → documents.id, not null | The compliance document being checked against |
| `filename`, `file_type` | String, not null | The case study's own upload — validated and stored the same way a document is ([04](04-api-reference.md)) |
| `status` | String, not null, default `pending` | `pending → processing → done \| failed`, same shape as `documents.status` |
| `error_message` | String, nullable | User-facing text on `failed` |
| `uploaded_at` | DateTime | |
| `incident_at` | DateTime, nullable | When the case study says the incident happened |
| `incident_source` | String, nullable | `"stated"` when the case study named a time, `"upload_time"` when none was found and the upload time stood in |
| `evidence_text` | Text, nullable | The parsed case study, stored once so re-reading a check does not re-parse the file |

A case study is deliberately **not** a `Document` row: it gets no extraction of its
own, it must not appear on the dashboard, and its only relationship is to the one
compliance document it was checked against. Migration `0004`.

### `check_findings`

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `check_id` | FK → compliance_checks.id, not null | |
| `kind` | String, not null | `"obligation"` or `"deadline"` — which table `source_id` points into |
| `source_id` | Integer, not null | The obligation or deadline row this finding judges |
| `section_id` | Integer, nullable | Denormalised from the source row, for the same click-through-to-source reason every other finding carries one |
| `requirement` | Text, not null | **A snapshot** of the obligation/deadline text at check time, not a live join |
| `verdict` | String, not null | `done` \| `not_done` \| `partly` \| `unclear` |
| `evidence` | Text, nullable | The sentence from the case study the model quoted, or null |
| `note` | Text, nullable | One sentence explaining the verdict |
| `due_at`, `bucket` | DateTime, String, both nullable | Only set when `kind == "deadline"` — the deadline resolved against `incident_at`, not against upload time |

`requirement` is a snapshot on purpose. Re-processing the compliance document
replaces its `obligations` rows outright, and a live join would silently change or
delete an old check's findings when that happens; the snapshot keeps a finished
check meaning what it meant when it ran. See
[05](05-processing-pipeline.md#the-compliance-check) for how one finding gets its
verdict. Migration `0004`.

`delete_document` removes a document's checks, their findings and their uploaded
case-study files along with everything else — there is no `ON DELETE CASCADE` on
these FKs (same as the rest of this schema), so `backend/app/routers/documents.py`
deletes children before the parent row.

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
