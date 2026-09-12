# 09 — Security

What is defended, how, and — just as important — what is not.

## Authentication

| Mechanism | Detail |
|---|---|
| Password storage | bcrypt via passlib. Plaintext is never stored or logged |
| Password floor | 8 characters, enforced client and server side |
| Password ceiling | 72 **bytes** — bcrypt ignores everything past it, so accepting more would be a lie |
| Token | JWT, HS256, `JWT_SECRET` from the environment |
| Lifetime | 480 minutes (`JWT_EXPIRE_MINUTES`) |
| Claims | `sub` (user id), `exp`, `email` |

**The `email` claim is display data only.** `get_current_user` reads `sub` and
re-loads the user from the database on every request, so a tampered claim buys
nothing. Verified: an `alg:none` forged token returns 401.

### Session lifecycle in the browser

The token is in `localStorage`, so a session survives reloads and new tabs. It ends
on its own when it expires (a timer), when a request comes back 401 (the token died
early — server restart, rotated secret), or when the user signs out. Any of those
clears the token, redirects to `/login`, and leaves an explanation. Signing out in
one tab signs out the others.

## Authorisation

**One chokepoint**, `_get_owned_document` in `routers/documents.py`. Every
document-scoped route calls it first, which is why authorisation cannot be forgotten
on a new endpoint — there is nowhere else to obtain a document.

```python
def _get_owned_document(doc_id, db, user) -> Document:
    # 404, never 403 — the existence of another account's document is not disclosed
```

Verified across GET / DELETE / chat / eval: another account's document is a 404.

## Input validation

| Surface | Control |
|---|---|
| Email | Regex, stripped, lowercased, ≤254 chars |
| Password | 8 chars ≤ p ≤ 72 bytes |
| Upload extension | `.pdf` / `.docx` only, case-insensitive |
| Upload content | Magic bytes `%PDF-` / `PK\x03\x04` — a renamed `.txt` is caught here, not deep in the parser |
| Upload size | Streamed in 1 MB chunks, abandoned over `MAX_UPLOAD_MB` (25) |
| Upload filename | `Path(filename).name` — `../../etc/evil.pdf` cannot escape the upload directory |
| Chat question | ≤2000 chars, server-enforced |
| Path parameters | FastAPI type coercion — `/api/documents/abc` is a 422 |

## Rate limiting

`backend/app/rate_limit.py` — a sliding window per key.

| Endpoint | Limit | Window |
|---|---|---|
| Login, per address | 10 | 15 min |
| Login, per IP | 30 | 15 min |
| Register, per IP | 5 | 1 hour |

Three deliberate details:

1. **Counted before the password check**, so a wrong guess is never free and
   bcrypt's cost is not a CPU-exhaustion lever an attacker can pull.
2. **The lockout blocks the correct password too.** If a correct password still
   succeeded during a lockout, the change in response would tell the attacker they
   had found it.
3. **Two axes.** Per-address stops one account being ground through a password list
   from many hosts; per-IP stops one host working through many accounts. Verified:
   one account's lockout does not affect another's sign-in.

> **The ceiling, stated plainly.** Counters are **in memory, per process**. With one
> API container that is the whole truth. Behind a second worker, each enforces its
> own share and the effective limit multiplies. Move the store to Redis at that
> point — the call sites do not change. This is written in the module's docstring so
> it cannot be discovered by surprise.

## Injection

- **SQL** — SQLAlchemy ORM throughout, no string-built queries. Verified:
  `' OR 1=1 --` as a username returns a clean 401.
- **XSS** — React escapes by default. Markdown is rendered by `react-markdown`,
  which does not evaluate raw HTML. There is no `dangerouslySetInnerHTML` anywhere.
- **Prompt injection** — a document *could* contain text instructing the model. The
  blast radius is bounded by what the model is trusted with: it never decides
  authorisation, never supplies a `section_id`, and its date output is re-checked in
  code. The worst outcome is a wrong finding in that document's own results, which
  is what the citations and the grounding metric exist to expose. **This is a real,
  unmitigated risk** and belongs in [14](14-known-limitations.md).

## Error handling

Internal detail never reaches the user:

| Internal | Returned |
|---|---|
| `File format not allowed: 19_report.pdf` (names internal paths) | "This file could not be read. It may be corrupt, password-protected, or saved in an unsupported format." |
| Provider exception from the model call | 503 "The assistant is unavailable right now. Try again shortly." |
| Wrong password vs. unknown account | Identical 401 "Incorrect email or password" |

The real detail goes to the log via `logger.exception`. Verified by test:
`"provider exploded"` does not appear in the 503 response.

## CORS

One origin — `VITE_API_URL_ORIGIN`, default `http://localhost:3002` — with
credentials allowed. No wildcard. Verified: a preflight from `evil.example` is
refused.

## Secrets

`.env`, git-ignored, seeded from `.env.example`. `make setup` generates a random
`JWT_SECRET` if it is still `changeme`. No secret is committed; `LLM_API_KEY` is
read from the environment only.

---

## What is NOT covered

Stated plainly, because a security section that lists only wins is not a security
section.

| Gap | Consequence | Fix when |
|---|---|---|
| **No HTTPS in this stack** | Tokens and passwords travel in clear | Always terminate TLS at a proxy before any real deployment |
| **Token in `localStorage`** | Readable by any XSS. Chosen for a simple SPA with no cookie/CSRF machinery | Move to an httpOnly cookie + CSRF token if the threat model hardens |
| **No refresh tokens** | An 8-hour session, then a full sign-in | Add refresh + rotation for longer sessions |
| **Rate limits are per process** | Multiply behind multiple workers | Redis-backed store before horizontal scaling |
| **No account lockout or MFA** | Sustained distributed guessing is only slowed | Add MFA before real PII lands here |
| **No password reset** | A forgotten password is a dead account | Needs an email provider |
| **No audit log** | No record of who read or deleted what | Required if real resident data is ever handled |
| **Uploads stored unencrypted** | Disk access reveals documents | Encrypt at rest if documents become sensitive |
| **No virus scanning** | A malicious PDF is stored and parsed | ClamAV in the upload path |
| **Prompt injection unmitigated** | A crafted document can steer its own extraction | Bounded by citations + grounding; needs a real defence if untrusted documents are accepted |
| **No PII handling policy** | Aged-care documents may contain resident information | Privacy Act 1988 / APP obligations apply before production use |

The last one is the important one for this domain. The samples are synthetic. The
moment a real incident report is uploaded, the application is handling health
information about identifiable people, and that is a legal regime the code does not
currently address.
