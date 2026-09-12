# 02 — Architecture

## The whole system on one screen

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Browser                                                                 │
│  React 18 · TypeScript · Vite · Tailwind · React Router · React Query    │
│  localhost:3002                                                          │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │  JSON over HTTP, Bearer JWT
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  API — FastAPI on Uvicorn, localhost:8002                                │
│                                                                          │
│   routers/   auth · upload · documents · summarize · obligations ·       │
│              risks · deadlines · actions · eval · chat                   │
│   services/  docling_parser · extraction · processing · llm ·            │
│              eval_scoring                                                │
│   auth.py    JWT issue/verify · bcrypt      rate_limit.py  abuse limits  │
└───────┬───────────────────────────────┬──────────────────────┬───────────┘
        │ SQLAlchemy                    │ BackgroundTasks      │ HTTPS
        ▼                               ▼                      ▼
┌────────────────┐      ┌──────────────────────────┐   ┌──────────────────┐
│ PostgreSQL 16  │      │ process_document()       │   │ OpenAI API       │
│ port 5434      │      │  parse → gate → extract  │   │ gpt-4o-mini      │
│ Alembic        │      │  → retry → persist       │   │ (base URL is     │
│ migrations     │      │  ThreadPoolExecutor ×16  │   │  configurable)   │
└────────────────┘      └──────────────────────────┘   └──────────────────┘
        ▲                                                        ▲
        │                                          paced by InMemoryRateLimiter
        └── uploads/ volume: the original files, for reprocessing
```

## The three containers

`docker-compose.yml` defines exactly three services:

| Service | Image / build | Port | Holds |
|---|---|---|---|
| `db` | `postgres:16` | 5434→5432 | `db_data` volume |
| `backend` | `./backend` | 8002 | `uploads_data` volume; source bind-mounted for reload |
| `frontend` | `./frontend` | 3002 | Vite dev server; source bind-mounted, `node_modules` kept in-image |

The backend container runs `alembic upgrade head` before starting Uvicorn, so a
fresh checkout comes up with a migrated schema and no manual step.

> **The `node_modules` detail matters.** The frontend container keeps its own
> `node_modules` in an anonymous volume so the host's platform binaries do not leak
> in. The consequence is that a package added to `package.json` and installed in the
> container is *absent from the host*, and the editor's TypeScript server then
> cannot resolve it — which looks like every line of every file being wrong. Run
> `npm install` on the host after pulling. See `docs/VSCODE_SETUP.md`.

## Request paths

### Synchronous — everything except upload

```
Browser ──► FastAPI router ──► get_current_user (JWT → User row)
                           ──► _get_owned_document (404 if not yours)
                           ──► SQLAlchemy query
                           ◄── JSON
```

`_get_owned_document` in `routers/documents.py` is the single chokepoint for
ownership. Every document-scoped route calls it first, which is why authorisation
cannot be forgotten on a new endpoint — there is nowhere else to get a document.

### Asynchronous — upload

```
POST /api/upload
  ├─ validate extension, magic bytes, size (streamed in 1 MB chunks)
  ├─ write to uploads/{id}_{filename}
  ├─ insert Document(status="pending")
  ├─ background_tasks.add_task(process_document, id, path)
  └─ 201 {id, filename, status}          ← returns in ~100 ms

                  … meanwhile, after the response is sent …

process_document()
  ├─ status = "processing"
  ├─ parse_document()        → ParsedSection[]
  ├─ check_relevance()       → one model call; "unsupported" ends it here
  ├─ insert every Section, flush to get ids
  ├─ extract in batches, 16 concurrent, paced under the TPM ceiling
  ├─ retry anything the model skipped: 4 at a time, then 1 at a time
  ├─ insert Obligation / Risk / Deadline / ActionItem / Summary
  └─ status = "done"
```

The browser learns it finished by polling `GET /api/documents` (dashboard) and
`GET /api/documents/{id}` (detail page) every 4 seconds while any document is
`pending` or `processing`, and stopping once none are.

## Layering in the backend

```
routers/     HTTP only: parse the request, check ownership, shape the response.
             No business logic, no model calls.
services/    Everything that thinks.
   docling_parser   bytes  → ParsedSection[]
   extraction       text   → SectionExtraction (the model boundary)
   processing       orchestrates the whole pipeline; the only writer of findings
   llm              one cached, rate-limited ChatOpenAI client for the process
   eval_scoring     scoring, shared by the API and scripts/eval.py
models/      SQLAlchemy tables. No behaviour.
schemas.py   Pydantic request validation.
auth.py      JWT and bcrypt.        rate_limit.py   abuse counters.
```

The rule that keeps this honest: **a router never imports `langchain`**. Anything
that reaches the model lives in `services/`. `routers/chat.py` is the one place a
router calls `get_llm()`, and it does so through the service module.

## Frontend structure

```
src/
  main.tsx          React root, StrictMode, BrowserRouter
  App.tsx           every route, QueryClientProvider, AuthProvider
  context/
    AuthContext     the token, the signed-in email, expiry handling
  components/
    ProtectedRoute  redirects to /login when there is no live token
    DashboardLayout header, account menu, skip link, <main id="main">
    AIAssistant     the chat panel / bottom sheet
    CategoryTable   the shared table for obligations, risks, deadlines, actions
    ConfirmModal    focus-trapping confirmation dialog
  pages/
    Landing · Login · Dashboard · DocumentDetail · EvalPage · NotFound
  api/
    client.ts       the single fetch wrapper: attaches the token, extracts the
                    server's own error message, signals session expiry
    auth · documents · extractions · chat · eval
```

Server state is **React Query** only — no Redux, no global store. Local UI state
(which tab, is the panel open, the splitter position) is `useState` in the component
that owns it. The only cross-cutting client state is the auth token, which is one
context.

## How the pieces fail

Each boundary degrades rather than collapsing:

| Failure | Behaviour |
|---|---|
| Parser cannot read the file | `status="failed"`, a message a person can act on; the library's own error (which names internal paths) goes to the log |
| Relevance gate errors | The document proceeds. A broken filter must not block valid work |
| One extraction batch fails | Logged; those sections are retried at 4, then at 1 |
| Sections still missing after retries | Logged as an error with a count — visible, not silent |
| Model call fails during chat | 503 with "try again shortly"; the provider's raw error never reaches the user |
| Background task raises | Caught at the top of `process_document`; the request cycle is already finished and must not be affected |

## Technology choices in one line each

| Choice | Why |
|---|---|
| **FastAPI** | Pydantic validation at the edge and OpenAPI for free at `/docs` |
| **PostgreSQL** | Relational findings with foreign keys to sections; the citation model is relational |
| **SQLAlchemy + Alembic** | Schema in version control, migrations applied on boot |
| **pypdfium2** | Reads a PDF's text layer directly — the fast path, ~0.8 s for 654 pages |
| **docling** | Layout + OCR fallback for scanned PDFs and DOCX |
| **LangChain (`langchain-openai`)** | `with_structured_output` and a rate limiter; the provider is swappable via `LLM_BASE_URL` |
| **React Query** | Polling, caching and refetch conditions declared, not hand-rolled |
| **Tailwind** | The design system lives in `tailwind.config.js`, not in scattered CSS |
| **Playwright** | The bugs that mattered were behavioural — scroll position, keyboard reachability — and only a real browser sees those |

See [12 Design decisions](12-design-decisions.md) for the reasoning in full.
