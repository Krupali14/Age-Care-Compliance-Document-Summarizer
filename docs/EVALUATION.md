# Evaluation results: what the numbers mean and how to run them

Extraction is a language model reading a legal document. That is worth measuring,
and the app measures it two different ways — because there are two different
questions, and only one of them can be answered without a human first writing down
the right answers.

| | Automatic self-check | Ground-truth run |
|---|---|---|
| Needs annotation? | No | Yes |
| Runs | On every document, automatically | On demand |
| Answers | "Did it invent things? Did it skip stretches?" | "Did it find the right things?" |
| Metrics | Grounding · Coverage · Overall | Precision · Recall · F1 |
| `ground_truth_ref` | `"auto"` | file path, or `"api"` |

Both write an `EvalRun` row, both appear in the same history, and they are
**labelled differently in the UI on purpose**. Calling a self-check "precision"
would imply the findings had been compared against something they weren't.

Code: `backend/app/services/eval_scoring.py` ·
API: `backend/app/routers/eval.py` · UI: `frontend/src/pages/EvalPage.tsx`

---

## 1. The automatic self-check

`run_auto_eval(db, document_id)`

Nobody has hand-annotated the document a user uploaded ninety seconds ago. These
two measures need only the document and what was extracted from it, so they can run
the moment processing finishes.

### Grounding — the check against invented content

> Of the findings extracted, what share have wording actually carried by the
> section they cite?

```python
fuzz.token_set_ratio(finding_text, source_section_text) >= 55
```

Every obligation, risk, deadline and action item is compared against the raw text
of its own `section_id`. The threshold is **55**, deliberately far below an exact
match: summarising rewords things, and the point is not to catch paraphrase. What
it catches is a finding whose words appear nowhere in its source — the failure that
matters, because a fabricated obligation in a compliance tool is worse than a
missing one.

Zero findings scores `0.0`: nothing was invented, but nothing was supported either.

### Coverage — the check against silent gaps

> Of the sections that were worth extracting, what share produced at least one
> finding?

The denominator is sections of **40 characters or more** — matching
`processing.EXTRACTABLE_MIN_CHARS`, since shorter sections are never sent to the
model and counting them would understate coverage.

**Low coverage is not automatically wrong.** A page of definitions carries no
obligations, and a standards document's front matter carries nothing at all. What
coverage catches is a *drop* — stretches of a document that produced nothing where
comparable stretches produced plenty. That is the shape of a failed batch, a
schema the model quietly ignored, or a parse that ran off the rails.

> Coverage is exactly the signal that would have caught the batching bug described
> in `PROCESSING_PIPELINE.md` §3 on the day it appeared: a document whose every
> section says "The provider implements a system to…" scored a summary on all 31
> sections and zero findings on all of them.

### Overall

The harmonic mean of the two — the same shape as F1. It is low when *either* is
low, which is the intended behaviour: findings that are all grounded but cover a
tenth of the document are not a good result, and neither is the reverse.

```python
overall = 2 · grounding · coverage / (grounding + coverage)
```

---

## 2. The ground-truth run

`run_eval(db, document_id, ground_truth, ground_truth_ref)`

When someone *has* written down the right answers, the standard retrieval metrics
apply.

A prediction and a ground-truth item are counted as the same finding when

```python
fuzz.token_sort_ratio(predicted, truth) >= 75
```

— word-order-insensitive, so "report the incident within 24 hours" matches
"within 24 hours, report the incident". Matching is **greedy and one-to-one**: each
ground-truth item is consumed by at most one prediction, so ten near-identical
predictions cannot all claim the same truth.

Then, per category:

- **Precision** = matched predictions / all predictions — *how much of what it
  found was real.*
- **Recall** = matched truths / all truths — *how much of what was there it found.*
- **F1** = their harmonic mean.

The four category scores are averaged unweighted into the run's headline numbers.
This treats a document's deadlines as equally important to its obligations
regardless of count, which is a judgement, not a law — weight by category size
instead if that suits your data better.

