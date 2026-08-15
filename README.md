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

## Makefile targets

- `make up` — build and start all containers
- `make down` — stop and remove containers
- `make build` — rebuild images
- `make logs` — tail logs from all services
- `make migrate` — run Alembic migrations inside the backend container
- `make seed` — placeholder for future seed data script
- `make clean` — remove containers, volumes, and dangling images
- `make restart` — down then up
