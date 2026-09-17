# 04 — API reference

Base URL `http://localhost:8002`. Interactive OpenAPI at **`/docs`**, always current
— this file explains the parts the schema cannot.

## Conventions

- Every route except `/health`, `/api/auth/register` and `/api/auth/login` needs
  `Authorization: Bearer <token>`.
- A document belonging to another account returns **404, never 403**. The
  application does not confirm that an id exists to someone who cannot see it.
- Errors are `{"detail": "..."}`; Pydantic validation errors are
  `{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}`. The frontend's
  `api/client.ts` unwraps both, so the server's own wording reaches the user.

## Health

### `GET /health`
No auth. `{"status": "ok"}`. Used for readiness checks.

---

## Authentication

### `POST /api/auth/register`

```json
{ "email": "manager@facility.com", "password": "secret123" }
```

`201 → {"id": 1, "email": "manager@facility.com"}`

| Rule | Failure |
|---|---|
| Address matches `^[^@\s]+@[^@\s]+\.[^@\s]+$` | 422 "Enter a valid email address" |
| Address ≤ 254 characters | 422 |
| Password ≥ 8 characters | 422 |
| Password ≤ 72 **bytes** | 422 — bcrypt silently ignores everything past 72, so accepting a longer one would be a lie |
| Address not already taken | 400 "Email already registered" |
| ≤ 5 registrations per hour per IP | 429 + `Retry-After` |

The address is stripped and lowercased before storage.

### `POST /api/auth/login`

**Form-encoded**, not JSON — this is OAuth2's password flow, so the username field
is literally named `username` and carries the email.

```
Content-Type: application/x-www-form-urlencoded
username=manager@facility.com&password=secret123
```

`200 → {"access_token": "eyJ…", "token_type": "bearer"}`

- The JWT carries `sub` (user id), `exp`, and `email`. Authorisation reads `sub` and
  re-loads the user from the database every request, so the `email` claim is display
  data only and a tampered one buys nothing.
- Default lifetime 480 minutes (`JWT_EXPIRE_MINUTES`).
- Wrong password → 401 "Incorrect email or password" — the same message whether or
  not the account exists.
- ≤ 10 attempts per 15 minutes **per address**, and 30 per 15 minutes per IP → 429.
  Counted *before* the password check, so a guess is never free and bcrypt's cost is
  not a lever an attacker can pull. The lockout also blocks the *correct* password,
  or its success would reveal the hit.

---

## Upload

### `POST /api/upload`

`multipart/form-data`, field `file`.

`201 → {"id": 12, "filename": "policy.pdf", "status": "pending"}`

Returns as soon as the bytes are on disk — typically ~100 ms. Extraction runs after
the response, as a background task. Poll `GET /api/documents/{id}` for the result.

| Rule | Failure |
|---|---|
| Extension `.pdf` or `.docx` (case-insensitive) | 400 |
| First bytes are `%PDF-` / `PK\x03\x04` | 400 "not a readable PDF…" |
| Not empty | 400 "This file is empty" |
| ≤ `MAX_UPLOAD_MB` (default 25) | 413 |

Streamed in 1 MB chunks and abandoned the moment it runs over, so an oversized
upload costs bounded memory and disk rather than its full size. The partial file is
removed and the `Document` row deleted on every failure path. The stored name is
`Path(filename).name`, so `../../etc/evil.pdf` cannot escape the upload directory.

---

## Documents

### `GET /api/documents`
Every document for the caller, newest first.
```json
[{"id": 12, "filename": "policy.pdf", "status": "done", "uploaded_at": "…"}]
```

### `GET /api/documents/{id}`
One document **with all its sections** — this is what the detail page renders.
```json
{ "id": 12, "filename": "policy.pdf", "status": "done", "error_message": null,
  "sections": [{"id": 1, "heading": "5.1 Method", "order_idx": 0,
                "page_ref": "7", "raw_text": "…"}] }
```

### `DELETE /api/documents/{id}`
Deletes the document, its sections and every other row that hangs off it —
obligations, risks, deadlines, action items, summaries, eval runs, and now its
compliance checks and their findings and uploaded case-study files. `204`.

---

## Extractions

All four take a document id, return a flat list, and 404 on a document that is not
yours.

| Route | Row shape |
|---|---|
| `GET /api/summarize/{id}` | `{id, text}` — `text` is Markdown bullets |
| `GET /api/obligations/{id}` | `{id, section_id, text, responsible_role, priority}` |
| `GET /api/risks/{id}` | `{id, section_id, text, severity}` |
| `GET /api/deadlines/{id}` | `{id, section_id, description, due_date, due_at, bucket, responsible_role, status}` |
| `GET /api/actions/{id}` | `{id, section_id, text, responsible_role, timeframe, priority}` |

An empty list means the document genuinely has none of that category — a
definitions-only policy legitimately has no deadlines. It does not mean an error.

