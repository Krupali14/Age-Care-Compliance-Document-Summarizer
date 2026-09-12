# Document processing: how it works, and how it was made fast

How a file gets from the upload button to a page of obligations, risks, deadlines
and action items — and where every second of that time goes.

Measured on the machine this project runs on (Docker Desktop, `gpt-4o-mini` over
`api.openai.com`), September 2026.

---

## 1. The path a file takes

```
POST /api/upload ──► validate ──► stream to disk ──► 201 Created  (≈100 ms)
                                       │
                                       └─► BackgroundTasks: process_document()
                                              │
                                              ├─ 1. parse      (0.04 – 0.8 s)
                                              ├─ 2. relevance  (≈3 s, one LLM call)
                                              ├─ 3. sections   (one DB flush)
                                              ├─ 4. extract    (dominant cost)
                                              ├─ 5. retry gaps
                                              └─ 6. persist + status = "done"
```

| File | `backend/app/routers/upload.py` | `backend/app/services/processing.py` |
|---|---|---|
| Parsing | `backend/app/services/docling_parser.py` | |
| Extraction | `backend/app/services/extraction.py` | `backend/app/services/llm.py` |

### Step 0 — Upload (`routers/upload.py`)

The request returns as soon as the bytes are on disk; nothing waits for the LLM.
The response carries `status: "pending"` and the dashboard polls the document
until it reads `done`.

Three things are checked before a byte is stored, because each of them is cheaper
to catch here than to explain later:

- **Extension** — `.pdf` / `.docx` only.
- **Magic bytes** — the first chunk must start with `%PDF-` or `PK\x03\x04`. A
  `.txt` renamed to `.pdf` otherwise fails deep inside the parser with an error no
  user can act on.
- **Size** — the file is streamed in 1 MB chunks and abandoned the moment it
  crosses `MAX_UPLOAD_MB` (default 25). Reading it whole and then checking would
  mean a 2 GB upload costs 2 GB of memory before being refused.

### Step 1 — Parsing (`docling_parser.py`)

This is where the largest single optimisation lives.

`docling` runs a layout model and OCR over every page. That is the right tool for
a scanned document and completely wasted on a born-digital PDF, which already
carries its text.

```python
def parse_document(file_path):
    if file_path.lower().endswith(".pdf") and _has_text_layer(file_path):
        sections = _parse_pdf_text_layer(file_path)   # pypdfium2, no models
        if sections:
            return sections
    return _parse_with_docling(file_path)             # scanned PDF, or DOCX
```

`_has_text_layer()` samples up to 20 pages and asks whether they carry more than
200 characters between them. If they do, the text layer is read directly.

**Measured:**

| Document | Pages | Fast path | docling path |
|---|---|---|---|
| Aged Care Act 2024 compilation | 654 | **0.77 s** | ~2 h |
| Strengthened Quality Standards | 49 | **0.16 s** | — |
| 15-page extract | 15 | **0.04 s** | — |

Roughly four orders of magnitude, for the documents this product actually sees.
Scanned PDFs still fall through to docling with OCR — correctness is not traded
away, only wasted work.

Parsing also does three things that pay for themselves later:

- **Running headers and footers are stripped.** A line appearing in the top or
  bottom margin of more than half the pages is furniture, not content. Left in, it
  is re-extracted on every page and the same "obligation" appears hundreds of times.
- **Headings are detected structurally** (`Part 5`, `Division 1`, `92A Definitions`,
  `3.2 Incident reporting`), so a section is a provision rather than an arbitrary
  character window. Table-of-contents entries — the ones with dot leaders — are
  excluded.
- **Oversize sections are split** at `MAX_SECTION_CHARS = 6000`. A 1.1 M-character
  document with no detected headings would otherwise be one unsendable section.

### Step 2 — The relevance gate

One cheap LLM call, before any extraction spend, asking whether this is compliance
material at all. An invoice or a résumé is marked `unsupported` and costs one call
instead of two hundred.

The sample it sees is deliberately **half from the front and half from the middle**
of the document. A long Act opens with a cover page and a table of contents; a
sample taken purely from the front tells you almost nothing about what the document
is.

The prompt is written to be permissive on purpose — the failure that matters is
rejecting a real compliance document, not accepting a borderline one. When in doubt
it answers `is_relevant = true`. Measured at ≈3 s.

If the gate itself errors, the document proceeds. A broken filter must not block
valid work.

### Steps 3–5 — Extraction

This is where the wall-clock time lives. Everything below exists to reduce the
number of LLM round-trips, or to overlap them.

#### Optimisation 1 — Don't extract what isn't content

```python
EXTRACTABLE_MIN_CHARS = 40
```

A parsed "section" shorter than this is a contents fragment or a stray page number
(`"ii Aged Care Act 2024"`, `"system 77"`). The row is still stored so the document
reads complete, but it is never sent to the model: it wastes a slot and invites the
model to invent a summary from a heading.

On the 654-page Act this removes 198 of 1304 sections before any call is made.

#### Optimisation 2 — Batch sections into one call

