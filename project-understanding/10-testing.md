# 10 — Testing

Two suites, testing different things, for different reasons.

| Suite | Runner | Where | Speed | Needs a model key? |
|---|---|---|---|---|
| Backend | pytest | `backend/tests/` | ~26 s, 80 tests | No — every model call is mocked |
| End-to-end | Playwright | `frontend/e2e/` | ~6 min | **Yes** — it drives the real pipeline |

## Running them

```bash
make test          # backend: docker compose exec backend python -m pytest tests -q
make e2e           # brings the stack up with raised auth limits, then runs Playwright
```

Or directly:

```bash
docker compose exec backend python -m pytest tests -q
docker compose exec backend python -m pytest tests/test_chat.py -q -k retrieval

cd frontend
npm run e2e                                  # everything
npm run e2e -- --project=desktop             # one project
npm run e2e -- -g "newest answer"            # one test by name
npm run e2e:ui                               # interactive
npm run e2e:report                           # last HTML report
```

> **`make e2e` raises the auth rate limits for the run.** The suite signs up a fresh
> account per test from a single address, which is precisely what those limits exist
> to stop. Raising them for the duration is honest; weakening the production
> defaults would not be. Running `npm run e2e` against a normally-configured stack
> fails at the sixth registration — that is the limit working.

## Backend suite — `backend/tests/`

| File | Covers |
|---|---|
| `conftest.py` | In-memory SQLite on a `StaticPool`, so the client, background tasks and direct writes share one connection. Autouse fixture resets the rate limiter between tests |
| `test_auth.py` | Register, login, token issue/verify, password rules |
| `test_rate_limit.py` | Lockout after the limit; the lockout blocks the *correct* password; one account's lockout does not affect another's |
| `test_input_limits.py` | Email ≤254; chat question ≤2000, and that an over-long one never reaches the model |
| `test_upload.py` | Extension, magic bytes, empty file, size, traversal-safe filename, byte-budget filename trimming, no orphan row when the write fails |
| `test_startup_recovery.py` | Documents stranded by a restart are failed with a reason; finished ones are untouched; a database failure at startup does not stop the app |
| `test_documents.py` | Listing, detail, delete, and cross-account 404s |
| `test_docling_parser.py` | Heading detection, running-header stripping, oversize splitting |
| `test_extraction.py` | Index/heading verification, discarding mis-attributed results, deadline normalisation |
| `test_processing.py` | The pipeline: parse failure → `failed`, relevance gate → `unsupported`, retry of missed sections |
| `test_chat.py` | Retrieval ranks real content above contents scraps; findings are retrievable for category questions; blank question 422; model failure → 503 without leaking; no sections → 409 |
| `test_eval.py` | Scoring maths, the empty-ground-truth 400, auto-eval on a non-`done` document |
| `test_models.py`, `test_config.py` | Schema and settings |

**Model calls are mocked throughout** (`patch("app.routers.chat.get_llm")`), so the
suite is fast, deterministic, free, and runs without a key. The assertions check the
*prompt that was built*, not the model's answer — e.g. that the seeded section text
actually reached the prompt. That is the part the code is responsible for.

## End-to-end suite — `frontend/e2e/`

Playwright, against the real stack: Vite on 3002, FastAPI on 8002, Postgres, and a
real model. Two projects: `desktop` (1440×900 Chrome) and `mobile` (Pixel 5).

| Spec | Tests |
|---|---|
| `auth.spec.ts` | 7 — register/sign-out/sign-in, redirect away from `/login`, short password, duplicate address, stale error cleared, expiry notice, protected route |
| `documents.spec.ts` | 6 — upload→extract→read every tab, out-of-scope refusal, fake PDF, delete with confirmation, cross-account 404, unknown route |
| `chat.spec.ts` | 5 — real answer with citations, auto-scroll, suggestions get out of the way, empty/over-long question, Markdown rendering |
| `evaluation.spec.ts` | 1 — self-check fires on first open, metrics render, re-evaluate adds a run |
| `accessibility.spec.ts` | 7 — mouse-free journey, landmarks and tab pattern, account menu keyboard, dialog focus trap, keyboard-resizable splitter, labelled icon controls, no sideways scroll at 390 px |
| `mobile.spec.ts` | 1 — the assistant sheet opens, locks body scroll, closes on Escape |

