# 14 — Known limitations and what comes next

An honest list. Everything here is known, deliberate, and unfixed.

---

## Product limits

| Limitation | Detail |
|---|---|
| **One file per upload** | Dropping several uploads the first and says so. No bulk ingest |
| **PDF and DOCX only** | No images, no plain text, no HTML, no email |
| **25 MB ceiling** | `MAX_UPLOAD_MB` |
| **No cross-document view** | Every screen is one document. No "all deadlines across our policies", which is the obvious next feature |
| **No export** | Findings cannot be downloaded as CSV, Excel or PDF. For a compliance manager whose next step is a spreadsheet, this is the most-missed feature |
| **No editing** | A wrong finding cannot be corrected, dismissed or annotated. It is a read-only view of what the model produced |
| **No tracking** | It extracts obligations; it does not track whether they were met. Not a compliance register |
| **No teams** | One account is one person. No sharing, roles or organisations |
| **English only** | Prompts and parsing assume English |
| **No reprocessing** | Improving a prompt does not update existing documents; they must be deleted and re-uploaded |

## Technical limits

| Limitation | Consequence | Fix |
|---|---|---|
| **Background tasks, not a queue** | No retry after a crash, no visibility, no horizontal scale; extraction competes with request handling. **A restart abandons every in-flight document** — recovered at startup by failing them with a reason, but the work is lost and must be re-uploaded | Celery/RQ/arq — the first thing to change for production ([D9](12-design-decisions.md)) |
| **Concurrent uploads queue invisibly** | Ten at once serialise behind one process-wide rate limiter; each card reads "Reading" with no queue position or estimate | Comes with the queue work |
| **Rate limits per process** | Multiply behind multiple workers | Redis-backed store ([D11](12-design-decisions.md)) |
| **No caching of extractions** | The same document uploaded twice is extracted twice, at full cost | Hash the file, reuse the result |
| **Whole-document load** | `GET /api/documents/{id}` returns all 1304 sections in one response | Paginate the sections tab |
| **No pagination anywhere** | 1914 obligations render as one list | Virtualise or paginate |
| **Retrieval is lexical** | Paraphrased questions miss ([D5](12-design-decisions.md)) | Embeddings blended with BM25 |
| **Chat has no memory** | Each question is retrieved and answered independently; "and who signs that off?" has no antecedent | Feed the transcript into retrieval |
| **Summary is concatenated** | Section summaries joined in order, not synthesised into a document-level summary | A second pass over the section summaries |
| **Only the PKs and `users.email` are indexed** | Fine at current sizes | Index `document_id` when a query is measurably slow |
| **Uploads never cleaned up** | The volume grows forever | Delete the file when the document is deleted |

## Quality limits

- **Extraction is as good as the model.** `gpt-4o-mini` was chosen for cost across
  ~186 calls per document. A stronger model would extract better and cost more; that
  trade has not been measured.
- **No ground-truth set exists in the repository.** Every number reported so far is
  from the automatic self-check. Nobody has annotated a document and measured true
  precision and recall.
- **Coverage varies legitimately by document type**, so there is no absolute
  threshold that means "good". Comparison is the only honest reading.
- **Grounding cannot see legal correctness.** It proves the words came from the
  document. It cannot tell you the model read a provision the way a compliance
  officer would.
- **Risks are under-extracted on standards documents.** A standards document states
  duties, not risks, and the prompt forbids invention. Correct behaviour, but it
  reads as a gap.

## Security gaps

Summarised from [09](09-security.md) — the ones that block production:

1. **No HTTPS** in this stack. Terminate TLS at a proxy.
2. **Token in `localStorage`** — readable by any XSS.
3. **No MFA, no password reset, no account lockout** beyond rate limiting.
4. **No audit log** — no record of who read or deleted what.
5. **Uploads unencrypted at rest.**
6. **No virus scanning** of uploads.
7. **Prompt injection unmitigated** — a crafted document can steer its own
   extraction. Bounded by citations and grounding, not prevented.
8. **No PII handling policy.** The samples are synthetic. The moment a real incident
   report is uploaded, this is health information about identifiable people, and the
   Privacy Act 1988 and the Australian Privacy Principles apply. **This is the
   blocker for real use, not a nice-to-have.**

## Testing gaps

- No frontend unit layer (no Vitest/RTL) — component behaviour is covered E2E.
- Chromium only; no Firefox or WebKit.
- No visual regression testing.
- No load or concurrency testing.
- The E2E suite needs a real API key and costs money to run.
- `npm run lint` is declared but ESLint is not installed or configured.

---

## What I would do next, in order

**1. Export.** CSV or Excel of obligations and deadlines. The single highest
value-per-hour item — a compliance manager's next step after reading the screen is
always a spreadsheet.

**2. A real queue.** Celery or arq. Buys retries, visibility and horizontal scale,
and takes extraction out of the API process. The prerequisite for more than one
concurrent user.

**3. A ground-truth set.** Annotate three or four documents of different kinds, put
them in the repository, and run `scripts/eval.py` in CI. Until this exists, no
prompt change can be shown to be an improvement rather than a change.

**4. Cross-document views.** "Every deadline across our policies, by date." The
data model already supports it; only the UI is missing.

**5. Editing and dismissal.** Let a user mark a finding wrong. That feedback is also
the cheapest ground truth there is.

**6. The security baseline** — TLS, audit logging, a PII policy — before any real
document is uploaded.

**7. Hybrid retrieval.** Embeddings blended with BM25, once paraphrased questions
are an actual complaint rather than a hypothetical one.