```python
MAX_BATCH_SECTIONS = 8
MAX_BATCH_CHARS    = 6000
```

Each call repeats a fixed instruction block, which favours few large calls; a
call's latency tracks the tokens it must *generate*, which favours many small ones.
These sizes sit near the floor of that curve. The ceilings also stop a response
from overrunning the model's output-token limit and coming back as truncated,
unparseable JSON — which loses the entire call.

**Measured call reduction:**

| Document | Extractable sections | Batches | Calls saved |
|---|---|---|---|
| Aged Care Act 2024 | 1106 | 186 | **5.9×** |
| Quality Standards | 141 | 20 | **7.0×** |
| 15-page extract | 28 | 5 | **5.6×** |

#### Optimisation 3 — Run the calls concurrently

```python
max_workers = int(os.environ.get("EXTRACTION_CONCURRENCY", "16"))
```

Extraction is network-bound and each call generates independently, so wall-clock
scales with how many are in flight, not with CPU.

#### Optimisation 4 — Pace, don't retry

```python
rate_limiter=InMemoryRateLimiter(
    requests_per_second=float(os.environ.get("EXTRACTION_RPS", "1.3")),
    max_bucket_size=4,
)
```

Sixteen workers firing at once walk straight into the account's tokens-per-minute
ceiling. Retrying the resulting 429s measured *lower* throughput than pacing, and
calls that exhausted their retries dropped their sections from the document
entirely. The limiter releases calls just under the ceiling instead; the small
bucket absorbs a lull without letting the start of a document burst through.

`EXTRACTION_RPS` and `EXTRACTION_CONCURRENCY` are the two knobs to turn for a
different account tier. They are read from the environment, not hard-coded.

#### Optimisation 5 — One HTTP client for the process

```python
@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI: ...
```

A fresh `ChatOpenAI` per call builds a fresh connection pool and pays the TLS
handshake again. Hundreds of concurrent calls make that measurable.

#### Optimisation 6 — Stable prompt prefix

The instruction block is rendered *before* the section text, so it forms an
identical prefix across every call in a document and the API can serve it from its
prompt cache.

#### Correctness under batching: index + heading echo

Each section in a batch is rendered with an explicit index, and the model must
return that index **and** the heading, copied. On the way back:

- an index that wasn't in the batch, or was returned twice, is dropped;
- a heading that doesn't match the section it claims is dropped, with a log line.

Dropping leaves the index missing rather than filing one section's findings under
another. Missing indices are then re-extracted:

```python
RETRY_BATCH_SIZES = (4, 1)
```

Four at a time first, then one at a time — a single-section call has nothing to
confuse. Without this pass a long document silently loses whole stretches of
content. Anything still missing after both passes is logged as an error with a
count, so the gap is visible rather than silent.

### Step 6 — Persist

Section rows are created and flushed **first**, so every finding can carry a real
`section_id` and every answer in the app can cite its source. Findings are then
inserted per section and the document is marked `done` in a single commit.

Deadlines are normalised on the way in: a date already in the past is not a
deadline (`normalize_due_date()`), while relative phrasing — "within 30 days of the
incident" — is kept verbatim because it names no calendar date.

---

## 2. End-to-end timing

15-page extract, 31 sections, 28 extractable, 5 batches:

| Stage | Time |
|---|---|
| Upload → 201 | ≈0.1 s |
| Parse | 0.04 s |
| Relevance gate | ≈3.0 s |
| Extraction (5 batches, concurrent + paced) | ≈11 s |
| **Total to `status = "done"`** | **14.1 s** |

Extraction is ~78% of it, which is the expected shape: everything else has already
been optimised down to noise. The remaining lever is the call count, which is why
batching is where the tuning constants live.

For the 654-page Act, 186 batches against a 1.3 rps limiter put a floor of roughly
143 s on the run regardless of concurrency — the rate limit, not the code, is the
binding constraint at that size.

### If it needs to be faster

In rough order of payoff:

1. **Raise `EXTRACTION_RPS`** to whatever the account tier allows. This is the
   binding constraint on large documents.
2. **Raise `MAX_BATCH_SECTIONS`** — but watch for truncated JSON responses, and see
   the warning in §3 below about what large batches do to extraction quality.
3. **Persist incrementally** so the UI can show sections filling in rather than
   waiting for one final commit. This changes perceived time, not actual time.
4. **Move `process_document` out of `BackgroundTasks`** into a real queue (Celery,
   RQ, arq). Today it runs in the API process; a queue buys retries, visibility and
   horizontal scale rather than raw speed.

---

## 3. A batching trap worth knowing about

*Fixed September 2026 — recorded because it is the kind of bug that comes back.*

**Symptom.** Some documents showed a summary and nothing else: Obligations 0,
Risks 0, Deadlines 0, Actions 0, on a standards document whose every section reads
"The provider implements a system to…".

**Not** a parse failure and **not** a failed call: every section came back with a
result, and the summaries were correct.

**Cause.** The extraction schema declared the four finding lists with defaults:

