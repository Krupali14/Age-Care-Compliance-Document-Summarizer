# Compliance Check Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a user upload a case-study document inside a compliance document's page and get a verdict (done / not done / partly / unclear) against every obligation and deadline that compliance document carries, with deadlines timed from the incident.

**Architecture:** A `compliance_checks` row owns a parsed case-study text and many `check_findings`. A background task batches the parent document's obligations and deadlines eight at a time, hands each batch the case-study evidence (whole text when short, BM25-selected passages when long) and asks the model for one verdict per requirement. Deadlines are resolved to a `due_at` through the existing `services/deadlines.py`, anchored on the incident time read out of the case study.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic v2, LangChain structured output, pytest; React 18 + TanStack Query + Tailwind; Docker Compose (Postgres).

**Spec:** `docs/superpowers/specs/2026-09-17-compliance-check-design.md`

## Global Constraints

- Every test runs inside the backend container: `docker compose exec -T backend python -m pytest <path> -q`. The host venv is broken (scipy import error) — do not try to run pytest on the host.
- Frontend typecheck: `cd frontend && npx tsc --noEmit -p tsconfig.json`.
- Migrations run with `docker compose exec -T backend alembic upgrade head`. The current head is `0003` (deadline status).
- Ownership is always checked through the parent document with `app.routers.documents._get_owned_document(doc_id, db, user)`. Never trust an id from the URL on its own.
- LLM calls use `app.services.llm.get_llm()` and `with_structured_output(Model, method="json_schema")` — strict structured output, matching `app/services/extraction.py`.
- Verdict values are exactly `done`, `not_done`, `partly`, `unclear`. Statuses on a check are exactly `pending`, `processing`, `done`, `failed`.
- A background task must never raise: every failure path sets `status="failed"` with a user-readable `error_message` and returns.
- Comments explain *why*, in the voice of the surrounding code. No comment that restates the line below it.
- Commit after every task with the trailer `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

---

### Task 1: Move BM25 retrieval into a shared service

The check needs the same passage ranking the chat endpoint uses. Copying it would leave two rankers to fix; it moves out instead, and `chat.py` imports it.

**Files:**
- Create: `backend/app/services/retrieval.py`
- Modify: `backend/app/routers/chat.py` (delete `_WORD_RE`, `_STOPWORDS`, `_K1`, `_B`, `_terms`, `_rank`; import them instead)
- Test: `backend/tests/test_retrieval.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `app.services.retrieval.terms(text: str) -> list[str]`, `app.services.retrieval.rank(query: str, passages: list[str]) -> list[int]` (indices, best first), `app.services.retrieval.STOPWORDS: frozenset[str]`.

Note the signature change: `chat._rank` took `list[tuple[str, Section, str | None]]`. The shared one takes plain strings, so the check can rank case-study passages that have no `Section`. `chat.py` passes `[text for text, _s, _k in passages]`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_retrieval.py
from app.services.retrieval import rank, terms


def test_terms_drops_stopwords_and_single_characters():
    assert terms("What are the deadlines in this section?") == ["deadlines", "section"]


def test_rank_prefers_the_passage_sharing_rare_terms():
    passages = [
        "General information about care and services provided to residents.",
        "The provider must notify the Commission of a reportable incident within 24 hours.",
        "Care plans are reviewed annually.",
    ]
    assert rank("reportable incident notification", passages)[0] == 1


def test_rank_returns_every_index_even_when_nothing_matches():
    passages = ["alpha beta", "gamma delta"]
    assert sorted(rank("zzzz", passages)) == [0, 1]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec -T backend python -m pytest tests/test_retrieval.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.retrieval'`

- [ ] **Step 3: Create the service by moving the code out of chat.py**

Create `backend/app/services/retrieval.py` holding `_WORD_RE`, `STOPWORDS` (renamed from `_STOPWORDS`), `_K1`, `_B`, `terms()` and `rank()`. Move the existing docstring on `_rank` across unchanged — it records why BM25 replaced string similarity, and that reasoning belongs with the code.

```python
"""BM25 passage ranking, shared by the chat endpoint and the compliance check."""

import math
import re
from collections import Counter

_WORD_RE = re.compile(r"[a-z0-9]+")

_K1 = 1.5
_B = 0.75

STOPWORDS = frozenset(
    "a an and any are as at be been by can do does for from has have how in is it its "
    "me my of on or our shall should so that the their them there these this those to "
    "under up was were what when where which who whom why will with within would you "
    "your".split()
)


def terms(text: str) -> list[str]:
    return [w for w in _WORD_RE.findall(text.lower()) if w not in STOPWORDS and len(w) > 1]


def rank(query: str, passages: list[str]) -> list[int]:
    """Passage indices, best match first, scored with BM25."""
    docs = [Counter(terms(text)) for text in passages]
    if not docs:
        return []
    lengths = [sum(d.values()) or 1 for d in docs]
    avg_len = sum(lengths) / len(lengths)
    n = len(docs)

    query_terms = set(terms(query))
    document_freq = Counter(term for d in docs for term in query_terms if term in d)
    idf = {
        term: math.log(1 + (n - df + 0.5) / (df + 0.5))
        for term, df in document_freq.items()
    }

    def score(i: int) -> float:
        doc, length = docs[i], lengths[i]
        total = 0.0
        for term, weight in idf.items():
            tf = doc.get(term, 0)
            if tf:
                total += weight * (tf * (_K1 + 1)) / (tf + _K1 * (1 - _B + _B * length / avg_len))
        return total

    # A query sharing no term with any passage scores every passage zero; falling
    # back to the longest ones at least hands the model substantive text to read.
    return sorted(range(n), key=lambda i: (score(i), lengths[i]), reverse=True)
```

- [ ] **Step 4: Point chat.py at the shared service**

In `backend/app/routers/chat.py`: delete `import math`, `from collections import Counter`, `_WORD_RE`, `_STOPWORDS`, `_K1`, `_B`, `_terms`, `_rank`, and the full `_rank` docstring (it moved in Step 3). Add `from app.services.retrieval import rank, terms`. Then:

- in `_rank(question, passages)`'s two call sites inside `_select`, replace `ranked = _rank(question, passages)` with `ranked = rank(question, [text for text, _section, _kind in passages])`
- replace `set(_terms(question))` with `set(terms(question))` in `_select`

- [ ] **Step 5: Run the retrieval and chat tests**

Run: `docker compose exec -T backend python -m pytest tests/test_retrieval.py tests/test_chat.py -q`
Expected: PASS — the new tests plus every existing chat test, unchanged.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/retrieval.py backend/app/routers/chat.py backend/tests/test_retrieval.py
git commit -m "refactor: move BM25 ranking into a shared retrieval service

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: Share the upload validation

The case-study upload has to enforce the same extension allow-list, magic bytes, size cap and filename trimming the document upload does. One helper, two callers — a second copy would drift.

