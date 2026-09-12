# 05 — The processing pipeline

How a file becomes structured findings. This is the summary; the full performance
write-up with every measurement is **`docs/PROCESSING_PIPELINE.md`**.

## The six steps

```
POST /api/upload ─► validate ─► stream to disk ─► 201  (~100 ms)
                                      │
                                      └─► process_document()  (background)
                                            1. parse          0.04 – 0.8 s
                                            2. relevance gate ≈3 s, one call
                                            3. store sections one flush
                                            4. extract        the dominant cost
                                            5. retry gaps
                                            6. persist, status = "done"
```

`backend/app/services/processing.py` orchestrates 1–6.

---

## 1. Parsing — `docling_parser.py`

The single largest optimisation in the codebase.

```python
def parse_document(file_path):
    if file_path.lower().endswith(".pdf") and _has_text_layer(file_path):
        sections = _parse_pdf_text_layer(file_path)   # pypdfium2, no models
        if sections:
            return sections
    return _parse_with_docling(file_path)             # scanned PDF, or DOCX
```

A born-digital PDF already carries its text. Running a layout model and OCR over it
is wasted work:

| Document | Pages | Text layer | docling |
|---|---|---|---|
| Aged Care Act 2024 | 654 | **0.77 s** | ~2 h |
| Strengthened Standards | 49 | **0.16 s** | — |
| 15-page extract | 15 | **0.04 s** | — |

Scanned PDFs (no text layer) and DOCX still go through docling with OCR, so
correctness is not traded away — only wasted work.

Parsing also does three things that pay off later:

- **Strips running headers/footers.** A line in the top or bottom margin of more
  than half the pages is furniture. Left in, the same "obligation" is extracted
  hundreds of times.
- **Detects headings structurally** — `Part 5`, `Division 1`, `92A Definitions`,
  `3.2 Incident reporting` — so a section is a provision, not an arbitrary window.
  Table-of-contents entries (the ones with dot leaders) are excluded.
- **Splits oversize sections** at 6000 characters, so an 858,000-character document
  with no detected headings is never one unsendable section.

## 2. The relevance gate — `extraction.check_relevance()`

One cheap model call before any extraction spend. An invoice costs one call instead
of two hundred, and comes back as `status="unsupported"` with the model's own
one-sentence reason.

The sample is deliberately **half from the front, half from the middle**: a long Act
opens with a cover page and a table of contents, so a front-only sample says little
about what the document is.

The prompt is written to be permissive on purpose. The failure that matters is
rejecting a real compliance document, so when in doubt it answers `is_relevant =
true`. If the gate itself errors, the document proceeds — a broken filter must not
block valid work.

## 3. Sections first

Every `Section` row is created and flushed **before** any extraction, so each finding
can carry a real `section_id`. That ordering is what makes every claim in the
interface traceable to a paragraph.

## 4. Extraction — where the time goes

Six optimisations, each targeting the call count or the overlap:

| # | Optimisation | Effect |
|---|---|---|
| 1 | Skip sections under 40 chars | 198 of 1304 sections never sent, on the Act |
| 2 | Batch up to 8 sections / 6000 chars per call | **5.6–7.0× fewer calls** |
| 3 | 16 concurrent calls (`EXTRACTION_CONCURRENCY`) | Wall-clock tracks calls in flight, not CPU |
| 4 | Pace at 1.3 rps (`EXTRACTION_RPS`) | Retrying 429s measured *slower* than pacing, and exhausted retries dropped sections entirely |
| 5 | One cached `ChatOpenAI` per process | No TLS handshake per call across hundreds of calls |
| 6 | Instructions before section text | Stable prefix, servable from the API's prompt cache |

**Correctness under batching.** Each section is rendered with an explicit index, and
the model must return that index *and* echo the heading. On the way back, an index
that was not in the batch, was returned twice, or is paired with the wrong heading
is dropped — leaving it missing rather than filing one section's findings under
another.

## 5. Retrying the gaps

```python
RETRY_BATCH_SIZES = (4, 1)
```

