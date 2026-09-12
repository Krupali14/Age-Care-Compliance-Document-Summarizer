# 12 — Design decisions

Why the system is this way and not another way. Each entry: the decision, the
alternatives, and what would change it.

---

## D1 — Read the PDF text layer before reaching for OCR

**Decision.** `parse_document` checks whether a PDF carries embedded text and, if it
does, reads it with pypdfium2. Only scanned PDFs and DOCX go through docling's
layout + OCR pipeline.

**Alternative.** Send everything through docling — one code path, always correct.

**Why not.** 0.77 s versus roughly two hours for a 654-page Act. Four orders of
magnitude, for the documents this product actually sees. The fallback keeps scanned
documents working, so no correctness is traded away — only wasted work.

**Revisit when** a text layer turns out to be systematically wrong for some
publisher's PDFs. The fallback is one line away.

---

## D2 — Batch sections into one model call

**Decision.** Up to 8 sections or 6000 characters per call.

**Alternative.** One call per section — simpler, and a bad response damages one
section instead of eight.

**Why not.** 5.6–7× the calls, and the call count is the dominant cost. Two costs
pull against each other: the fixed instruction block repeats per call (favouring few
large calls), while latency tracks tokens *generated* (favouring many small ones run
in parallel). These sizes sit near the floor of that curve.

**The price.** Batching is what made the model drop optional fields (D3), and needs
index + heading verification to prove a response belongs to the sections it claims.

**Revisit when** responses start coming back truncated — that means the batch is
overrunning the output-token limit, and the whole call is lost.

---

## D3 — Every finding field is required in the output schema

**Decision.** `obligations`, `risks`, `deadlines`, `action_items` have no defaults,
and `with_structured_output(..., method="json_schema")` enforces them.

**What happened without it.** An optional field is a field the model may omit. Asked
for eight sections at once, `gpt-4o-mini` omitted all four lists on all eight and
returned summaries alone; the defaults turned each omission into a confident empty
list. A standards document whose every section reads "The provider implements a
system to…" came back with zero obligations.

| Schema | Method | Obligations from one 8-section batch |
|---|---|---|
| Optional | `function_calling` (default) | `0,0,0,0,0,0,0,0` |
| Required | `json_schema` (strict) | `3,1,2,1,1,2,1,3` |

**The general rule.** Under batching, every optional field is one the model will
eventually drop, and a default turns that omission into a fact. Anything the model
must actually consider should be required.

---

## D4 — Pace the calls instead of retrying the 429s

**Decision.** `InMemoryRateLimiter` at 1.3 rps with a 4-call bucket.

**Alternative.** Fire all 16 workers and let `max_retries` handle the rejections.

**Why not.** Measured *lower* throughput — backoff thrash — and calls that exhausted
their retries dropped their sections from the document entirely. Silent data loss is
worse than being slow.

**Consequence.** On the 654-page Act, 186 batches at 1.3 rps put a ~143 s floor on
the run regardless of concurrency. The rate limit, not the code, is the binding
constraint at that size. `EXTRACTION_RPS` is the knob.

---

## D5 — BM25, not embeddings

**Decision.** Retrieval is BM25 in Python over the document's sections and findings.

**Alternative.** Embed every section, store vectors, retrieve by cosine similarity.

**Why not, yet.** BM25 needs no vector store, no embedding call per document,
nothing to keep warm, and no second service that can fail. Ranking 3,777 passages
takes 0.02–0.16 s. It fixed every observed failure.

**What it cannot do.** Match meaning. *"Who signs off on restraint use?"* will not
find a section that only says *"authorised by the delegate"*.

**Revisit when** paraphrased questions become a real complaint. Embed the same
passage list and blend the scores — the passage list is already the right unit.

---

## D6 — Index the extracted findings as retrievable passages

**Decision.** Obligations, risks, deadlines and actions are searchable alongside the
sections, tied to their source section.

**Why.** The four questions the UI suggests ask about exactly what extraction has
already filed — but provisions rarely contain the words "risk" or "deadline". Search
over section text alone missed them, and the assistant answered "I don't know" while
the answer sat in its own database.

**The subtlety.** A finding is one sentence, so on a length-normalised ranking it
outscores the provision it came from. An early attempt to reserve half the context
for full sections made things *worse* — the bulk of unrelated sections drowned three
short risk findings and the model refused. The version that works ranks everything
together and guarantees slots only when the question names a category.

**Recorded because** the failed attempt is not obvious from the final code, and
someone will otherwise try it again.

---

## D7 — Findings carry both `document_id` and `section_id`

**Decision.** Every finding row has both.