**Files:**
- Modify: `backend/app/routers/upload.py` (extract `save_upload`, call it from `upload_document`)
- Test: `backend/tests/test_upload_helper.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `app.routers.upload.save_upload(file: UploadFile, dest_dir: Path, name_prefix: str) -> tuple[Path, str]` returning `(written_path, safe_filename)`. Raises `HTTPException` 400/413 exactly as the endpoint does today. On any failure it deletes the partial file before re-raising. Also exported: `ALLOWED_TYPES`, `_fit_filename`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_upload_helper.py
import io
from pathlib import Path

import pytest
from fastapi import HTTPException, UploadFile

from app.routers.upload import save_upload


def _upload(name: str, data: bytes) -> UploadFile:
    return UploadFile(filename=name, file=io.BytesIO(data))


def test_save_upload_writes_the_file_with_its_prefix(tmp_path):
    path, name = save_upload(_upload("case.pdf", b"%PDF-1.4 body"), tmp_path, "check-7")
    assert name == "case.pdf"
    assert path == Path(tmp_path) / "check-7_case.pdf"
    assert path.read_bytes() == b"%PDF-1.4 body"


def test_save_upload_rejects_a_disallowed_extension(tmp_path):
    with pytest.raises(HTTPException) as exc:
        save_upload(_upload("notes.txt", b"hello"), tmp_path, "check-7")
    assert exc.value.status_code == 400


def test_save_upload_rejects_a_file_whose_bytes_do_not_match_its_extension(tmp_path):
    with pytest.raises(HTTPException) as exc:
        save_upload(_upload("case.pdf", b"not a pdf at all"), tmp_path, "check-7")
    assert exc.value.status_code == 400
    assert list(Path(tmp_path).iterdir()) == []


def test_save_upload_rejects_an_empty_file(tmp_path):
    with pytest.raises(HTTPException) as exc:
        save_upload(_upload("case.pdf", b""), tmp_path, "check-7")
    assert exc.value.status_code == 400
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec -T backend python -m pytest tests/test_upload_helper.py -q`
Expected: FAIL — `ImportError: cannot import name 'save_upload'`

- [ ] **Step 3: Extract the helper**

In `backend/app/routers/upload.py`, add above `upload_document`:

```python
def save_upload(file: UploadFile, dest_dir: Path, name_prefix: str) -> tuple[Path, str]:
    """Validate and stream an upload to `dest_dir/{name_prefix}_{filename}`.

    Every caller that accepts a file from a user goes through here, so the
    extension allow-list, the magic-byte check, the size cap and the filename byte
    budget cannot drift apart between upload paths.
    """
    # ponytail: strip directory components so a crafted filename (e.g. "../../etc/x.pdf")
    # can't escape dest_dir — Path.name discards any path segments, keeping only the basename.
    safe_filename = _fit_filename(Path(file.filename).name)
    ext = Path(safe_filename).suffix.lower()
    if ext not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{name_prefix}_{safe_filename}"

    written = 0
    try:
        with dest.open("wb") as f:
            while chunk := file.file.read(CHUNK_BYTES):
                if written == 0 and not chunk.startswith(_SIGNATURES[ext]):
                    raise HTTPException(
                        status_code=400,
                        detail=f"This file is not a readable {ext.lstrip('.').upper()} — it may be corrupt or renamed from another format",
                    )
                written += len(chunk)
                if written > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File is larger than the {MAX_UPLOAD_BYTES // (1024 * 1024)}MB limit",
                    )
                f.write(chunk)
        if written == 0:
            raise HTTPException(status_code=400, detail="This file is empty")
    except Exception:
        # Every failure, not only the ones raised above: an OSError here — a name the
        # filesystem refuses, a full disk, a permissions problem — must not leave a
        # partial file behind for a caller that is about to roll its row back.
        dest.unlink(missing_ok=True)
        raise
    return dest, safe_filename
```

- [ ] **Step 4: Call it from the document upload**

Replace the body of `upload_document` between the `Document` row creation and `background_tasks.add_task` so the endpoint keeps its own row-rollback but delegates the file work. The endpoint now reads:

```python
@router.post("/upload", status_code=status.HTTP_201_CREATED, response_model=UploadResponse)
def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    safe_filename = _fit_filename(Path(file.filename).name)
    ext = Path(safe_filename).suffix.lower()
    if ext not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")

    document = Document(
        user_id=user.id,
        filename=safe_filename,
        file_type=ext.lstrip("."),
        status="pending",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    upload_dir = Path(os.environ.get("UPLOAD_DIR", "/app/uploads"))
    try:
        dest, _name = save_upload(file, upload_dir, str(document.id))
    except Exception:
        # The row exists only to hold the file being written; without it the
        # dashboard would show a document that can never finish processing.
        db.delete(document)
        db.commit()
        raise

    background_tasks.add_task(process_document, document.id, str(dest))
    return {"id": document.id, "filename": document.filename, "status": document.status}
```

The extension check runs twice (once here so the row is never created for a `.txt`, once inside the helper). That is deliberate: the helper cannot assume its caller checked.

- [ ] **Step 5: Run the upload tests**

Run: `docker compose exec -T backend python -m pytest tests/test_upload_helper.py tests/test_upload.py tests/test_documents.py -q`
Expected: PASS — including every existing upload rejection test.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/upload.py backend/tests/test_upload_helper.py
git commit -m "refactor: extract save_upload so every upload path shares its validation

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: Models and migration

**Files:**
- Create: `backend/app/models/compliance_check.py`, `backend/app/models/check_finding.py`, `backend/alembic/versions/0004_compliance_checks.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_compliance_models.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `app.models.ComplianceCheck` with columns `id, document_id, filename, file_type, status, error_message, uploaded_at, incident_at, incident_source, evidence_text` and `findings` relationship; `app.models.CheckFinding` with `id, check_id, kind, source_id, section_id, requirement, verdict, evidence, note, due_at, bucket`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_compliance_models.py
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import CheckFinding, ComplianceCheck, Document, User


def test_a_check_cascades_its_findings_when_deleted():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()

    user = User(email="a@b.com", hashed_password="h")
    db.add(user)
    db.flush()
    doc = Document(user_id=user.id, filename="policy.pdf", file_type="pdf", status="done")
    db.add(doc)
    db.flush()
    check = ComplianceCheck(
        document_id=doc.id,
        filename="case.pdf",
        file_type="pdf",
        status="done",
        incident_at=datetime(2026, 9, 14, 15, 10),
        incident_source="stated",
        evidence_text="The fall occurred at 3:10pm.",
    )
    db.add(check)
    db.flush()
    db.add(CheckFinding(
        check_id=check.id, kind="deadline", source_id=1, section_id=None,
        requirement="Notify the Commission", verdict="not_done",
        evidence=None, note="The case study records no notification.",
        due_at=datetime(2026, 9, 15, 15, 10), bucket="overdue",
    ))
    db.commit()

    assert len(check.findings) == 1
    db.delete(check)
    db.commit()
    assert db.query(CheckFinding).count() == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec -T backend python -m pytest tests/test_compliance_models.py -q`
Expected: FAIL — `ImportError: cannot import name 'ComplianceCheck' from 'app.models'`

- [ ] **Step 3: Write the models**

```python
# backend/app/models/compliance_check.py
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class ComplianceCheck(Base):
    """One case-study document checked against one compliance document.

    The case study is deliberately not a Document row: it is evidence, it gets no
    extraction of its own, and it must not appear on the dashboard.
    """

    __tablename__ = "compliance_checks"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    error_message = Column(String, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    # When the incident the deadlines hang off actually happened, and whether the
    # case study said so or we fell back to the upload time.
    incident_at = Column(DateTime, nullable=True)
    incident_source = Column(String, nullable=True)
    evidence_text = Column(Text, nullable=True)

    findings = relationship(
        "CheckFinding", back_populates="check", cascade="all, delete-orphan"
    )
```

```python
# backend/app/models/check_finding.py
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class CheckFinding(Base):
    __tablename__ = "check_findings"

    id = Column(Integer, primary_key=True)
    check_id = Column(Integer, ForeignKey("compliance_checks.id"), nullable=False)
    # "obligation" or "deadline" — which table source_id points into.
    kind = Column(String, nullable=False)
    source_id = Column(Integer, nullable=False)
    section_id = Column(Integer, nullable=True)
    # Snapshot of the requirement as it was checked. Re-processing the compliance
    # document replaces its obligation rows, and without this an old report would
    # silently change or lose its rows.
    requirement = Column(Text, nullable=False)
    verdict = Column(String, nullable=False)
    evidence = Column(Text, nullable=True)
    note = Column(Text, nullable=True)
    due_at = Column(DateTime, nullable=True)
    bucket = Column(String, nullable=True)

    check = relationship("ComplianceCheck", back_populates="findings")
```

