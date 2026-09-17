# Compliance check — design

**Date:** 2026-09-17
**Status:** approved, ready for implementation planning

## Problem

A compliance document (policy, standard, procedure) is uploaded and the app extracts
its obligations, risks, deadlines and action items. What it cannot answer is the
question the user actually has: *given what my organisation did in this case, which
of those requirements are satisfied, which are outstanding, and how long do I have
left?*

Today that comparison happens in the user's head. The compliance check does it in
the app: the user opens a compliance document, uploads a case-study document
(an incident record, an audit response, a file note) into a new section of that
document, and gets a verdict against every obligation and deadline the compliance
document carries.

## Direction is one-way

The compliance document is the source of requirements. The case study is the
evidence. A check always reads one case study against one compliance document, and
the case study is uploaded from inside that compliance document's page. There is no
"compare any two documents" mode.

The case study is parsed into text and used as evidence. It is not extracted, does
not get obligations or deadlines of its own, and never appears on the dashboard as a
document. Its only reason to exist is the check.

## What a check produces

For every obligation and every deadline belonging to the compliance document, one
finding:

| Field | Meaning |
|---|---|
| `verdict` | `done` \| `not_done` \| `partly` \| `unclear` |
| `evidence` | the sentence from the case study that supports the verdict, or null |
| `note` | one sentence explaining the verdict |
| `due_at` | deadlines only: when it falls due, counted from the incident |
| `bucket` | deadlines only: `overdue` / `within_24_hours` / … (existing buckets) |

`unclear` is a first-class answer: the case study is silent on that requirement. It
is not a failure and must not be reported as one.

## The clock

A deadline stated as "within 24 hours of the incident" is only meaningful once the
incident has a time. The check extracts the trigger date — and time of day where the
document gives one — from the case study, and every relative deadline is resolved
from it via the existing `services/deadlines.resolve_due_at`.

Where the case study states no date, the check falls back to the upload time and
records which of the two it used (`incident_source`), so the report can say so rather
than implying a precision it does not have.

## Data model

Migration `0004`.

```
compliance_checks
  id, document_id -> documents.id (cascade delete)
  filename, file_type
  status            pending | processing | done | failed
  error_message
  uploaded_at
  incident_at       datetime, nullable
  incident_source   "stated" | "upload_time"
  evidence_text     the parsed case-study text

check_findings
  id, check_id -> compliance_checks.id (cascade delete)
  kind              "obligation" | "deadline"
  source_id         the obligation/deadline row this came from
  section_id        source section in the compliance document
  requirement       text snapshot of the requirement as checked
  verdict, evidence, note
  due_at, bucket    deadlines only
```

`requirement` is a snapshot on purpose. Re-processing the compliance document
replaces its obligation rows; without the snapshot an old report would silently
change or lose its rows.

## Processing

`services/compliance_check.run_check(check_id, path)`, run as a background task the
same way `process_document` is:

1. Parse the case study with `docling_parser`. No readable text → status `failed`
   with a message the user can act on.
2. Extract the incident datetime; fall back to upload time.
3. Load the compliance document's obligations and deadlines.
4. Batch them (8 per call, matching extraction's batching).
5. Evidence per batch: the whole case-study text when it is under 12,000 characters
   — which covers a normal incident record — otherwise the best-matching passages by
   BM25. The threshold is the cheap path and the fallback in one branch, not two
   code paths.
6. One structured LLM call per batch returns a verdict per requirement, constrained
   by `Literal` + strict json_schema exactly as `extraction.extract_batch` is.
7. Deadlines additionally get `due_at` and `bucket`.
8. Persist findings; mark the check `done`.

A batch whose call fails or comes back unmatchable stores its requirements as
`unclear` with a note saying no verdict was reached. A single bad call must not lose
the report, and it must not be reported as non-compliance either.

## Shared code that moves

Two pieces are needed in a second place, so they move once rather than being copied:

- **BM25 ranking** — `_terms`, `_rank` and the stopword list leave `routers/chat.py`
  for `services/retrieval.py`. `chat.py` imports them; behaviour is unchanged.
- **Upload validation** — extension allow-list, magic-byte check, size cap, filename
  byte-trim and the cleanup-on-failure path leave `routers/upload.py` for a
  `save_upload()` helper. Both upload endpoints call it, so the case-study upload
  cannot drift from the document upload's protections.

## API

All routes are owned through the parent document, the same check every other router
makes.

```
POST   /api/compliance-checks/{doc_id}        multipart upload -> 201 {id, status}
GET    /api/compliance-checks/{doc_id}        checks for this document
GET    /api/compliance-checks/item/{check_id} one check with its findings
DELETE /api/compliance-checks/item/{check_id} 204
```

## Frontend

A **Compliance Check** tab on the document page, beside Deadlines.

- **Empty:** an upload control — "Upload a case-study document to check it against
  this document."
- **Running:** the polling the detail page already does while a document processes.
- **Done:** a header (case-study name, incident time, whether that time was stated in
  the document or assumed from the upload, and the verdict counts), then findings
  grouped as **Deadlines to meet** (due time, time remaining, verdict), **Not done**,
  **Partly done**, **Done / maintain**, with an `unclear` group last. A verdict
  filter, and every row links back to its source section in the compliance document.

## Sample documents

No sample currently states a deadline shorter than a day, so hour and minute
handling has nothing to demonstrate against. Two new samples, generated with
`python-docx` (already installed; `.docx` is an accepted upload type, so no new
dependency and no new file format):

1. **Kanangra Court — Incident Escalation Protocol.** Carries deadlines at
   "within 30 minutes", "within 4 hours", "within 24 hours", "within 2 business days"
   and "within 30 days and 4 hours of the incident".
2. **Kanangra Court — Case study: medication error, Resident K.** The evidence
   document for a check against (1): states the incident date and time, records some
   escalation steps as done, leaves others undone.

Both carry the same `SAMPLE — fictional document for demonstration` marking the
existing samples use, and the generator script is committed beside them.

## Testing

- `find_incident_datetime`: date with time, date alone, no date at all.
- Evidence selection: a short case study passes whole; a long one goes through BM25.
- `run_check` with a mocked LLM (`MagicMock`, the `test_processing.py` pattern):
  findings persisted per requirement, deadlines carry `due_at` counted from the
  incident, a failed batch degrades to `unclear` rather than losing the check.
- Endpoints: ownership 404s, upload rejection paths still enforced through the
  shared helper, check deletion.
- Frontend: `tsc --noEmit` clean; the tab renders each verdict group.

## Out of scope

- Editing a verdict by hand, or re-running a check against a changed case study.
- More than one case study compared to each other.
- An overall compliance score or percentage.
- Checking risks and action items — obligations and deadlines only in this pass.