**Why.** `document_id` makes "all obligations here" one indexed query.
`section_id` is what makes a finding clickable back to its paragraph. Without the
second, the product is a list of assertions with no provenance — and in a compliance
tool, provenance *is* the product.

---

## D8 — `due_date` is a string

**Decision.** Text, not `Date`.

**Why.** A compliance deadline is often not a calendar date: *"within 30 days of the
incident"*, *"1 month after commencement"*. Those are the useful ones, and a `Date`
column cannot hold them. `normalize_due_date()` keeps future dates and relative
phrasing and drops dates already past.

**The cost.** No date arithmetic in SQL. A real deadline calendar would need a
resolved-date column alongside the phrasing.

---

## D9 — Background tasks, not a queue

**Decision.** `process_document` runs in FastAPI's `BackgroundTasks`.

**Alternative.** Celery, RQ or arq with a worker.

**Why not, yet.** A queue adds a broker, a worker process and a deployment topology
to a project whose entire load is one user uploading one document. `BackgroundTasks`
returns the upload in ~100 ms and does the work after the response, which is the
behaviour that matters.

**What it costs.** No retries after a crash, no visibility, no horizontal scale, and
extraction competes with request handling in the same process.

**And one thing that had to be handled explicitly.** A background task lives and
dies with the process, so a restart mid-extraction left the row on `processing`
forever — the dashboard polled it indefinitely and nothing ever picked the work back
up. Ten documents were found stranded that way after a single restart. A `lifespan`
startup hook now fails anything left in a working state, because at startup nothing
is running by definition. That is *recovery*, not a queue: the work is still lost
and the user is asked to upload again.

**Revisit when** documents are uploaded concurrently by real users. This is the
first thing that should change for production.

---

## D10 — 404, never 403

**Decision.** Another account's document is "not found".

**Why.** A 403 confirms the id exists. Enumeration then tells an attacker how many
documents the system holds and when they were created. 404 says nothing.

---

## D11 — Rate limiting in memory, with the ceiling written down

**Decision.** A dict and a deque in `rate_limit.py`, not Redis.

**Why.** One API container is the entire deployment, so a per-process counter is the
whole truth. Adding Redis to enforce a limit on a single process is a service to
operate for no benefit.

**The ceiling, stated in the module docstring.** Behind a second worker, each
enforces its own share and the effective limit multiplies. Swap the store for Redis
at that point — the call sites do not change.

**Why the docstring matters.** A shortcut with a known limit is engineering. The
same shortcut undocumented is a trap.

---

## D12 — The token lives in `localStorage`

**Decision.** JWT in `localStorage`, sent as a Bearer header.

**Alternative.** httpOnly cookie with CSRF protection.

**Why.** A pure SPA against a separate API origin; no cookie/CSRF machinery, and the
session survives reloads and new tabs for free.

**The cost, plainly.** Any XSS can read the token. The mitigation is that there is
no `dangerouslySetInnerHTML` anywhere and Markdown is rendered by a library that
does not evaluate raw HTML. **If this ever handles real resident data, revisit it** —
see [09](09-security.md).

---

## D13 — React Query only, no global store

**Decision.** Server state in React Query; UI state in the component that owns it;
one context for auth.

**Why.** Almost all state here *is* server state. Polling, caching and refetch
conditions are declared rather than hand-rolled. A Redux store would mostly be a
second copy of what React Query already holds, kept in sync by hand.

---

## D14 — Two evaluation modes, labelled differently

**Decision.** An automatic self-check (grounding/coverage/overall) and a ground-truth
run (precision/recall/F1), sharing one table but never one label.

**Why.** Nobody has annotated the document a user uploaded ninety seconds ago, so a
metric that needs ground truth cannot run — but "did it invent things?" and "did it
skip stretches?" can be answered from the document alone. Calling a self-check
"precision" would claim a comparison that never happened.

**The payoff.** Coverage is exactly the signal that catches D3's failure mode: a
summary on every section and findings on none.

---

## D15 — The E2E suite raises the rate limits rather than lowering them

**Decision.** `make e2e` starts the stack with `LOGIN_MAX_ATTEMPTS=1000
REGISTER_MAX_ATTEMPTS=1000`.

**Alternative.** Set a permissive default and tighten it in production.

**Why not.** The default is the value that ships. A default chosen for the
convenience of the test suite is a production weakness introduced by testing. The
test environment is the thing that should bend.

---

## D16 — Suggested questions belong to the empty state

**Decision.** The chips render only when the conversation is empty; "New
conversation" brings them back.

**Why.** They used to sit in a strip pinned above the composer for the whole
conversation — a fixed panel between the transcript and the input that squeezed
every answer into a narrow band. They are useful for exactly one moment: not knowing
what to ask. After that they are furniture.