In `backend/app/models/__init__.py`, add the two imports after `from app.models.eval_run import EvalRun` and add `"ComplianceCheck"` and `"CheckFinding"` to `__all__`.

- [ ] **Step 4: Write the migration**

```python
# backend/alembic/versions/0004_compliance_checks.py
"""compliance checks

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "compliance_checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("file_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), nullable=True),
        sa.Column("incident_at", sa.DateTime(), nullable=True),
        sa.Column("incident_source", sa.String(), nullable=True),
        sa.Column("evidence_text", sa.Text(), nullable=True),
    )
    op.create_index("ix_compliance_checks_document_id", "compliance_checks", ["document_id"])

    op.create_table(
        "check_findings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("check_id", sa.Integer(), sa.ForeignKey("compliance_checks.id"), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("section_id", sa.Integer(), nullable=True),
        sa.Column("requirement", sa.Text(), nullable=False),
        sa.Column("verdict", sa.String(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("due_at", sa.DateTime(), nullable=True),
        sa.Column("bucket", sa.String(), nullable=True),
    )
    op.create_index("ix_check_findings_check_id", "check_findings", ["check_id"])


def downgrade() -> None:
    op.drop_index("ix_check_findings_check_id", table_name="check_findings")
    op.drop_table("check_findings")
    op.drop_index("ix_compliance_checks_document_id", table_name="compliance_checks")
    op.drop_table("compliance_checks")
```

- [ ] **Step 5: Run the test and the migration**

Run: `docker compose exec -T backend python -m pytest tests/test_compliance_models.py -q`
Expected: PASS

Run: `docker compose exec -T backend alembic upgrade head`
Expected: `Running upgrade 0003 -> 0004, compliance checks`

- [ ] **Step 6: Commit**

```bash
git add backend/app/models backend/alembic/versions/0004_compliance_checks.py backend/tests/test_compliance_models.py
git commit -m "feat: add compliance_checks and check_findings tables

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: Read the incident time out of a case study

**Files:**
- Create: `backend/app/services/compliance_check.py` (first half — this task adds only the incident-time function and the module docstring)
- Test: `backend/tests/test_compliance_incident_time.py`

**Interfaces:**
- Consumes: `app.services.extraction._latest_date_in`, `app.services.extraction._MONTHS`.
- Produces: `app.services.compliance_check.find_incident_datetime(text: str, fallback: datetime) -> tuple[datetime, str]` returning `(when, source)` where `source` is `"stated"` or `"upload_time"`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_compliance_incident_time.py
from datetime import datetime

from app.services.compliance_check import find_incident_datetime

FALLBACK = datetime(2026, 9, 17, 9, 0)


def test_a_stated_date_and_time_is_used():
    text = "The medication error occurred on 14 September 2026 at 3:10pm in Wing B."
    assert find_incident_datetime(text, FALLBACK) == (datetime(2026, 9, 14, 15, 10), "stated")


def test_a_24_hour_clock_is_understood():
    text = "Incident date: 14 September 2026. Time of incident: 15:10."
    assert find_incident_datetime(text, FALLBACK) == (datetime(2026, 9, 14, 15, 10), "stated")


def test_a_date_with_no_time_starts_at_midnight():
    text = "The fall occurred on 14 September 2026 and was reported the same day."
    assert find_incident_datetime(text, FALLBACK) == (datetime(2026, 9, 14, 0, 0), "stated")


def test_no_date_at_all_falls_back_to_the_upload_time():
    assert find_incident_datetime("A resident was unwell.", FALLBACK) == (FALLBACK, "upload_time")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec -T backend python -m pytest tests/test_compliance_incident_time.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.compliance_check'`

- [ ] **Step 3: Write the function**

```python
# backend/app/services/compliance_check.py
"""Checking a case-study document against a compliance document's requirements.

The compliance document supplies the requirements; the case study is the evidence.
Every obligation and deadline the compliance document carries gets one verdict, and
deadlines are resolved against the moment the case study says the incident happened.
"""

import logging
import re
from datetime import datetime, time

from app.services.extraction import _latest_date_in

logger = logging.getLogger(__name__)

# "3:10pm", "3.10 pm", "15:10", "3pm". The hour alone is only taken when it carries
# am/pm — a bare "15" in a sentence is a quantity, not a time.
_TIME = re.compile(
    r"\b(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm)\b|\b([01]?\d|2[0-3]):([0-5]\d)\b",
    re.IGNORECASE,
)

# How far into the document to look. An incident record states when it happened in
# its opening lines; a mention 20 pages later is a cross-reference to another event.
INCIDENT_SCAN_CHARS = 3000


def _first_time_in(text: str) -> time | None:
    match = _TIME.search(text)
    if match is None:
        return None
    if match.group(3):  # 12-hour form
        hour = int(match.group(1)) % 12
        minute = int(match.group(2) or 0)
        if match.group(3).lower() == "pm":
            hour += 12
        return time(hour, minute)
    return time(int(match.group(4)), int(match.group(5)))


def find_incident_datetime(text: str, fallback: datetime) -> tuple[datetime, str]:
    """When the incident happened, and whether the document said so.

    A relative deadline ("within 24 hours of the incident") is meaningless until the
    incident has a time. Where the case study states one, that is the clock; where it
    does not, the upload time stands in and the caller is told so, rather than the
    report implying a precision it does not have.
    """
    head = text[:INCIDENT_SCAN_CHARS]
    when = _latest_date_in(head)
    if when is None:
        return fallback, "upload_time"
    return datetime.combine(when, _first_time_in(head) or time(0, 0)), "stated"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec -T backend python -m pytest tests/test_compliance_incident_time.py -q`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/compliance_check.py backend/tests/test_compliance_incident_time.py
git commit -m "feat: read the incident date and time out of a case study

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: Run the check

**Files:**
- Modify: `backend/app/services/compliance_check.py` (add requirement loading, evidence selection, the prompt, the batch call and `run_check`)
- Test: `backend/tests/test_compliance_run.py`

**Interfaces:**
- Consumes: `find_incident_datetime` (Task 4), `app.services.retrieval.rank` (Task 1), `app.models.ComplianceCheck` / `CheckFinding` (Task 3), `app.services.deadlines.resolve_due_at` / `bucket_for`, `app.services.docling_parser.parse_document`, `app.services.llm.get_llm`.
- Produces:
  - `Requirement` dataclass: `kind: str`, `source_id: int`, `section_id: int | None`, `text: str`, `due_date: str | None`
  - `load_requirements(document_id: int, db) -> list[Requirement]`
  - `select_evidence(query: str, evidence_text: str) -> str`
  - `MAX_WHOLE_EVIDENCE_CHARS = 12000`, `EVIDENCE_TOP_K = 6`, `MAX_BATCH_REQUIREMENTS = 8`
  - `CheckVerdict` / `CheckBatch` Pydantic models
  - `run_check(check_id: int, file_path: str) -> None`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_compliance_run.py
from datetime import datetime
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import CheckFinding, ComplianceCheck, Deadline, Document, Obligation, Section, User
from app.services.docling_parser import ParsedSection


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _seed(db):
    user = User(email="a@b.com", hashed_password="h")
    db.add(user)
    db.flush()
    doc = Document(user_id=user.id, filename="policy.pdf", file_type="pdf", status="done")
    db.add(doc)
    db.flush()
    section = Section(document_id=doc.id, heading="Part 3", order_idx=0, page_ref=None, raw_text="x")
    db.add(section)
    db.flush()
    db.add(Obligation(document_id=doc.id, section_id=section.id, text="Notify the family", responsible_role="RN", priority="high"))
    db.add(Deadline(document_id=doc.id, section_id=section.id, description="Notify the Commission", due_date="within 24 hours of the incident", responsible_role="RN"))
    check = ComplianceCheck(document_id=doc.id, filename="case.pdf", file_type="pdf", status="pending")
    db.add(check)
    db.commit()
    return doc, check