**27 tests. All passing.**

### Why these exist in a browser

Every bug this suite covers was invisible to a unit test:

- a panel that never scrolled, so the second answer rendered below the fold
- an upload control with no keyboard path
- document cards that no keyboard could reach
- a detail page that never re-fetched after processing finished
- a bottom sheet that ignored Escape

None of those are wrong *functions*. They are wrong *behaviour in a real browser*,
and only a real browser sees them.

### Conventions

- `workers: 1`, `fullyParallel: false` — tests share one API and its rate limiter.
- Each test signs up its own account (`uniqueEmail`) and uploads its own documents,
  so none depends on another's data.
- `timeout: 180_000` — an upload runs a real extraction, not a stub.
- `trace`, `screenshot` and `video` are retained on failure. When one fails, start
  with `npx playwright show-trace test-results/<name>/trace.zip`.
- Selectors are roles and accessible names (`getByRole("tab", …)`), not CSS classes
  — which means the suite doubles as an accessibility assertion. Where a role will
  not do, a stable `[data-answer]` hook is used rather than a styling class.

### Wait for what you assert, and nothing more

Three upload helpers, with deliberately different contracts:

| Helper | Waits for | Use when |
|---|---|---|
| `upload()` | the card appears | the test is about the interface |
| `uploadAndWait()` | a terminal status | the test asserts on extracted content |
| `openDocument()` | the assistant panel (sections exist, findings need not) | the test is about the document page |

Six accessibility tests originally called `uploadAndWait`, though not one asserts
anything about extracted content — they test a focus ring, a tab pattern, a dialog,
a splitter. Each was therefore made to depend on a real model call behind a shared
rate limiter, and the keyboard-journey test duly failed on a busy machine after 170
seconds while passing in 19 on an idle one. Switching them to `upload()` took that
test to **2.7 s** and made it deterministic.

> **Two lessons, learned the same way.**
>
> **Selecting on styling classes makes a test lie.** The first auto-scroll test
> selected `.rounded-tl-sm` — a Tailwind class shared by the answer bubble *and* the
> typing indicator. It reported "1 answer" while the reply was still in flight, typed
> into the composer, and the app correctly discarded the keystroke. The test failed
> and pointed at the wrong culprit. Hence `[data-answer]`. (It did surface a real UX
> gap: the composer is now disabled while a reply is in flight.)
>
> **Every extra precondition is a way to fail for an unrelated reason** — and a suite
> that fails for unrelated reasons is one people learn to ignore.

## What is not tested

Honestly:

- **Extraction quality.** Whether the model found the *right* obligations is not a
  unit test — that is what [08 Evaluation](08-evaluation.md) is for.
- **Load and concurrency.** No test runs twenty uploads at once.
- **Cross-browser.** Chromium only. Firefox and WebKit would each need a download;
  the specs test layout and behaviour, not engine differences.
- **Visual regression.** No screenshot diffing.
- **The frontend unit layer.** There is no Vitest/RTL suite; component behaviour is
  covered end-to-end instead. For this size of app that is a reasonable trade — the
  E2E suite is the one that has actually caught things.

## Adding a test

**A bug fix gets a test that fails before the fix.** Every regression assertion in
both suites names the defect it guards, e.g.:

```ts
// Regression: the transcript kept its scroll position, so the second answer of
// a conversation rendered ~900px below the fold and the screen looked unchanged.
```

That comment is the point. In a year, when someone is deciding whether an assertion
still matters, the reason it was written is the only thing that answers them.
