# 07 — Frontend guide

React 18 · TypeScript · Vite · Tailwind · React Router 6 · TanStack Query 5.

## Routes

```
/                                       Landing            public
/login                                  Login              public (redirects away if signed in)
/dashboard                              Dashboard          protected ─┐
/dashboard/documents/:id                DocumentDetail     protected  ├ DashboardLayout
/dashboard/documents/:id/eval           EvalPage           protected  │  (header, account
/dashboard/*                            NotFound           protected ─┘   menu, skip link)
*                                       NotFound           public
```

`ProtectedRoute` redirects to `/login` when there is no live token. `Login`
redirects to `/dashboard` when there *is* one — reaching a sign-in form with a live
session and being offered to authenticate over the top of it was a real defect.

## State: three kinds, three homes

| Kind | Where | Examples |
|---|---|---|
| **Server state** | React Query | documents, sections, findings, eval runs |
| **Session** | `AuthContext` | the token, the signed-in email, expiry |
| **Local UI** | `useState` in the owning component | active tab, panel open, splitter width, chat transcript |

No Redux, no global store. The chat transcript is deliberately local: it is not
persisted, and reloading the page starts a fresh conversation.

### React Query polling

Both the dashboard and the detail page poll every 4 seconds **while any document is
`pending` or `processing`**, and stop once none are:

```ts
refetchInterval: (query) =>
  query.state.data?.status === "pending" || query.state.data?.status === "processing"
    ? 4000 : false
```

The detail page not doing this was a bug: opening a document straight after
uploading it — the obvious thing to do — froze on "still being processed" with every
tab at zero until the user thought to reload, long after the server had finished.

### AuthContext

- The token lives in `localStorage`, so a session survives reloads and new tabs.
- `claimsOf()` decodes the payload for `exp` and `email`. **Never for authorisation**
  — the server re-loads the user from `sub` on every request.
- A `setTimeout` logs the user out exactly when the token expires. Delays over
  2³¹−1 ms are skipped, because `setTimeout` stores its delay in a 32-bit int and a
  longer one overflows and fires immediately.
- A 401 on any non-auth request dispatches `auth:expired`, treated the same as
  expiry — the token died early (server restart, rotated secret).
- A `storage` event logs out the other tabs.
- Expiry writes a reason to `sessionStorage`, which `/login` reads once and shows.
  Being bounced to a sign-in form with no explanation reads as lost work.

## `api/client.ts` — the one fetch wrapper

Everything goes through it, and it does four things:

1. Attaches `Authorization: Bearer <token>`.
2. **Extracts the server's own message.** The API explains refusals precisely
   ("Password must be at most 72 bytes", "File is larger than the 25MB limit");
   throwing a raw status meant callers fell back to "something went wrong" and the
   explanation was lost. FastAPI's array-shaped validation errors are unwrapped too.
3. On 401 for a non-auth route, clears the token and fires `auth:expired`. A
   sign-in failure is *not* session expiry — that belongs to the login form.
4. Throws `Error` with readable text, so every caller can render it directly.

## Components worth knowing

### `AIAssistant`
The chat panel (desktop, beside the document) and bottom sheet (phone).

- **Suggestions live in the scroll flow, and follow the conversation.** Two
  mistakes were made here in sequence, and the second is the more interesting one.
  They first sat in a strip pinned above the composer — *fixed chrome*, which costs
  the answer area its height for the whole conversation whether or not you want it.
  Removing that strip fixed the obstruction but deleted the feature: once a
  conversation started there was nothing to click.

  The distinction that matters is **fixed chrome vs. scroll flow**, not *present vs.
  absent*. They now render beneath the newest answer, inside the transcript, under
  an "Ask next" label. They scroll away like any other message and cost the answer
  nothing.

  They are also derived from the document rather than hardcoded — see
  `src/lib/suggestions.ts`. Openers are filtered by what extraction actually found,
  so a document with no deadlines is never offered "What deadlines are mentioned?".
  Follow-ups lead with the sections the **last answer cited** ("What does
  \"14.1 Contractual requirements\" require?"), fall back to categories the
  document has, and drop anything already asked.