def test_select_evidence_passes_a_short_case_study_whole():
    from app.services.compliance_check import select_evidence

    text = "The fall occurred at 3pm. The family was notified at 3:30pm."
    assert select_evidence("Notify the family", text) == text


def test_select_evidence_retrieves_passages_from_a_long_case_study():
    from app.services.compliance_check import MAX_WHOLE_EVIDENCE_CHARS, select_evidence

    needle = "The registered nurse notified the family at 3:30pm."
    filler = "\n\n".join(f"Routine observation entry number {i} recorded no change." for i in range(400))
    assert len(filler) > MAX_WHOLE_EVIDENCE_CHARS
    selected = select_evidence("notified the family", f"{filler}\n\n{needle}")
    assert needle in selected
    assert len(selected) < len(filler)


def test_run_check_stores_a_verdict_per_requirement_and_times_deadlines_from_the_incident():
    from app.services.compliance_check import CheckBatch, CheckVerdict, run_check

    db = _db()
    doc, check = _seed(db)
    check_id = check.id

    parsed = [ParsedSection(heading="Case study", order_idx=0, page_ref=None,
                            raw_text="The medication error occurred on 14 September 2026 at 3:10pm. The family was notified at 3:30pm.")]
    verdicts = CheckBatch(verdicts=[
        CheckVerdict(index=0, verdict="done", evidence="The family was notified at 3:30pm.", note="Notified within the hour."),
        CheckVerdict(index=1, verdict="not_done", evidence=None, note="No notification to the Commission is recorded."),
    ])
    fake_llm = MagicMock()
    fake_llm.with_structured_output.return_value.invoke.return_value = verdicts

    with patch("app.services.compliance_check.SessionLocal", return_value=db), \
         patch("app.services.compliance_check.parse_document", return_value=parsed), \
         patch("app.services.compliance_check.get_llm", return_value=fake_llm):
        run_check(check_id, "/tmp/case.pdf")

    stored = db.query(ComplianceCheck).filter_by(id=check_id).one()
    assert stored.status == "done"
    assert stored.incident_source == "stated"
    assert stored.incident_at == datetime(2026, 9, 14, 15, 10)

    findings = {f.kind: f for f in db.query(CheckFinding).filter_by(check_id=check_id)}
    assert findings["obligation"].verdict == "done"
    assert findings["deadline"].verdict == "not_done"
    # "within 24 hours of the incident", counted from 3:10pm on the 14th.
    assert findings["deadline"].due_at == datetime(2026, 9, 15, 15, 10)
    assert findings["deadline"].bucket in {"overdue", "within_24_hours", "within_7_days", "within_30_days", "later"}


def test_run_check_records_unclear_when_the_model_call_fails():
    from app.services.compliance_check import run_check

    db = _db()
    doc, check = _seed(db)
    check_id = check.id

    parsed = [ParsedSection(heading="Case study", order_idx=0, page_ref=None, raw_text="A resident fell on 14 September 2026.")]
    fake_llm = MagicMock()
    fake_llm.with_structured_output.return_value.invoke.side_effect = RuntimeError("provider down")

    with patch("app.services.compliance_check.SessionLocal", return_value=db), \
         patch("app.services.compliance_check.parse_document", return_value=parsed), \
         patch("app.services.compliance_check.get_llm", return_value=fake_llm):
        run_check(check_id, "/tmp/case.pdf")

    stored = db.query(ComplianceCheck).filter_by(id=check_id).one()
    assert stored.status == "done"
    assert {f.verdict for f in db.query(CheckFinding).filter_by(check_id=check_id)} == {"unclear"}


def test_run_check_fails_the_check_when_the_case_study_cannot_be_parsed():
    from app.services.compliance_check import run_check

    db = _db()
    doc, check = _seed(db)
    check_id = check.id

    with patch("app.services.compliance_check.SessionLocal", return_value=db), \
         patch("app.services.compliance_check.parse_document", side_effect=RuntimeError("bad file")):
        run_check(check_id, "/tmp/case.pdf")

    stored = db.query(ComplianceCheck).filter_by(id=check_id).one()
    assert stored.status == "failed"
    assert "could not be read" in stored.error_message
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose exec -T backend python -m pytest tests/test_compliance_run.py -q`
Expected: FAIL — `ImportError: cannot import name 'select_evidence'`

- [ ] **Step 3: Add the requirement loading and evidence selection**

Append to `backend/app/services/compliance_check.py` (and extend the imports at the top with `from dataclasses import dataclass`, `from typing import Literal`, `from pydantic import BaseModel`, `from app.database import SessionLocal`, `from app.models import CheckFinding, ComplianceCheck, Deadline, Obligation`, `from app.services.deadlines import bucket_for, resolve_due_at`, `from app.services.docling_parser import parse_document`, `from app.services.llm import get_llm`, `from app.services.retrieval import rank`):

```python
# A case study that fits in this many characters is sent whole — an incident record
# normally does, and whole text beats retrieved passages when it is affordable.
# Past it, the batch gets the passages that match its requirements instead.
MAX_WHOLE_EVIDENCE_CHARS = 12000
EVIDENCE_TOP_K = 6
# Matching extraction's batching: the response carries one verdict per requirement,
# and a batch that overruns the output-token limit loses the whole call.
MAX_BATCH_REQUIREMENTS = 8


@dataclass
class Requirement:
    """One thing the compliance document requires, as handed to the check."""

    kind: str  # "obligation" | "deadline"
    source_id: int
    section_id: int | None
    text: str
    due_date: str | None


def load_requirements(document_id: int, db) -> list[Requirement]:
    out = [
        Requirement("obligation", row.id, row.section_id, row.text, None)
        for row in db.query(Obligation).filter(Obligation.document_id == document_id)
    ]
    out += [
        Requirement("deadline", row.id, row.section_id, row.description, row.due_date)
        for row in db.query(Deadline).filter(Deadline.document_id == document_id)
    ]
    return out


def select_evidence(query: str, evidence_text: str) -> str:
    """The part of the case study this batch should be judged against."""
    if len(evidence_text) <= MAX_WHOLE_EVIDENCE_CHARS:
        return evidence_text
    paragraphs = [p.strip() for p in evidence_text.split("\n\n") if p.strip()]
    best = rank(query, paragraphs)[:EVIDENCE_TOP_K]
    # Kept in document order: a case study is a narrative, and passages shuffled
    # into relevance order read as a different sequence of events.
    return "\n\n".join(paragraphs[i] for i in sorted(best))
```

- [ ] **Step 4: Add the prompt and the batch call**

```python
class CheckVerdict(BaseModel):
    index: int
    verdict: Literal["done", "not_done", "partly", "unclear"]
    evidence: str | None = None
    note: str


class CheckBatch(BaseModel):
    verdicts: list[CheckVerdict]


CHECK_PROMPT = """You are auditing one organisation's record of what it did against \
the requirements of a compliance document.

The EVIDENCE below is the organisation's own account — an incident record, a case \
study, or a file note. The REQUIREMENTS are drawn from the compliance document.

For EACH requirement, return an object carrying that requirement's "index" and:
- "verdict": one of
  - "done" — the evidence shows this requirement was met
  - "partly" — some of it was met, or it was met late or incompletely
  - "not_done" — the evidence shows it was not met, or shows an action that \
contradicts it
  - "unclear" — the evidence does not say either way
- "evidence": the sentence from the EVIDENCE that supports your verdict, quoted \
exactly, or null when there is none
- "note": one sentence explaining the verdict, addressed to the user

Judge only from the EVIDENCE. Do not assume a requirement was met because it is \
routine, standard practice, or something the organisation would normally do. \
"unclear" is the correct answer whenever the evidence is silent — it is not a \
failure, and reporting silence as "not_done" would accuse the organisation of \
something this document does not show.

EVIDENCE:
{evidence}

REQUIREMENTS:
{requirements}"""