Anything missing is re-extracted four at a time, then one at a time — a
single-section call has nothing to confuse. Without this pass a long document
silently loses whole stretches. Whatever is still missing is logged as an error with
a count, so the gap is visible rather than silent.

## 6. Persisting

Findings are inserted per section, deadlines normalised on the way in
(`normalize_due_date` drops dates already past, keeps relative phrasing verbatim),
the section summaries are joined in document order into one `Summary`, and the
status flips to `done` in a single commit.

---

## End-to-end timing

15-page extract — 31 sections, 28 extractable, 5 batches:

| Stage | Time |
|---|---|
| Upload → 201 | ≈0.1 s |
| Parse | 0.04 s |
| Relevance gate | ≈3.0 s |
| Extraction | ≈11 s |
| **Total** | **14.1 s** |

Extraction is ~78% — the expected shape once everything else is noise. For the
654-page Act, 186 batches against a 1.3 rps limiter put a floor of ~143 s on the
run regardless of concurrency: the rate limit, not the code, is the binding
constraint at that size.

---

## The batching trap — worth knowing before you change anything

*Found and fixed September 2026. Recorded because it is the kind of bug that comes
back.*

**Symptom.** A standards document whose every section reads "The provider implements
a system to…" came back with a summary and **zero** obligations, risks, deadlines
and actions.

Not a parse failure and not a failed call — every section returned a result, and the
summaries were correct.

**Cause.** The four finding lists were declared with defaults:

```python
obligations: list[ExtractedObligation] = []   # optional in the JSON schema
```

An optional field is one the model may omit. Asked for eight sections at once,
`gpt-4o-mini` omitted all four lists on all eight and returned summaries alone. The
defaults then turned each omission into a confident empty list.

| Schema | Method | Obligations from one 8-section batch |
|---|---|---|
| Optional lists | `function_calling` (the default) | `0,0,0,0,0,0,0,0` |
| Required lists | `json_schema` (strict) | `3,1,2,1,1,2,1,3` |

**Fix.** The lists are re-declared without defaults on `IndexedSectionExtraction`,
and `with_structured_output(..., method="json_schema")` enforces them. "Nothing
here" must now be an explicit empty list.

**The general lesson.** Under batching, every optional field in a structured-output
schema is a field the model will eventually drop — and a default turns that omission
into a fact. Anything the model must actually consider should be required.

> Coverage, in the evaluation, is exactly the metric that catches this class of bug.
> See [08](08-evaluation.md).

## When extraction fails

The pipeline distinguishes three outcomes, because they need different words:

| Outcome | Status | What the user is told |
|---|---|---|
| Some sections extracted, some lost | `done` | Nothing — partial content is still content, and the loss is logged |
| **No** section extracted, from a document that had extractable sections | `failed` | "The document was read, but nothing could be extracted from it. The AI service may be unavailable or rate limited. Try uploading it again in a few minutes." |
| Interrupted by a restart | `failed` | "Processing was interrupted before it finished, most likely by a server restart. Upload the document again." |

The second case is the one that bit: a run where every call was rate-limited out
logged `75 of 75 extractable sections have no result` and then marked the document
`done`. The user saw a green **Ready** badge over six empty tabs, indistinguishable
from a document that genuinely contains no obligations.

Zero results from a document that had sections worth extracting is not a document
with no obligations — it is a document nothing was read from.

The third case exists because extraction runs in a background task, which lives and
dies with the process. A restart used to leave the row on `processing` forever. At
startup nothing is running by definition, so a `lifespan` hook fails anything still
in a working state. That is recovery, not a queue: the work is lost and the document
must be uploaded again.

## Tuning

| Variable | Default | Raise when |
|---|---|---|
| `EXTRACTION_RPS` | 1.3 | The account's TPM ceiling is higher — this is the binding constraint on large documents |
| `EXTRACTION_CONCURRENCY` | 16 | Rarely; the limiter, not the pool, is the bottleneck |
| `MAX_UPLOAD_MB` | 25 | Larger documents are expected |

Raising `EXTRACTION_RPS` above the account's real limit makes processing **slower**,
not faster — that is what optimisation 4 is about.