- **The transcript auto-scrolls** on every message *and* on the typing indicator, so
  the question lands visibly rather than only when the answer arrives. Without it the
  second answer rendered ~900 px below the fold and the screen looked unchanged.
- **The composer is disabled while a reply is in flight** — `send()` drops anything
  typed then, and doing so silently read as the Enter key being broken.
- `role="log"` + `aria-live="polite"`, so answers are announced.
- Answers render as Markdown; `[data-answer]` marks a finished answer, distinct from
  the typing indicator that shares its bubble styling.

### `DocumentDetail`
Tabs, the section list, the resizable split, focus mode, and the mobile sheet.

- Proper tab semantics: `role="tablist"` / `role="tab"` / `aria-selected` /
  `role="tabpanel"`. The count badge is `aria-hidden` with an `sr-only` "…, 75 items"
  carrying the number into the accessible name.
- Source chips jump to a section: switch to Sections, scroll to it, highlight for
  1.5 s.
- The splitter is mouse-driven and clamped to 50–80%.
- The mobile sheet is `role="dialog" aria-modal="true"`, closes on Escape, and locks
  body scroll while open.

### `Dashboard`
Upload, the document grid, delete.

- Upload is a **real `<button>`** that opens a visually-hidden input. It was a
  `<label>` wrapping a `display:none` input, which is focusable by nobody — there
  was no keyboard path to the application's primary action.
- Cards are `role="link" tabIndex={0}` with Enter/Space handlers and a visible
  focus ring. They were `<div onClick>`, which left everything past the dashboard
  unreachable without a mouse.
- Errors sit in a `role="status"` live region.
- Dropping several files uploads the first and says so, rather than silently
  discarding the rest.

### `ConfirmModal`
Focus starts inside, Escape closes, Tab cycles within, focus returns to the trigger
on close. The reference for how a dialog should behave here.

## Design system — `tailwind.config.js`

| Token | Value | Used for |
|---|---|---|
| `ink` | `#14213D` | Primary text, dark surfaces |
| `parchment` | `#F7F4EC` | Page background — paper, not app-grey |
| `teal` | `#0E7C7B` | Accent, citations, focus |
| `amber` | `#D97706` | Processing, warnings, "unsupported" |
| `coral` | `#DC4C3E` | Errors, destructive actions |
| `sage` | — | Success, "Ready", good scores |

Fonts: **Fraunces** (display), **Inter** (body), **IBM Plex Mono** (filenames,
section references, metadata). The monospace is doing real work — it marks anything
that is a literal quotation from the document.

Status colours are consistent everywhere: amber means in progress, sage means done,
coral means failed. Unknown statuses fall back to a neutral pill with the raw name
rather than rendering unstyled.

## Accessibility, as implemented

Verified by `e2e/accessibility.spec.ts`:

- Skip link to `#main` on every dashboard page.
- The full upload → open-document journey works with the keyboard alone.
- Tab pattern on the document views; live regions for errors, status and answers.
- The account menu has `aria-haspopup`/`aria-expanded`, closes on Escape, and
  returns focus.
- The delete dialog traps and restores focus.
- No page scrolls sideways at 390 px.

## Build and scripts

```bash
npm run dev          # Vite dev server, port 3002
npm run build        # tsc -b && vite build
npm run e2e          # Playwright regression suite
npm run e2e:ui       # ..., interactive
npm run e2e:report   # last HTML report
```

`npm run lint` is declared but ESLint is **not installed and not configured** — see
`docs/VSCODE_SETUP.md` §4 for how to wire it up or remove it. Type checking is real
and enforced: `npm run build` runs `tsc -b` first.