def _render_requirements(batch: list[Requirement]) -> str:
    lines = []
    for i, req in enumerate(batch):
        due = f" (due: {req.due_date})" if req.due_date else ""
        lines.append(f"--- Requirement index {i} ---\n{req.kind}: {req.text}{due}")
    return "\n\n".join(lines)


def _verdicts_for(batch: list[Requirement], evidence_text: str) -> dict[int, CheckVerdict]:
    """One model call for one batch; an empty dict when the call cannot be trusted."""
    query = " ".join(req.text for req in batch)
    prompt = CHECK_PROMPT.format(
        evidence=select_evidence(query, evidence_text),
        requirements=_render_requirements(batch),
    )
    structured = get_llm().with_structured_output(CheckBatch, method="json_schema")
    try:
        result = structured.invoke(prompt)
    except Exception:  # noqa: BLE001 - any provider failure looks the same here
        logger.exception("Compliance check batch failed for %s requirements", len(batch))
        return {}
    out: dict[int, CheckVerdict] = {}
    for item in result.verdicts:
        # An index the model invented or returned twice cannot be matched to a
        # requirement; dropping it leaves that requirement "unclear" rather than
        # filing another requirement's verdict against it.
        if 0 <= item.index < len(batch) and item.index not in out:
            out[item.index] = item
    return out
```

- [ ] **Step 5: Add `run_check`**

```python
def run_check(check_id: int, file_path: str) -> None:
    """Background task: parse the case study, judge every requirement, store findings."""
    # ponytail: no db.close() — same as process_document, whose comment explains why.
    db = SessionLocal()
    try:
        check = db.query(ComplianceCheck).filter(ComplianceCheck.id == check_id).first()
    except Exception:  # noqa: BLE001 - never let a background task crash the caller
        logger.exception("Failed to fetch ComplianceCheck id=%s", check_id)
        return
    if check is None:
        return
    check.status = "processing"
    db.commit()

    try:
        sections = parse_document(file_path)
    except Exception:  # noqa: BLE001 - unrecoverable parse failure
        logger.exception("Failed to parse case study for check id=%s at %s", check_id, file_path)
        check.status = "failed"
        check.error_message = (
            "This file could not be read. It may be corrupt, password-protected, or "
            "saved in an unsupported format."
        )
        db.commit()
        return

    evidence_text = "\n\n".join(
        f"{s.heading}\n{s.raw_text}" if s.heading else s.raw_text for s in sections
    ).strip()
    if not evidence_text:
        check.status = "failed"
        check.error_message = "This document has no readable text to check against."
        db.commit()
        return

    check.evidence_text = evidence_text
    check.incident_at, check.incident_source = find_incident_datetime(
        evidence_text, check.uploaded_at or datetime.utcnow()
    )
    db.commit()

    requirements = load_requirements(check.document_id, db)
    if not requirements:
        check.status = "failed"
        check.error_message = (
            "This compliance document has no obligations or deadlines to check against yet."
        )
        db.commit()
        return

    now = datetime.utcnow()
    for start in range(0, len(requirements), MAX_BATCH_REQUIREMENTS):
        batch = requirements[start : start + MAX_BATCH_REQUIREMENTS]
        verdicts = _verdicts_for(batch, evidence_text)
        for i, req in enumerate(batch):
            verdict = verdicts.get(i)
            due_at = resolve_due_at(req.due_date, check.incident_at) if req.kind == "deadline" else None
            db.add(CheckFinding(
                check_id=check.id,
                kind=req.kind,
                source_id=req.source_id,
                section_id=req.section_id,
                requirement=req.text,
                # A batch the model failed to answer leaves its requirements
                # unjudged. That is "unclear", not "not_done" — the difference
                # between "we have no answer" and "you did not do it".
                verdict=verdict.verdict if verdict else "unclear",
                evidence=verdict.evidence if verdict else None,
                note=verdict.note if verdict else "The check could not reach a verdict for this requirement.",
                due_at=due_at,
                bucket=bucket_for(due_at, now) if req.kind == "deadline" else None,
            ))
        db.commit()

    check.status = "done"
    db.commit()
```

- [ ] **Step 6: Run the tests**

Run: `docker compose exec -T backend python -m pytest tests/test_compliance_run.py -q`
Expected: PASS (5 tests)

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/compliance_check.py backend/tests/test_compliance_run.py
git commit -m "feat: judge a case study against a document's obligations and deadlines

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: The API

**Files:**
- Create: `backend/app/routers/compliance.py`
- Modify: `backend/app/main.py` (import and include the router)
- Test: `backend/tests/test_compliance_api.py`

**Interfaces:**
- Consumes: `save_upload` (Task 2), `run_check` (Task 5), models (Task 3).
- Produces: `POST /api/compliance-checks/{doc_id}` → 201 `{id, filename, status}`; `GET /api/compliance-checks/{doc_id}` → list of `{id, filename, status, error_message, uploaded_at, incident_at, incident_source, counts}`; `GET /api/compliance-checks/item/{check_id}` → the check plus `findings`; `DELETE /api/compliance-checks/item/{check_id}` → 204.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_compliance_api.py
import io

from tests.test_documents import _auth_header


def _document(client, session_local, headers):
    from app.models import Document, Obligation, Section, User

    db = session_local()
    user = db.query(User).filter_by(email="a@b.com").one()
    doc = Document(user_id=user.id, filename="policy.pdf", file_type="pdf", status="done")
    db.add(doc)
    db.flush()
    section = Section(document_id=doc.id, heading="Part 3", order_idx=0, page_ref=None, raw_text="x")
    db.add(section)
    db.flush()
    db.add(Obligation(document_id=doc.id, section_id=section.id, text="Notify the family", responsible_role="RN", priority="high"))
    db.commit()
    return doc.id


def test_upload_creates_a_check_and_schedules_it(client, session_local, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    headers = _auth_header(client)
    doc_id = _document(client, session_local, headers)

    resp = client.post(
        f"/api/compliance-checks/{doc_id}",
        headers=headers,
        files={"file": ("case.pdf", io.BytesIO(b"%PDF-1.4 evidence"), "application/pdf")},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "pending"

    listed = client.get(f"/api/compliance-checks/{doc_id}", headers=headers).json()
    assert len(listed) == 1
    assert listed[0]["filename"] == "case.pdf"


def test_upload_rejects_a_file_that_is_not_a_pdf_or_docx(client, session_local, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    headers = _auth_header(client)
    doc_id = _document(client, session_local, headers)

    resp = client.post(
        f"/api/compliance-checks/{doc_id}",
        headers=headers,
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert resp.status_code == 400


def test_checks_are_scoped_to_the_documents_owner(client, session_local, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    headers = _auth_header(client)
    other = _auth_header(client, "b@b.com")
    doc_id = _document(client, session_local, headers)

    assert client.get(f"/api/compliance-checks/{doc_id}", headers=other).status_code == 404
    resp = client.post(
        f"/api/compliance-checks/{doc_id}",
        headers=other,
        files={"file": ("case.pdf", io.BytesIO(b"%PDF-1.4 evidence"), "application/pdf")},
    )
    assert resp.status_code == 404


def test_findings_are_served_and_a_check_can_be_deleted(client, session_local, tmp_path, monkeypatch):
    from app.models import CheckFinding, ComplianceCheck

    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    headers = _auth_header(client)
    other = _auth_header(client, "b@b.com")
    doc_id = _document(client, session_local, headers)

    db = session_local()
    check = ComplianceCheck(document_id=doc_id, filename="case.pdf", file_type="pdf", status="done")
    db.add(check)
    db.flush()
    db.add(CheckFinding(check_id=check.id, kind="obligation", source_id=1, section_id=None,
                        requirement="Notify the family", verdict="done",
                        evidence="Family notified at 3:30pm.", note="Notified promptly."))
    db.commit()
    check_id = check.id

    body = client.get(f"/api/compliance-checks/item/{check_id}", headers=headers).json()
    assert body["findings"][0]["verdict"] == "done"
    assert body["counts"]["done"] == 1

    assert client.get(f"/api/compliance-checks/item/{check_id}", headers=other).status_code == 404
    assert client.delete(f"/api/compliance-checks/item/{check_id}", headers=headers).status_code == 204
    assert client.get(f"/api/compliance-checks/item/{check_id}", headers=headers).status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec -T backend python -m pytest tests/test_compliance_api.py -q`