Both empty scores `1.0` (correctly found nothing); one side empty scores `0.0`.

### The ground-truth file

A JSON object keyed by category. Only the categories present are scored:

```json
{
  "obligations": [
    "The registered provider must report every reportable incident to the Commission within 24 hours.",
    "The provider must notify the resident's next of kin as soon as practicable."
  ],
  "risks": [
    "Recurrence of fall due to wet flooring without adequate signage"
  ],
  "deadlines": [
    "Lodge SIRS notification within 24 hours"
  ],
  "action_items": [
    "Complete post-incident clinical review"
  ]
}
```

An empty object is refused with a 400 rather than dividing by zero.

---

## 3. Running an evaluation

### On screen

Open a document → **Evaluation results** (top right) →
`/dashboard/documents/{id}/eval`.

- The **first time** the page is opened for a processed document with no runs, the
  automatic self-check fires on its own. A `useRef` guard stops a re-render or the
  mutation's own refetch from firing it twice.
- **Re-evaluate** re-runs it against the current extraction — useful after
  reprocessing.
- Each run is a card: three metrics as percentages, the run's source
  (`Automatic self-check`, or the ground-truth reference), and a timestamp. Newest
  first, tagged `latest`.
- Metrics are colour-coded — green ≥ 80%, amber ≥ 50%, red below.
- The note under the newest card explains which pair of metrics is being shown, so
  a self-check is never mistaken for a ground-truth score.

Documents that are still processing, `failed` or `unsupported` show an explanation
instead of a button. Evaluating them would score nothing against nothing.

### Over the API

```bash
# Automatic self-check — no ground truth needed
curl -X POST http://localhost:8002/api/documents/42/eval/auto \
     -H "Authorization: Bearer $TOKEN"

# Ground-truth run
curl -X POST http://localhost:8002/api/documents/42/eval \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"ground_truth": {"obligations": ["…"], "risks": ["…"]}}'

# History, newest first
curl http://localhost:8002/api/documents/42/eval \
     -H "Authorization: Bearer $TOKEN"
```

All three enforce document ownership: another account's document is a 404, not a
403 — the existence of the document is not disclosed.

`POST /eval/auto` returns **409** unless the document's status is `done`.

### From the command line

```bash
docker compose exec backend python scripts/eval.py 42 ground_truth/doc42.json
# OVERALL: precision=0.81 recall=0.64 f1=0.72
```

The script and the API call the same `run_eval()`, so a number from CI and a number
on screen cannot drift apart. The run is persisted with the file path as its
`ground_truth_ref`, so the history shows which annotation set produced it.

---

## 4. Reading the results honestly

**Grounding below ~0.8 is the one to stop for.** It means findings are carrying
wording their source section does not support. Check the failing sections directly
before touching prompts — a parse that mis-assigned text to a heading produces the
same symptom as a hallucinating model, and the fix is entirely different.

**Coverage is a comparison, not a target.** Read it against comparable documents,
not against 100%. A 49-page standards document and a 654-page Act have genuinely
different densities. A run that drops far below the same document's previous run is
the signal.

**A single ground-truth run is an anecdote.** Precision and recall on one annotated
document tell you about that document. Annotate several, of different kinds, before
concluding anything about a prompt change.

**Neither metric checks whether the extraction is legally correct.** Grounding
proves the words came from the document. It cannot tell you the model read a
provision the way a compliance officer would. The in-app disclaimer stands: verify
against the original before acting.

---

## 5. Worth adding next

- **Category-level scores in the UI.** They are computed inside `run_eval` and then
  averaged away; surfacing them would show that recall is fine on obligations and
  poor on deadlines, which the single number hides.
- **A stored ground-truth set** in the repository, so `scripts/eval.py` runs in CI
  and a prompt change that costs five points of recall fails the build.
- **Trend over time.** Every run is already persisted with a timestamp; the page
  lists them but does not plot them.
- **Grounding at the section level**, so the page can name the specific findings
  that failed rather than reporting one percentage.
