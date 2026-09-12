# Aged Care Compliance Summariser

AI-assisted summarisation of aged-care compliance documents — extracting obligations, risks, deadlines, and action items.

This is a structural scaffold: routing, layout, and API stubs are in place. No NLP/LLM logic yet.

## Prerequisites

- Docker + Docker Compose

## Setup

```bash
cp .env.example .env
make up
```

## Access

- Frontend: http://localhost:3002
- Backend health check: http://localhost:8002/health
- Postgres: localhost:5434

## Extraction performance

Documents are parsed from their embedded text layer and extracted in batched,
concurrent LLM calls that are paced to stay under the provider's tokens-per-minute
limit. Measured end to end on an OpenAI `gpt-4o-mini` key with a 200k TPM limit:

| Document | Sections | Time |
| --- | --- | --- |
| Strengthened Aged Care Quality Standards (20pp) | 155 | ~27s |
| Aged Care Act 2024 compilation (858k chars) | 1304 | ~2.6 min |

Tune with `EXTRACTION_RPS` and `EXTRACTION_CONCURRENCY` (see `.env.example`). Raising
`EXTRACTION_RPS` above the account's rate limit makes processing *slower*, not faster.

## Documentation

**New to the project? Start at
[`project-understanding/00-START-HERE.md`](project-understanding/00-START-HERE.md)** —
fifteen files covering what this is, how it is built, why it is built that way, the
data model, every endpoint, the AI and retrieval design, security, testing, and the
known limitations.

Engineering deep-dives:

- [`docs/PROCESSING_PIPELINE.md`](docs/PROCESSING_PIPELINE.md) — upload → extraction
  timing, every optimisation and its measured effect, and how relevant documents and
  sections are identified.
- [`docs/EVALUATION.md`](docs/EVALUATION.md) — what the evaluation metrics mean and
  how to run them from the screen, the API, or the command line.
- [`docs/VSCODE_SETUP.md`](docs/VSCODE_SETUP.md) — editor extensions, and what to do
  about red underlines in Node/React files.

## Makefile targets

- `make up` — build and start all containers
- `make down` — stop and remove containers
- `make build` — rebuild images
- `make logs` — tail logs from all services
- `make migrate` — run Alembic migrations inside the backend container
- `make test` — backend pytest suite
- `make e2e` — start the stack with raised auth limits, then run the Playwright
  regression suite (25 browser tests; needs a real `LLM_API_KEY`)
- `make seed` — placeholder for future seed data script
- `make clean` — remove containers, volumes, and dangling images
- `make restart` — down then up