Expected: FAIL — 404s on every route (the router does not exist yet)

- [ ] **Step 3: Write the router**

```python
# backend/app/routers/compliance.py
import os
from collections import Counter
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import CheckFinding, ComplianceCheck, User
from app.routers.documents import _get_owned_document
from app.routers.upload import ALLOWED_TYPES, _fit_filename, save_upload
from app.services.compliance_check import run_check

router = APIRouter(prefix="/api/compliance-checks", tags=["compliance-checks"])


def _get_owned_check(check_id: int, db: Session, user: User) -> ComplianceCheck:
    check = db.query(ComplianceCheck).filter(ComplianceCheck.id == check_id).first()
    if check is None:
        raise HTTPException(status_code=404, detail="Check not found")
    # A check has no owner of its own; it belongs to whoever owns the document it
    # was run against, and _get_owned_document raises 404 for anyone else.
    _get_owned_document(check.document_id, db, user)
    return check


def _counts(findings: list[CheckFinding]) -> dict[str, int]:
    tally = Counter(f.verdict for f in findings)
    return {verdict: tally.get(verdict, 0) for verdict in ("done", "partly", "not_done", "unclear")}


@router.post("/{doc_id}", status_code=status.HTTP_201_CREATED)
def create_check(
    doc_id: int,
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_owned_document(doc_id, db, user)

    safe_filename = _fit_filename(Path(file.filename).name)
    ext = Path(safe_filename).suffix.lower()
    if ext not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")

    check = ComplianceCheck(
        document_id=doc_id,
        filename=safe_filename,
        file_type=ext.lstrip("."),
        status="pending",
    )
    db.add(check)
    db.commit()
    db.refresh(check)

    upload_dir = Path(os.environ.get("UPLOAD_DIR", "/app/uploads"))
    try:
        dest, _name = save_upload(file, upload_dir, f"check{check.id}")
    except Exception:
        # The row exists only to hold the file being written.
        db.delete(check)
        db.commit()
        raise

    background_tasks.add_task(run_check, check.id, str(dest))
    return {"id": check.id, "filename": check.filename, "status": check.status}


@router.get("/{doc_id}")
def list_checks(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _get_owned_document(doc_id, db, user)
    checks = (
        db.query(ComplianceCheck)
        .filter(ComplianceCheck.document_id == doc_id)
        .order_by(ComplianceCheck.id.desc())
        .all()
    )
    return [
        {
            "id": c.id,
            "filename": c.filename,
            "status": c.status,
            "error_message": c.error_message,
            "uploaded_at": c.uploaded_at,
            "incident_at": c.incident_at,
            "incident_source": c.incident_source,
            "counts": _counts(c.findings),
        }
        for c in checks
    ]


@router.get("/item/{check_id}")
def get_check(check_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    check = _get_owned_check(check_id, db, user)
    return {
        "id": check.id,
        "document_id": check.document_id,
        "filename": check.filename,
        "status": check.status,
        "error_message": check.error_message,
        "uploaded_at": check.uploaded_at,
        "incident_at": check.incident_at,
        "incident_source": check.incident_source,
        "counts": _counts(check.findings),
        "findings": [
            {
                "id": f.id,
                "kind": f.kind,
                "section_id": f.section_id,
                "requirement": f.requirement,
                "verdict": f.verdict,
                "evidence": f.evidence,
                "note": f.note,
                "due_at": f.due_at.isoformat() if f.due_at else None,
                "bucket": f.bucket,
            }
            for f in check.findings
        ],
    }


@router.delete("/item/{check_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_check(check_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    check = _get_owned_check(check_id, db, user)
    db.delete(check)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

In `backend/app/main.py`: add `compliance` to the `from app.routers import ...` line and `app.include_router(compliance.router)` beside the other includes.

- [ ] **Step 4: Run the tests**

Run: `docker compose exec -T backend python -m pytest tests/test_compliance_api.py -q`
Expected: PASS (4 tests)

- [ ] **Step 5: Run the whole backend suite**

Run: `docker compose exec -T backend python -m pytest tests -q`
Expected: PASS — every existing test plus the new ones.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/compliance.py backend/app/main.py backend/tests/test_compliance_api.py
git commit -m "feat: compliance check API

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: The Compliance Check tab

**Files:**
- Create: `frontend/src/api/compliance.ts`, `frontend/src/components/ComplianceCheckPanel.tsx`
- Modify: `frontend/src/pages/DocumentDetail.tsx` (add the tab to `TABS`, render the panel)

**Interfaces:**
- Consumes: the four endpoints from Task 6.
- Produces: `listChecks(docId)`, `getCheck(checkId)`, `createCheck(docId, file)`, `deleteCheck(checkId)`, and the default-exported `ComplianceCheckPanel({ docId, sections, onSectionClick })`.

- [ ] **Step 1: Write the API module**

```ts
// frontend/src/api/compliance.ts
import { apiFetch } from "./client";

export interface CheckSummary {
  id: number;
  filename: string;
  status: string;
  error_message: string | null;
  uploaded_at: string | null;
  incident_at: string | null;
  /** "stated" when the case study gave the incident time, "upload_time" when it did not. */
  incident_source: string | null;
  counts: Record<string, number>;
}

export interface CheckFinding {
  id: number;
  kind: string;
  section_id: number | null;
  requirement: string;
  verdict: string;
  evidence: string | null;
  note: string | null;
  due_at: string | null;
  bucket: string | null;
}

export interface CheckDetail extends CheckSummary {
  document_id: number;
  findings: CheckFinding[];
}

export async function listChecks(docId: number): Promise<CheckSummary[]> {
  return (await apiFetch(`/api/compliance-checks/${docId}`)).json();
}

export async function getCheck(checkId: number): Promise<CheckDetail> {
  return (await apiFetch(`/api/compliance-checks/item/${checkId}`)).json();
}

export async function createCheck(docId: number, file: File): Promise<CheckSummary> {
  const body = new FormData();
  body.append("file", file);
  // No Content-Type header: the browser sets the multipart boundary itself.
  return (await apiFetch(`/api/compliance-checks/${docId}`, { method: "POST", body })).json();
}

export async function deleteCheck(checkId: number): Promise<void> {
  await apiFetch(`/api/compliance-checks/item/${checkId}`, { method: "DELETE" });
}
```

- [ ] **Step 2: Write the panel**

```tsx
// frontend/src/components/ComplianceCheckPanel.tsx
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createCheck, deleteCheck, getCheck, listChecks, type CheckFinding,
} from "../api/compliance";

const VERDICT_GROUPS = [
  { key: "not_done", label: "Not done", tone: "bg-coral/10 text-coral" },
  { key: "partly", label: "Partly done", tone: "bg-amber-50 text-amber" },
  { key: "done", label: "Done — maintain", tone: "bg-sage/10 text-sage" },
  { key: "unclear", label: "Not covered by this case study", tone: "bg-parchment-200 text-slate-500" },
] as const;

const BUCKET_LABEL: Record<string, string> = {
  overdue: "Overdue",
  within_24_hours: "Within 24 hours",
  within_7_days: "Within 7 days",
  within_30_days: "Within 30 days",
  later: "Later",
  no_date: "No date",
};

function formatWhen(iso: string | null) {
  if (!iso) return null;
  return new Date(iso).toLocaleString(undefined, {
    day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit",
  });
}

