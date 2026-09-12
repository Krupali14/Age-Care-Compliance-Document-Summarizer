# 06 — AI and retrieval

Where the model is used, what it is asked, and how the assistant finds the right
part of a 654-page Act.

## Every place a model is called

| Call | Where | How often | Purpose |
|---|---|---|---|
| Relevance gate | `extraction.check_relevance()` | once per upload | Is this compliance material? |
| Batch extraction | `extraction.extract_batch()` | once per batch of ≤8 sections | Summary + findings |
| Retry extraction | same, smaller batches | only for gaps | Recover skipped sections |
| Chat answer | `routers/chat.chat()` | once per question | Answer from retrieved passages |

Nothing else touches a model. There are **no embeddings** and **no vector store**.

## The client — `services/llm.py`

```python
@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        base_url=settings.llm_base_url,      # provider is swappable
        api_key=settings.llm_api_key,
        model=settings.llm_model,            # gpt-4o-mini
        temperature=0,                       # extraction is not a creative task
        rate_limiter=InMemoryRateLimiter(requests_per_second=1.3, max_bucket_size=4),
        max_retries=8,
        timeout=180,
    )
```

One cached client for the whole process: a fresh `ChatOpenAI` per call builds a
fresh connection pool and pays the TLS handshake again, which is measurable across
hundreds of concurrent calls.

`LLM_BASE_URL` means any OpenAI-compatible endpoint works. The repository's
`.env` carries a commented-out NVIDIA NIM configuration as evidence that this is
real, not theoretical.

---

## Extraction prompting

`PROMPT_TEMPLATE` in `extraction.py`. Three things about it are deliberate:

**1. Instructions first, sections last.** The instruction block is identical across
every call in a document, so it forms a stable prefix the API can serve from its
prompt cache.

**2. It says what *not* to do, specifically.**

> *If a section's text is only a heading, a cross-reference, or a table-of-contents
> entry with no substantive content, return an empty summary and no obligations,
> risks, deadlines or action items for it. Never describe what a section probably
> contains or what its title suggests — summarise only text you were given.*

That last clause exists because a model handed a heading will happily invent the
section under it.

**3. Deadline rules are explicit about time.**

> *Never output a date that has already passed. Commencement dates, past amendments,
> historical reporting periods and superseded dates are not deadlines — omit them.*

Today's date is interpolated into the prompt, and `normalize_due_date()` enforces
the same rule again in code afterwards. Belt and braces, because "showing a 2019
commencement date as due" was a real complaint.

### The output schema is the safety mechanism

```python
class IndexedSectionExtraction(SectionExtraction):
    index: int
    heading: str
    obligations: list[ExtractedObligation]   # no default — required
    risks: list[ExtractedRisk]
    deadlines: list[ExtractedDeadline]
    action_items: list[ExtractedActionItem]
```

Required, and enforced with `method="json_schema"` (OpenAI strict structured
outputs). The full story of why is in [05](05-processing-pipeline.md) — in short, an
optional list is a list the model silently drops under batching, and a default turns
that into a confident zero.

`index` + echoed `heading` are how a batched response is proved to belong to the
sections it claims. Anything that fails that check is discarded and retried alone.

One tolerance is built in: models routinely return the Markdown-bullet summary as a
*list of strings* instead of one block. Rejecting that would cost the whole batch its
result, so `_coerce_summary` joins it instead.

---

## Retrieval — how the assistant finds the answer

`routers/chat.py`. This is the part that was rebuilt, and the reasoning matters.

### What it used to do, and why it failed

Ranking was `rapidfuzz.token_set_ratio(question, section_text)` — **string
similarity**, which measures how alike two strings look, not whether one answers the
other. Similarity peaks when two strings are the same length, so short headings beat
the long provisions holding the answers:

| Question, against the 1304-section Act | Retrieved | Context given to the model |
|---|---|---|
| "What deadlines are mentioned?" | three headings | **293 characters** |
| "What are the major risks?" | two outline sections | 4089 chars, off-topic |

