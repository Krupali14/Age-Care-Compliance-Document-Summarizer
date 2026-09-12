# 08 — Evaluation

Extraction is a language model reading a legal document. That is worth measuring.
Full reference: **`docs/EVALUATION.md`**. This is the summary.

## Two different questions

| | Automatic self-check | Ground-truth run |
|---|---|---|
| Needs annotation? | No | Yes |
| Runs | Automatically, on every document | On demand |
| Answers | "Did it invent things? Did it skip stretches?" | "Did it find the right things?" |
| Metrics | Grounding · Coverage · Overall | Precision · Recall · F1 |
| `ground_truth_ref` | `"auto"` | a file path, or `"api"` |

Both write an `EvalRun`, both appear in the same history, and the UI **labels them
differently on purpose**. Calling a self-check "precision" would claim a comparison
that never happened.

## The automatic self-check

Nobody has annotated the document a user uploaded ninety seconds ago. These two
measures need only the document and what was extracted from it.

### Grounding — the check against invented content

> Of the findings extracted, what share have wording actually carried by the section
> they cite?

```python
fuzz.token_set_ratio(finding_text, its_section_text) >= 55
```

The threshold is deliberately far below an exact match — summarising rewords things,
and catching paraphrase is not the point. What it catches is a finding whose words
appear **nowhere in its source**. In a compliance tool a fabricated obligation is
worse than a missing one.

### Coverage — the check against silent gaps

> Of the sections worth extracting (≥40 chars), what share produced at least one
> finding?

**Low coverage is not automatically wrong.** A page of definitions carries no
obligations. What coverage catches is a *drop* — stretches producing nothing where
comparable stretches produced plenty. That is the shape of a failed batch, a schema
the model quietly ignored, or a parse that ran off the rails.

> Coverage is precisely the signal that would have caught the batching bug in
> [05](05-processing-pipeline.md) on the day it appeared: 31 sections, a summary on
> every one, zero findings on every one.

### Overall

Harmonic mean of the two. Low when *either* is low — findings that are all grounded
but cover a tenth of the document are not a good result, and neither is the reverse.

## The ground-truth run

A prediction matches a truth when `fuzz.token_sort_ratio(...) >= 75` —
word-order-insensitive, so "report the incident within 24 hours" matches "within 24
hours, report the incident". Matching is **greedy and one-to-one**, so ten
near-identical predictions cannot all claim the same truth.

- **Precision** = matched predictions / all predictions — how much of what it found was real
- **Recall** = matched truths / all truths — how much of what was there it found
- **F1** = their harmonic mean

The four category scores are averaged unweighted — a judgement, not a law.

### The ground-truth file

```json
{
  "obligations": ["The provider must report every reportable incident within 24 hours."],
  "risks": ["Recurrence of fall due to wet flooring without adequate signage"],
  "deadlines": ["Lodge SIRS notification within 24 hours"],
  "action_items": ["Complete post-incident clinical review"]
}
```

Only the categories present are scored. An empty object is refused with a 400 rather
than dividing by zero.

## Running it

**On screen** — open a document → *Evaluation results*. The self-check fires on its
own the first time a processed document's results are opened (a `useRef` guard stops
a re-render or the mutation's own refetch from firing it twice). *Re-evaluate*
re-runs it. Each run is a card: three percentages colour-coded green ≥80 / amber ≥50
/ red below, the run's source, and a timestamp, newest first and tagged `latest`.

**Over the API** — `POST /api/documents/{id}/eval/auto` (409 unless `done`), or
`POST /api/documents/{id}/eval` with ground truth.

**From the command line**

```bash
docker compose exec backend python scripts/eval.py 42 ground_truth/doc42.json
# OVERALL: precision=0.81 recall=0.64 f1=0.72
```

The script and the API call the same `run_eval()`, so a number from CI and a number
on screen cannot drift apart.

## A real reading

Sunrise Grove Incident Management Policy — 82 sections, 75 obligations, 6 risks,
34 deadlines:

```
Grounding 91%   Coverage 59%   Overall 71%
```

- 91% grounding: nearly every finding's wording is carried by its cited section.
  The remainder is worth spot-checking, not panicking over.
- 59% coverage: four in ten sections produced nothing. For a policy with
  definitions, scope statements and a document-control table, that is expected.
- 71% overall: a plausible score for a good run on this kind of document.

## Reading results honestly

- **Grounding below ~0.8 is the one to stop for.** But check the failing sections
  before touching prompts: a parse that mis-assigned text to a heading produces the
  same symptom as a hallucinating model, and the fix is entirely different.
- **Coverage is a comparison, not a target.** Read it against comparable documents
  and against the same document's previous runs — not against 100%.
- **A single ground-truth run is an anecdote.** Annotate several, of different kinds,
  before concluding anything about a prompt change.
- **Neither metric checks legal correctness.** Grounding proves the words came from
  the document. It cannot tell you the model read a provision the way a compliance
  officer would.