function FindingRow({
  finding,
  sections,
  onSectionClick,
}: {
  finding: CheckFinding;
  sections: { id: number; heading: string }[];
  onSectionClick?: (sectionId: number) => void;
}) {
  const heading = sections.find((s) => s.id === finding.section_id)?.heading;
  return (
    <div className="border-b border-ink/5 px-5 py-4">
      <p className="text-sm text-ink">{finding.requirement}</p>
      {finding.note && <p className="mt-1 text-sm text-slate-500">{finding.note}</p>}
      {finding.evidence && (
        <blockquote className="mt-2 border-l-2 border-teal/40 pl-3 text-sm italic text-slate-500">
          {finding.evidence}
        </blockquote>
      )}
      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
        {finding.due_at && (
          <span className="rounded-full bg-parchment-200 px-2 py-0.5 text-slate-500">
            Due {formatWhen(finding.due_at)}
            {finding.bucket ? ` · ${BUCKET_LABEL[finding.bucket] ?? finding.bucket}` : ""}
          </span>
        )}
        {heading && finding.section_id != null && onSectionClick && (
          <button
            onClick={() => onSectionClick(finding.section_id!)}
            className="rounded-full bg-teal-50 px-2.5 py-1 font-mono text-teal-600 transition hover:bg-teal hover:text-white"
          >
            {heading}
          </button>
        )}
      </div>
    </div>
  );
}