`GET /api/deadlines/{id}` carries three columns the others don't: `due_at` (ISO
datetime, or `null`), `bucket` (`overdue | within_24_hours | within_7_days |
within_30_days | later | no_date`), and `status` (`not_started | in_progress |
completed`, default `not_started`). `due_date` stays the raw stored string — a
calendar date or a relative timeframe, exactly as extracted; `due_at` and `bucket`
are computed on every request from `due_date` plus the document's `uploaded_at`
(the anchor a relative timeframe counts from), not stored. See
[05](05-processing-pipeline.md#the-compliance-check) and
`app/services/deadlines.py` for `resolve_due_at()` / `bucket_for()`.

### `PATCH /api/deadlines/item/{deadline_id}`

```json
{ "status": "in_progress" }
```

`200 → {"id": 41, "status": "in_progress"}`. Records progress against one
deadline — this is the only write endpoint any extraction category has. `status`
must be one of `not_started | in_progress | completed`, else `422`. 404 on a
deadline whose document is not yours (ownership is checked via the deadline's
`document_id`, since the row itself has no owner column).

---

## Chat

### `POST /api/chat/{doc_id}`

```json
{ "question": "What deadlines are mentioned?" }
```

```json
{ "answer": "The following deadlines are mentioned: …",
  "sources": [{"id": 41, "heading": "5.1 Method"}] }
```

`answer` is Markdown. `sources` are the sections the answer drew on, in rank order —
the UI renders them as chips that jump to the section.

| Case | Response |
|---|---|
| Blank or whitespace question | 422 "Ask a question first" |
| Question > 2000 characters | 422 — capped before it reaches the model |
| Document has no sections | 409 "no readable content to answer from" |
| Model or network failure | 503 "The assistant is unavailable right now." The provider's raw error is logged, never returned |

**How retrieval works** — BM25 over the document's own sections *plus* its extracted
findings, with guaranteed slots when the question names a category. That is the
substance of the feature and is explained in [06](06-ai-and-retrieval.md).

---

## Evaluation

### `GET /api/documents/{id}/eval`
Every run for the document, newest first.
```json
[{"id": 3, "precision": 0.91, "recall": 0.59, "f1": 0.71,
  "ground_truth_ref": "auto", "created_at": "…"}]
```
When `ground_truth_ref` is `"auto"`, read the three numbers as **grounding,
coverage, overall**.

### `POST /api/documents/{id}/eval/auto`
Scores the document against itself — no annotation needed. `201`, returns the run.
**409** unless the document's status is `done`.

### `POST /api/documents/{id}/eval`
Scores against hand-annotated ground truth.
```json
{ "ground_truth": { "obligations": ["…"], "risks": ["…"],
                    "deadlines": ["…"], "action_items": ["…"] } }
```
Only the categories present are scored. An empty object is **400**, rather than
dividing by zero.

---

## Compliance checks

Checks one case-study document (an incident record, a file note) against a
compliance document's own obligations and deadlines. The full pipeline is in
[05](05-processing-pipeline.md#the-compliance-check); this is the surface.

### `POST /api/compliance-checks/{doc_id}`

`multipart/form-data`, field `file` — the case study, not the compliance document
(that's `doc_id`, already uploaded and processed).

`201 → {"id": 7, "filename": "case-study.docx", "status": "pending"}`

Same file rules as `/api/upload` (PDF/DOCX, magic-byte check, size cap) via the
shared `save_upload()`. Verdicts run as a background task
(`app.services.compliance_check.run_check`); poll `GET /api/compliance-checks/item/{id}`
for `status`.

### `GET /api/compliance-checks/{doc_id}`

Every check run against this document, newest first.

```json
[{ "id": 7, "filename": "case-study.docx", "status": "done",
   "error_message": null, "uploaded_at": "…",
   "incident_at": "2026-09-14T15:10:00", "incident_source": "stated",
   "counts": {"done": 4, "partly": 1, "not_done": 1, "unclear": 2} }]
```

`counts` tallies `findings` by verdict, always carrying all four keys (zero-filled)
so the UI never has to guess which verdicts exist.

### `GET /api/compliance-checks/item/{check_id}`

One check with every finding.

```json
{ "id": 7, "document_id": 3, "filename": "case-study.docx", "status": "done",
  "incident_at": "2026-09-14T15:10:00", "incident_source": "stated",
  "counts": {"done": 4, "partly": 1, "not_done": 1, "unclear": 2},
  "findings": [
    { "id": 21, "kind": "deadline", "section_id": 5,
      "requirement": "Notify the coordinator within 30 minutes of the incident",
      "verdict": "done",
      "evidence": "The coordinator was notified at 3:22pm.",
      "note": "Notified 12 minutes after the incident, within the 30-minute window.",
      "due_at": "2026-09-14T15:40:00", "bucket": "overdue" } ] }
```

`due_at`/`bucket` are only present (non-null) on `kind: "deadline"` findings, and
`due_at` is resolved against `incident_at` — not the check's `uploaded_at` — so a
finding's due time reflects when the incident actually happened, not when someone
got around to running the check.

### `DELETE /api/compliance-checks/item/{check_id}`

Deletes the check, its findings, and its uploaded case-study file. `204`.

| Case | Response |
|---|---|
| `doc_id` / `check_id` not owned by the caller | 404 |
| Case study extension not `.pdf`/`.docx` | 400 |
| Case study unreadable | Check moves to `status: "failed"`, `error_message` set — not an HTTP error, since the upload itself succeeded |

---

## CORS

One origin only — `VITE_API_URL_ORIGIN`, default `http://localhost:3002`, with
credentials allowed. Any other origin is refused at the preflight. There is no
wildcard.

## Rate limits at a glance

| Endpoint | Limit | Window | Env override |
|---|---|---|---|
| `POST /api/auth/login` | 10 per address | 15 min | `LOGIN_MAX_ATTEMPTS`, `LOGIN_WINDOW_SECONDS` |
| `POST /api/auth/login` | 30 per IP | 15 min | (3 × the above) |
| `POST /api/auth/register` | 5 per IP | 1 hour | `REGISTER_MAX_ATTEMPTS`, `REGISTER_WINDOW_SECONDS` |

Counters are **per process, in memory**. With one API container that is the whole
truth; behind a second worker each enforces its own share and the effective ceiling
multiplies. Move the store to Redis at that point — the call sites do not change.
The end-to-end suite raises them via `make e2e` rather than weakening the defaults.