```python
obligations: list[ExtractedObligation] = []   # optional in the JSON schema
```

An optional field is a field the model may omit. Asked for eight sections at once,
`gpt-4o-mini` omitted all four lists on all eight and returned summaries alone. The
defaults then turned each omission into a confident empty list. The same sections
extracted one at a time yielded three obligations apiece.

**Evidence** (batch of 8 sections, identical text, same model):

| Schema | Method | Obligations returned |
|---|---|---|
| Optional lists | `function_calling` (default) | `0,0,0,0,0,0,0,0` |
| Required lists | `json_schema` (strict) | `3,1,2,1,1,2,1,3` |

**Fix.** The four lists are re-declared without defaults on
`IndexedSectionExtraction`, and `with_structured_output(..., method="json_schema")`
enforces them. "Nothing here" must now be an explicit empty list rather than a
silent omission.

**The general lesson.** Under batching, every optional field in a structured-output
schema is a field the model will eventually drop — and a default turns that
omission into a fact. Anything the model must actually consider should be required.

---

## 4. How relevant content is identified

Three different mechanisms answer three different questions. They are easy to
confuse.

### (a) Is this document in scope at all?

The relevance gate, above — one LLM call on a front-and-middle sample, deliberately
biased towards acceptance. Sets `status = "unsupported"` and shows the model's own
one-sentence reason.

### (b) Which sections answer this user's question? (`routers/chat.py`)

Ranking is **BM25** over the document's own sections, computed in-process with no
index and no extra dependency.

```python
score(term) = idf(term) · tf · (k1 + 1) / (tf + k1 · (1 − b + b · len/avg_len))
```

Three quantities, each carrying weight the previous approach threw away:

- **`idf`** — how rare the term is *in this document*. On an aged-care Act, a match
  on "care" means nothing and a match on "deadline" means a great deal.
- **`tf`** — how often it occurs in the section, with saturation so a section that
  repeats a word twenty times doesn't beat one that uses it five times in context.
- **length normalisation** — a long section is *discounted* for its length, not
  rewarded.

Stop-words are removed from the question first: "what", "are" and "the" match every
section equally and only add noise. Sections under 40 characters are excluded, in
step with `EXTRACTABLE_MIN_CHARS`. Up to `TOP_K = 6` passages are selected within a
`MAX_CONTEXT_CHARS = 12000` budget.

**What this replaced, and why.** Ranking used to be `rapidfuzz.token_set_ratio` —
string *similarity*, which measures how alike two strings look rather than whether
one answers the other. Similarity peaks when two strings are the same length, so
short headings beat the long provisions that held the answers:

| Question | Old ranking retrieved | Context handed to the model |
|---|---|---|
| "What deadlines are mentioned?" | three headings | **293 characters** |
| "What are the major risks?" | two outline sections | 4089 characters, off-topic |

With 293 characters of headings as its only source, the model answered "I don't
know" — correctly. The bug was never in the model or the API connection; it was
that retrieval handed it nothing to read.

### (c) Questions about categories the document never names

Even with BM25, "What are the major risks?" failed on documents that state duties
without ever using the word "risk". The answer existed — extraction had already
found and filed those risks — but no section contained the search term.

So **extracted findings are indexed as retrievable passages alongside the sections**:

```
Obligation: <text>. Responsible: <role>.
Risk (high severity): <text>
Deadline: <description>. Due: <date>. Responsible: <role>.
Required action: <text>. Timeframe: <timeframe>.
```

Each is tied to the section it came from, so citations still point at real text.
And when a question names a category — `obligation`, `risk`, `deadline`, `action`
and their synonyms — up to `MAX_CATEGORY_PASSAGES = 3` of that category's findings
are guaranteed a place in the context, ahead of pure term matching.

**Result** on the Aged Care Act 2024 (1304 sections, 2671 findings):

| Question | Before | After |
|---|---|---|
| What are the key compliance obligations? | *I don't know.* | 4 obligations, cited |
| What are the major risks? | *I don't know.* | risks with severities, cited |
| What deadlines are mentioned? | *I don't know.* | deadlines with due dates, cited |
| What actions are required? | *I don't know.* | required actions, cited |

Ranking 3777 passages takes 0.02–0.16 s. There is no vector store, no embedding
call and no index to keep warm; on documents of this size BM25 in Python is not the
bottleneck, and a retrieval step with no network hop cannot fail independently.

**When to revisit.** BM25 matches terms, not meaning — "Who signs off on restraint
use?" will not find a section that only says "authorised by the delegate". If
paraphrased questions become common, embed the same passage list and blend the two
scores. The passage list is already the right unit of work for that.

### One more thing the prompt was doing

The chat instruction used to read: *"Answer using only the excerpts. If the answer
isn't in the excerpts, say you don't know."* Asked to *summarise*, the model refused
— no excerpt contained a ready-made summary. It now says the excerpts are the only
permitted source but that it may summarise, combine and conclude from them, and
that passages labelled Obligation/Risk/Deadline/Required action are part of the
document. Grounding is unchanged; the refusals stopped.