With 293 characters of headings as its only source, the model answered *"I don't
know"* — correctly. **The bug was never the model or the API connection.** Retrieval
handed it nothing to read.

### What it does now — three mechanisms

#### 1. BM25 over the document's own text

```
score(term) = idf(term) · tf·(k1+1) / (tf + k1·(1 − b + b·len/avg_len))
```

Three quantities the old approach threw away:

- **idf** — how rare the term is *in this document*. On an aged-care Act, matching
  "care" means nothing; matching "deadline" means a great deal.
- **tf** with saturation — a section repeating a word twenty times does not beat one
  using it five times in context.
- **length normalisation** — a long section is *discounted* for its length, not
  rewarded.

Stop-words are stripped from the question first ("what", "are", "the" match
everything equally). Pure Python, no index, no dependency: ranking 3,777 passages
takes 0.02–0.16 s. A retrieval step with no network hop cannot fail independently.

#### 2. Extracted findings are retrievable passages

Even with BM25, *"What are the major risks?"* failed on documents that state duties
without ever using the word "risk". The answer existed — extraction had already
found and filed those risks — but no section contained the search term.

So the findings are indexed alongside the sections:

```
Obligation: <text>. Responsible: <role>.
Risk (high severity): <text>
Deadline: <description>. Due: <date>. Responsible: <role>.
Required action: <text>. Timeframe: <timeframe>.
```

Each is tied to the section it came from, so citations still point at real text.

#### 3. Category questions get guaranteed slots

When a question names a category — `obligation`, `risk`, `deadline`, `action` and
their synonyms — up to three of that category's findings are guaranteed a place in
the context, ahead of pure term matching.

### The result

On the Aged Care Act 2024 (1304 sections, 2671 findings, 3777 passages):

| Question | Before | After |
|---|---|---|
| What are the key compliance obligations? | *I don't know.* | 4 obligations, cited |
| What are the major risks? | *I don't know.* | risks with severities, cited |
| What deadlines are mentioned? | *I don't know.* | deadlines with due dates, cited |
| What actions are required? | *I don't know.* | required actions, cited |
| What happens if a provider fails to report an incident? | — | "…civil penalty of 250 penalty units", cited |

### The answering prompt

The original instruction — *"Answer using only the excerpts. If the answer isn't in
the excerpts, say you don't know."* — was read as a **lookup** instruction. Asked to
*summarise*, the model refused: no excerpt contained a ready-made summary.

It now says the excerpts are the only permitted source but that it may summarise,
combine and draw conclusions from them, and that passages labelled Obligation / Risk
/ Deadline / Required action are part of the document. Grounding is unchanged; the
spurious refusals stopped.

### Where BM25 will not reach

BM25 matches terms, not meaning. *"Who signs off on restraint use?"* will not find a
section that only says *"authorised by the delegate"*. If paraphrased questions
become common, embed the same passage list and blend the two scores — the passage
list is already the right unit of work for that. It is not done now because it would
add a vector store, an embedding call per document, and a second thing to keep warm,
to fix a problem that has not yet been observed.

---

## Cost and safety controls

| Control | Value | Why |
|---|---|---|
| Relevance gate | 1 call | An out-of-scope upload costs 1 call, not ~200 |
| Batching | ≤8 sections / call | 5.6–7× fewer calls |
| Rate limiter | 1.3 rps | Stays under the TPM ceiling; retrying 429s was measurably worse |
| Question cap | 2000 chars | Server-enforced; an unbounded paste reached the model verbatim before |
| `temperature` | 0 | Extraction is not a creative task |
| Model | `gpt-4o-mini` | Cheap enough for 186 calls per document, capable enough for structured extraction |

## What the model is never trusted with

- **Authorisation.** Ownership is a database query, never a prompt.
- **Provenance.** `section_id` comes from the pipeline, not the model's word.
- **Dates.** `normalize_due_date()` re-checks every date in code.
- **Identity.** The JWT's `email` claim is display-only; `sub` is re-loaded per request.