export default function ComplianceCheckPanel({
  docId,
  sections,
  onSectionClick,
}: {
  docId: number;
  sections: { id: number; heading: string }[];
  onSectionClick?: (sectionId: number) => void;
}) {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: checks } = useQuery({
    queryKey: ["compliance-checks", docId],
    queryFn: () => listChecks(docId),
    // A check that is still running finishes without anything else touching the page.
    refetchInterval: (query) =>
      (query.state.data ?? []).some((c) => c.status === "pending" || c.status === "processing") ? 3000 : false,
  });

  const activeId = selected ?? checks?.[0]?.id ?? null;
  const { data: check } = useQuery({
    queryKey: ["compliance-check", activeId],
    queryFn: () => getCheck(activeId!),
    enabled: activeId != null,
    refetchInterval: (query) =>
      query.state.data?.status === "pending" || query.state.data?.status === "processing" ? 3000 : false,
  });

  const upload = useMutation({
    mutationFn: (file: File) => createCheck(docId, file),
    onSuccess: (created) => {
      setError(null);
      setSelected(created.id);
      queryClient.invalidateQueries({ queryKey: ["compliance-checks", docId] });
    },
    onError: (e: Error) => setError(e.message),
  });

  const remove = useMutation({
    mutationFn: (checkId: number) => deleteCheck(checkId),
    onSuccess: () => {
      setSelected(null);
      queryClient.invalidateQueries({ queryKey: ["compliance-checks", docId] });
    },
  });

  useEffect(() => {
    if (checks && activeId != null && !checks.some((c) => c.id === activeId)) setSelected(null);
  }, [checks, activeId]);

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3 border-b border-ink/10 px-5 py-4">
        <label className="cursor-pointer rounded-lg bg-ink px-3 py-2 text-sm text-parchment transition hover:bg-ink-800">
          {upload.isPending ? "Uploading…" : "Upload a case-study document"}
          <input
            type="file"
            accept=".pdf,.docx"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) upload.mutate(file);
              e.target.value = "";
            }}
          />
        </label>
        <p className="text-sm text-slate-500">
          Checked against this document's obligations and deadlines.
        </p>
        {(checks?.length ?? 0) > 1 && (
          <select
            value={activeId ?? ""}
            onChange={(e) => setSelected(Number(e.target.value))}
            className="ml-auto rounded-lg border border-ink/10 bg-white px-2 py-1 text-xs text-slate-500"
          >
            {checks!.map((c) => <option key={c.id} value={c.id}>{c.filename}</option>)}
          </select>
        )}
      </div>

      {error && <p className="px-5 py-3 text-sm text-coral">{error}</p>}

      {!check && <p className="p-10 text-center text-sm text-slate-500">
        No case study checked yet. Upload one to see what is done, what is outstanding, and how long is left.
      </p>}

      {check && (check.status === "pending" || check.status === "processing") && (
        <p className="p-10 text-center text-sm text-slate-500">Checking {check.filename} against this document…</p>
      )}

      {check && check.status === "failed" && (
        <p className="p-10 text-center text-sm text-coral">{check.error_message}</p>
      )}

      {check && check.status === "done" && (
        <>
          <div className="flex flex-wrap items-center gap-3 border-b border-ink/10 bg-parchment-100 px-5 py-3 text-xs text-slate-500">
            <span className="font-medium text-ink">{check.filename}</span>
            <span>
              Incident {formatWhen(check.incident_at) ?? "unknown"}
              {check.incident_source === "upload_time" && " (assumed — the document states no date)"}
            </span>
            {VERDICT_GROUPS.map((g) => (
              <span key={g.key} className={`rounded-full px-2 py-0.5 ${g.tone}`}>
                {g.label} {check.counts[g.key] ?? 0}
              </span>
            ))}
            <button
              onClick={() => remove.mutate(check.id)}
              className="ml-auto rounded-lg border border-ink/10 px-2 py-1 transition hover:bg-white"
            >
              Delete check
            </button>
          </div>

          {VERDICT_GROUPS.map((group) => {
            const rows = check.findings.filter((f) => f.verdict === group.key);
            if (rows.length === 0) return null;
            // Deadlines first inside every group: a requirement with a clock on it is
            // the one the user has to act on first.
            const ordered = [...rows].sort((a, b) => (a.due_at ? 0 : 1) - (b.due_at ? 0 : 1));
            return (
              <section key={group.key}>
                <h3 className={`px-5 py-2 text-xs uppercase tracking-wide ${group.tone}`}>
                  {group.label} · {rows.length}
                </h3>
                {ordered.map((f) => (
                  <FindingRow key={f.id} finding={f} sections={sections} onSectionClick={onSectionClick} />
                ))}
              </section>
            );
          })}
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Wire the tab into the document page**

In `frontend/src/pages/DocumentDetail.tsx`:

1. Add the import beside the other component imports:
   `import ComplianceCheckPanel from "../components/ComplianceCheckPanel";`
2. Add to `TABS`, between `Actions` and `Sections`:
   `{ key: "Compliance Check", count: undefined },`
3. Render it beside the other tab panels, after the `Actions` block:

```tsx
{tab === "Compliance Check" && (
  <ComplianceCheckPanel docId={docId} sections={document.sections} onSectionClick={jumpToSection} />
)}
```

- [ ] **Step 4: Typecheck**

Run: `cd frontend && npx tsc --noEmit -p tsconfig.json`
Expected: no output

- [ ] **Step 5: Check it in the browser**

Run: `docker compose up -d` (already running is fine), open the app, open a processed document, click **Compliance Check**, upload one of the samples from Task 8, and confirm: the panel polls while running, then shows grouped findings with due times on the deadline rows.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/compliance.ts frontend/src/components/ComplianceCheckPanel.tsx frontend/src/pages/DocumentDetail.tsx
git commit -m "feat: compliance check tab

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 8: Sample documents with hour-scale deadlines

No existing sample states a deadline shorter than a day, so hour and minute handling has nothing to demonstrate against — and the check needs a case study to run on.

**Files:**
- Create: `samples/generate_escalation_samples.py`, `samples/Kanangra-Court-Incident-Escalation-Protocol.docx`, `samples/Kanangra-Court-Case-Study-Medication-Error.docx`
- Modify: `samples/README.md`

**Interfaces:**
- Consumes: `python-docx` (installed in the backend image; run the script inside the container).
- Produces: two `.docx` samples. `.docx` is already an accepted upload type, so no new dependency and no new format.

- [ ] **Step 1: Write the generator**

```python
# samples/generate_escalation_samples.py
"""Generate the two hour-scale sample documents.

python-docx lives in the backend image, and docker-compose mounts only ./backend
into it — so the script is fed to the container on stdin, writes into /app, and the
files are copied back out (see the plan's Task 8 Step 2 for the exact commands).

Everything here is fictional. The deadlines are deliberately short — minutes and
hours — because no other sample exercises sub-day timing.
"""

import os
from pathlib import Path

from docx import Document

OUT = Path(os.environ.get("SAMPLES_OUT", Path(__file__).parent))
MARKER = "SAMPLE — fictional document for demonstration"

PROTOCOL = [
    ("Kanangra Court Aged Care — Incident Escalation Protocol", 0),
    (MARKER, None),
    ("Part 1 Purpose", 1),
    ("This protocol sets the escalation steps and timeframes that apply when a "
     "medication incident, fall or unexplained absence occurs at Kanangra Court. "
     "Every provider, resident and reference in this document is fictional.", None),
    ("Part 2 Immediate response", 1),
    ("2.1 Clinical assessment", 2),
    ("The registered nurse on duty must assess the affected resident within 30 "
     "minutes of the incident being discovered and record the assessment in the "
     "clinical record.", None),
    ("2.2 Notifying the nurse in charge", 2),
    ("The registered nurse must notify the nurse in charge within 1 hour of the "
     "incident.", None),
    ("Part 3 Escalation", 1),
    ("3.1 Notifying the family or representative", 2),
    ("The facility manager must notify the resident's nominated representative "
     "within 4 hours of the incident.", None),
    ("3.2 Notifying the prescriber", 2),
    ("Where a medication was given in error, the prescriber must be contacted "
     "within 2 hours of the error being identified.", None),
    ("3.3 Reportable incident notification", 2),
    ("A Priority 1 reportable incident must be notified to the Aged Care Quality "
     "and Safety Commission within 24 hours of the provider becoming aware of it.", None),
    ("Part 4 Review", 1),
    ("4.1 Preliminary review", 2),
    ("The clinical governance lead must complete a preliminary review within 2 "
     "business days of the incident.", None),
    ("4.2 Full investigation", 2),
    ("A full investigation report must be submitted to the board within 30 days "
     "and 4 hours of the incident, to align with the Commission's reporting cycle.", None),
    ("4.3 Ongoing monitoring", 2),
    ("Medication administration audits must continue monthly for 6 months after "
     "any Priority 1 medication incident.", None),
]

CASE_STUDY = [
    ("Kanangra Court Aged Care — Case study: medication error, Resident K", 0),
    (MARKER, None),
    ("Incident summary", 1),
    ("The medication error occurred on 14 September 2026 at 3:10pm. Resident K was "
     "administered a dose of a medication prescribed for another resident during the "
     "afternoon medication round in Wing B.", None),
    ("Immediate response taken", 1),
    ("The registered nurse assessed Resident K at 3:25pm. Observations were within "
     "normal limits and were recorded in the clinical record at 3:40pm.", None),
    ("The nurse in charge was notified at 3:35pm and attended the wing.", None),
    ("The resident's daughter, the nominated representative, was telephoned at "
     "4:15pm and informed of the error and the observations taken.", None),
    ("Outstanding at the time of writing", 1),
    ("The prescriber had not been contacted at the time this record was written. "
     "The clinical governance lead has been asked to begin the preliminary review "
     "but has not yet scheduled it.", None),
    ("No notification has been made to the Aged Care Quality and Safety Commission; "
     "the facility manager is seeking advice on whether the incident meets the "
     "Priority 1 threshold.", None),
]


def _write(blocks, path: Path) -> None:
    doc = Document()
    for text, level in blocks:
        if level is None:
            doc.add_paragraph(text)
        else:
            doc.add_heading(text, level=level)
    doc.save(path)
    print(f"wrote {path}")


if __name__ == "__main__":
    _write(PROTOCOL, OUT / "Kanangra-Court-Incident-Escalation-Protocol.docx")
    _write(CASE_STUDY, OUT / "Kanangra-Court-Case-Study-Medication-Error.docx")
```

- [ ] **Step 2: Generate the files**

`docker-compose.yml` mounts only `./backend` into the backend container, so the script
is piped in and the output copied back:

```bash
docker compose exec -T -e SAMPLES_OUT=/app/_samples_out backend \
  sh -c 'mkdir -p /app/_samples_out && python -' < samples/generate_escalation_samples.py
docker compose cp backend:/app/_samples_out/Kanangra-Court-Incident-Escalation-Protocol.docx samples/
docker compose cp backend:/app/_samples_out/Kanangra-Court-Case-Study-Medication-Error.docx samples/
docker compose exec -T backend rm -rf /app/_samples_out
```

Expected: `wrote ...` twice, then two `.docx` files present in `samples/`.
`_samples_out` is removed because `./backend` is a bind mount — anything left there
lands in the repo.

- [ ] **Step 3: Check them end to end**

Upload `Kanangra-Court-Incident-Escalation-Protocol.docx` through the app. Confirm the Deadlines tab shows rows in the **Within 24 hours** bucket with times of day, not just dates. Then open its **Compliance Check** tab and upload `Kanangra-Court-Case-Study-Medication-Error.docx`. Expect roughly: family notification `done`, prescriber contact `not_done`, Commission notification `not_done` with an overdue or within-24-hours due time counted from 3:10pm on 14 September 2026, preliminary review `not_done` or `partly`, monthly audits `unclear`.

- [ ] **Step 4: Update the samples README**

Add the two documents to the table in `samples/README.md`, and add a short section under "Why they demo well":

```markdown
## Hour-scale deadlines and the compliance check

The Kanangra Court escalation protocol states deadlines in minutes and hours — 30
minutes, 1 hour, 2 hours, 4 hours, 24 hours, and "30 days and 4 hours" — so the
Deadlines tab shows due times rather than due dates, and the urgency buckets have
something short-dated to sort.

Its companion case study is the evidence document for the Compliance Check tab: it
states the incident time (14 September 2026, 3:10pm), records some escalation steps
as completed and leaves others outstanding, so a check against the protocol returns
a mix of done, not done and unclear verdicts.
```

- [ ] **Step 5: Commit**

```bash
git add samples/
git commit -m "feat: add hour-scale sample protocol and its case study

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 9: Documentation and graph refresh

**Files:**
- Modify: `project-understanding/04-api-reference.md`, `project-understanding/03-data-model.md`, `project-understanding/05-processing-pipeline.md`, `README.md` (feature list, if it carries one)

- [ ] **Step 1: Read what the docs currently say**

Run: `grep -n "deadlines\|Deadlines" project-understanding/03-data-model.md project-understanding/04-api-reference.md README.md`
Use what is there as the shape to match — these files describe every table and endpoint, and both sets grew in this work.

- [ ] **Step 2: Document the two new tables**

In `project-understanding/03-data-model.md`, add `compliance_checks` and `check_findings` beside the existing tables, including the `status` column added to `deadlines` in the previous iteration if it is not there yet.

- [ ] **Step 3: Document the endpoints**

In `project-understanding/04-api-reference.md`, add the four `/api/compliance-checks/...` routes and the `PATCH /api/deadlines/item/{id}` route, with the same level of detail the file uses for existing routes.

- [ ] **Step 4: Document the check pipeline**

In `project-understanding/05-processing-pipeline.md`, add a short section on the check: parse → incident time → batched verdicts → findings, and the 12,000-character evidence threshold.

- [ ] **Step 5: Refresh the knowledge graph**

Run: `graphify update .`
Expected: a rebuilt `graphify-out/graph.json` including the new modules.

- [ ] **Step 6: Commit**

```bash
git add project-understanding README.md graphify-out
git commit -m "docs: document the compliance check

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```
