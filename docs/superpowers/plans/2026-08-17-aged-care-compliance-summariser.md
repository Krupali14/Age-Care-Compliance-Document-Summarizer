# Aged Care Compliance Summariser Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the AI/NLP extraction pipeline (auth, upload, docling parsing, LLM extraction, dashboard, eval, chatbot) on top of the existing FastAPI/React/Postgres scaffold.

**Architecture:** FastAPI backend parses uploaded PDF/DOCX with docling into section chunks, runs one LangChain `ChatOpenAI` structured-output call per section to extract summary/obligations/risks/deadlines/action items, persists everything to Postgres with section-level source traceability, and serves it to a React dashboard. A standalone eval script scores extraction accuracy against hand-annotated ground truth.

**Tech Stack:** FastAPI, SQLAlchemy + Alembic, Postgres, docling, LangChain (`langchain-openai`), python-jose (JWT), passlib (bcrypt), React + React Query, Tailwind (existing).

**Spec:** `docs/superpowers/specs/2026-08-17-aged-care-compliance-summariser-design.md`

## Global Constraints

- LLM client: LangChain `ChatOpenAI`, configured via `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` env vars — no other LLM SDK.
- No queue infra (Celery/Redis) — use FastAPI `BackgroundTasks`.
- Doc parsing/chunking: docling only, section/heading-based (not fixed-token).
- Single-role auth (JWT), no RBAC.
- Every extracted row (obligation/risk/deadline/action) FKs to a `sections` row for source traceability.
- Per-section try/except during extraction — one bad section must not fail the whole document.
- Backend tests use `pytest` + FastAPI `TestClient` with a SQLite override for `get_db` (no real Postgres/LLM/docling in unit tests — those are mocked).

---

## File Structure

```
backend/app/
  config.py                  [new] env-driven settings (LLM + JWT config)
  auth.py                    [new] password hashing + JWT create/verify
  schemas.py                 [new] pydantic request/response models
  models/
    __init__.py               [modify] import all model modules
    user.py                   [new]
    document.py                [new]
    section.py                  [new]
    summary.py                   [new]
    obligation.py                 [new]
    risk.py                        [new]
    deadline.py                     [new]
    action_item.py                   [new]
    eval_run.py                       [new]
  services/
    docling_parser.py          [new] PDF/DOCX -> section list
    llm.py                      [new] ChatOpenAI factory
    extraction.py                [new] per-section structured extraction call
    processing.py                 [new] background pipeline orchestration
  routers/
    auth.py                     [new]
    upload.py                    [modify]
    documents.py                  [new] list/detail
    summarize.py                   [modify]
    obligations.py                  [modify]
    risks.py                         [modify]
    deadlines.py                      [modify]
    actions.py                         [modify]
    eval.py                             [new]
    chat.py                              [new, stretch]
  main.py                     [modify] register new routers
backend/scripts/eval.py       [new]
backend/ground_truth/sample_doc.json [new]
backend/tests/                [new] test_auth.py, test_upload.py, test_extraction.py, test_documents.py, test_eval.py
backend/requirements.txt      [modify]

frontend/src/
  api/client.ts                [new] fetch wrapper w/ auth header
  api/auth.ts                   [new]
  api/documents.ts               [new]
  context/AuthContext.tsx      [new]
  components/ProtectedRoute.tsx [new]
  components/CategoryTable.tsx   [new] shared table for obligations/risks/deadlines/actions
  components/ChatPanel.tsx        [new, stretch]
  pages/Login.tsx                [new]
  pages/Dashboard.tsx             [modify]
  pages/DocumentDetail.tsx         [new]
  pages/EvalPage.tsx                [new]
  App.tsx                        [modify]
frontend/package.json          [modify] add @tanstack/react-query
```

---

## Task 1: Backend dependencies + config

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/app/config.py`
- Create: `backend/tests/test_config.py`
- Modify: `.env.example`, `.env`

**Interfaces:**
- Produces: `app.config.settings` — a `Settings` instance with attributes `database_url: str`, `llm_base_url: str`, `llm_api_key: str`, `llm_model: str`, `jwt_secret: str`, `jwt_algorithm: str = "HS256"`, `jwt_expire_minutes: int = 60`.

- [ ] **Step 1: Add dependencies**

Append to `backend/requirements.txt`:
```
langchain-core==0.3.15
langchain-openai==0.2.6
docling==2.14.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
pydantic-settings==2.5.2
rapidfuzz==3.10.0
pytest==8.3.3
httpx==0.27.2
```

- [ ] **Step 2: Add env vars**

Append to `.env.example` and `.env`:
```
LLM_BASE_URL=https://integrate.api.nvidia.com/v1
LLM_API_KEY=changeme
LLM_MODEL=meta/llama-3.1-70b-instruct
JWT_SECRET=changeme-dev-secret
```

- [ ] **Step 3: Write the failing test**

```python
# backend/tests/test_config.py
import os

def test_settings_load_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/db")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.com/v1")
    monkeypatch.setenv("LLM_API_KEY", "key123")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("JWT_SECRET", "secret123")

    from app.config import Settings
    settings = Settings()

    assert settings.database_url == "postgresql://u:p@localhost/db"
    assert settings.llm_base_url == "https://example.com/v1"
    assert settings.llm_model == "test-model"
    assert settings.jwt_algorithm == "HS256"
    assert settings.jwt_expire_minutes == 60
```

- [ ] **Step 4: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_config.py -v`
Expected: FAIL with "No module named 'app.config'"

- [ ] **Step 5: Write implementation**

```python
# backend/app/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    model_config = {"env_file": ".env"}


settings = Settings()
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/requirements.txt backend/app/config.py backend/tests/test_config.py .env.example .env
git commit -m "Add LLM/JWT config settings"
```

---

## Task 2: Data models + migration

**Files:**
- Create: `backend/app/models/user.py`, `document.py`, `section.py`, `summary.py`, `obligation.py`, `risk.py`, `deadline.py`, `action_item.py`, `eval_run.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/tests/test_models.py`
- Create: `backend/alembic/versions/0001_initial_schema.py` (via `alembic revision --autogenerate`)

**Interfaces:**
- Consumes: `app.database.Base` (`backend/app/database.py:10`)
- Produces: ORM classes `User`, `Document`, `Section`, `Summary`, `Obligation`, `Risk`, `Deadline`, `ActionItem`, `EvalRun`, all importable from `app.models`. `Document.status` is a string column with values `"pending" | "processing" | "done" | "failed"`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_models.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    User, Document, Section, Summary, Obligation, Risk, Deadline, ActionItem, EvalRun,
)


def test_models_create_and_relate():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    user = User(email="a@b.com", hashed_password="hash")
    db.add(user)
    db.flush()

    doc = Document(user_id=user.id, filename="policy.pdf", file_type="pdf", status="pending")
    db.add(doc)
    db.flush()

    section = Section(document_id=doc.id, heading="Section 1", order_idx=0, page_ref="1", raw_text="text")
    db.add(section)
    db.flush()

    db.add(Summary(document_id=doc.id, text="summary text", model_used="test-model"))
    db.add(Obligation(document_id=doc.id, section_id=section.id, text="must do X", responsible_role="Manager", priority="high"))
    db.add(Risk(document_id=doc.id, section_id=section.id, text="risk of Y", severity="medium"))
    db.add(Deadline(document_id=doc.id, section_id=section.id, description="submit report", due_date=None, responsible_role="Nurse"))
    db.add(ActionItem(document_id=doc.id, section_id=section.id, text="do Z", responsible_role="Manager", timeframe="30 days", priority="low", source_section="Section 1"))
    db.add(EvalRun(document_id=doc.id, precision=0.9, recall=0.8, f1=0.85, ground_truth_ref="gt_1.json"))
    db.commit()

    assert db.query(Document).filter_by(id=doc.id).first().status == "pending"
    assert db.query(Obligation).filter_by(document_id=doc.id).first().responsible_role == "Manager"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_models.py -v`
Expected: FAIL with "No module named 'app.models.user'" (or ImportError)

- [ ] **Step 3: Write implementation**

```python
# backend/app/models/user.py
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    documents = relationship("Document", back_populates="user")
```

```python
# backend/app/models/document.py
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    error_message = Column(String, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="documents")
    sections = relationship("Section", back_populates="document", cascade="all, delete-orphan")
```

```python
# backend/app/models/section.py
from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Section(Base):
    __tablename__ = "sections"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    heading = Column(String, nullable=False)
    order_idx = Column(Integer, nullable=False)
    page_ref = Column(String, nullable=True)
    raw_text = Column(Text, nullable=False)

    document = relationship("Document", back_populates="sections")
```

```python
# backend/app/models/summary.py
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text

from app.database import Base


class Summary(Base):
    __tablename__ = "summaries"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    text = Column(Text, nullable=False)
    model_used = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

```python
# backend/app/models/obligation.py
from sqlalchemy import Column, ForeignKey, Integer, String, Text

from app.database import Base


class Obligation(Base):
    __tablename__ = "obligations"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=False)
    text = Column(Text, nullable=False)
    responsible_role = Column(String, nullable=True)
    priority = Column(String, nullable=True)
```

```python
# backend/app/models/risk.py
from sqlalchemy import Column, ForeignKey, Integer, String, Text

from app.database import Base


class Risk(Base):
    __tablename__ = "risks"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=False)
    text = Column(Text, nullable=False)
    severity = Column(String, nullable=False)
```

```python
# backend/app/models/deadline.py
from sqlalchemy import Column, ForeignKey, Integer, String, Text

from app.database import Base


class Deadline(Base):
    __tablename__ = "deadlines"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=False)
    description = Column(Text, nullable=False)
    due_date = Column(String, nullable=True)
    responsible_role = Column(String, nullable=True)
```

```python
# backend/app/models/action_item.py
from sqlalchemy import Column, ForeignKey, Integer, String, Text

from app.database import Base


class ActionItem(Base):
    __tablename__ = "action_items"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=False)
    text = Column(Text, nullable=False)
    responsible_role = Column(String, nullable=True)
    timeframe = Column(String, nullable=True)
    priority = Column(String, nullable=True)
    source_section = Column(String, nullable=True)
```

```python
# backend/app/models/eval_run.py
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String

from app.database import Base


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    precision = Column(Float, nullable=False)
    recall = Column(Float, nullable=False)
    f1 = Column(Float, nullable=False)
    ground_truth_ref = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

```python
# backend/app/models/__init__.py
from app.models.user import User
from app.models.document import Document
from app.models.section import Section
from app.models.summary import Summary
from app.models.obligation import Obligation
from app.models.risk import Risk
from app.models.deadline import Deadline
from app.models.action_item import ActionItem
from app.models.eval_run import EvalRun

__all__ = [
    "User", "Document", "Section", "Summary", "Obligation",
    "Risk", "Deadline", "ActionItem", "EvalRun",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_models.py -v`
Expected: PASS

- [ ] **Step 5: Generate Alembic migration**

Run (inside the backend container, DB must be up — `make up` first):
```bash
make migrate  # ensures DB reachable
docker compose exec backend alembic revision --autogenerate -m "initial schema"
docker compose exec backend alembic upgrade head
```
Verify the generated file under `backend/alembic/versions/` creates all 9 tables (check its `upgrade()` body lists `users`, `documents`, `sections`, `summaries`, `obligations`, `risks`, `deadlines`, `action_items`, `eval_runs`).

- [ ] **Step 6: Commit**

```bash
git add backend/app/models backend/alembic/versions backend/tests/test_models.py
git commit -m "Add data models and initial migration"
```

---

## Task 3: Auth (JWT)

**Files:**
- Create: `backend/app/auth.py`
- Create: `backend/app/schemas.py` (auth section)
- Create: `backend/app/routers/auth.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/conftest.py` (shared TestClient + SQLite override fixture, used by all remaining backend test files)
- Create: `backend/tests/test_auth.py`

**Interfaces:**
- Consumes: `app.database.get_db` (`backend/app/database.py:13`), `app.config.settings` (Task 1), `app.models.User` (Task 2)
- Produces: `app.auth.hash_password(password: str) -> str`, `app.auth.verify_password(password: str, hashed: str) -> bool`, `app.auth.create_access_token(user_id: int) -> str`, `app.auth.get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User` — a FastAPI dependency later routers import for auth-gating. `POST /api/auth/register` and `POST /api/auth/login` (form: `email`, `password`) returning `{"access_token": str, "token_type": "bearer"}`.

- [ ] **Step 1: Write the shared test fixture**

```python
# backend/tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
```

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/test_auth.py
def test_register_then_login(client):
    resp = client.post("/api/auth/register", json={"email": "a@b.com", "password": "secret123"})
    assert resp.status_code == 201

    resp = client.post("/api/auth/login", data={"username": "a@b.com", "password": "secret123"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password_rejected(client):
    client.post("/api/auth/register", json={"email": "a@b.com", "password": "secret123"})
    resp = client.post("/api/auth/login", data={"username": "a@b.com", "password": "wrong"})
    assert resp.status_code == 401
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_auth.py -v`
Expected: FAIL (404, routes don't exist yet)

- [ ] **Step 4: Write implementation**

```python
# backend/app/auth.py
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def create_access_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise credentials_error

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_error
    return user
```

```python
# backend/app/schemas.py
from pydantic import BaseModel


class RegisterRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
```

```python
# backend/app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models import User
from app.schemas import RegisterRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    return {"id": user.id, "email": user.email}


@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = create_access_token(user.id)
    return TokenResponse(access_token=token)
```

Modify `backend/app/main.py` — add import and `app.include_router(auth.router)`:
```python
from app.routers import actions, auth, deadlines, obligations, risks, summarize, upload
...
app.include_router(auth.router)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_auth.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/auth.py backend/app/schemas.py backend/app/routers/auth.py backend/app/main.py backend/tests/conftest.py backend/tests/test_auth.py
git commit -m "Add JWT auth (register/login)"
```

---

## Task 4: Document upload

**Files:**
- Modify: `backend/app/routers/upload.py`
- Modify: `backend/app/schemas.py`
- Create: `backend/tests/test_upload.py`
- Modify: `docker-compose.yml` (add a named volume for uploaded files if not present)

**Interfaces:**
- Consumes: `get_current_user` (Task 3), `Document` model (Task 2)
- Produces: `POST /api/upload` (multipart file, auth required) → `{"id": int, "filename": str, "status": "pending"}`. Files saved to `UPLOAD_DIR` (env var, default `/app/uploads`) as `<document_id>_<original_filename>`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_upload.py
import io


def _auth_header(client):
    client.post("/api/auth/register", json={"email": "a@b.com", "password": "secret123"})
    resp = client.post("/api/auth/login", data={"username": "a@b.com", "password": "secret123"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_upload_requires_auth(client):
    resp = client.post("/api/upload", files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")})
    assert resp.status_code == 401


def test_upload_creates_pending_document(client, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    headers = _auth_header(client)
    resp = client.post(
        "/api/upload",
        headers=headers,
        files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["filename"] == "doc.pdf"
    assert body["status"] == "pending"


def test_upload_rejects_unsupported_type(client):
    headers = _auth_header(client)
    resp = client.post(
        "/api/upload",
        headers=headers,
        files={"file": ("doc.txt", io.BytesIO(b"plain text"), "text/plain")},
    )
    assert resp.status_code == 400
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_upload.py -v`
Expected: FAIL (`{"status": "not_implemented"}` response, 200 not 201)

- [ ] **Step 3: Write implementation**

```python
# backend/app/routers/upload.py
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Document, User

router = APIRouter(prefix="/api", tags=["upload"])

ALLOWED_TYPES = {".pdf", ".docx"}


@router.post("/upload", status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")

    document = Document(
        user_id=user.id,
        filename=file.filename,
        file_type=ext.lstrip("."),
        status="pending",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    upload_dir = Path(os.environ.get("UPLOAD_DIR", "/app/uploads"))
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / f"{document.id}_{file.filename}"
    with dest.open("wb") as f:
        f.write(file.file.read())

    return {"id": document.id, "filename": document.filename, "status": document.status}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_upload.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/upload.py backend/tests/test_upload.py
git commit -m "Implement document upload endpoint"
```

---

## Task 5: Docling parsing + section splitting

**Files:**
- Create: `backend/app/services/docling_parser.py`
- Create: `backend/tests/test_docling_parser.py`

**Interfaces:**
- Produces: `app.services.docling_parser.parse_document(file_path: str) -> list[ParsedSection]`, where `ParsedSection` is a `dataclass(heading: str, order_idx: int, page_ref: str | None, raw_text: str)`.

- [ ] **Step 1: Write the failing test**

Mock docling's `DocumentConverter` so the test doesn't depend on real parsing:

```python
# backend/tests/test_docling_parser.py
from unittest.mock import MagicMock, patch


def test_parse_document_splits_into_sections():
    fake_result = MagicMock()
    fake_result.document.export_to_markdown.return_value = (
        "# Introduction\nThis is the intro.\n\n"
        "# Obligations\nStaff must report incidents within 24 hours.\n"
    )

    with patch("app.services.docling_parser.DocumentConverter") as MockConverter:
        MockConverter.return_value.convert.return_value = fake_result

        from app.services.docling_parser import parse_document
        sections = parse_document("/tmp/fake.pdf")

    assert len(sections) == 2
    assert sections[0].heading == "Introduction"
    assert sections[0].order_idx == 0
    assert "intro" in sections[0].raw_text
    assert sections[1].heading == "Obligations"
    assert sections[1].order_idx == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_docling_parser.py -v`
Expected: FAIL with "No module named 'app.services'"

- [ ] **Step 3: Write implementation**

```python
# backend/app/services/docling_parser.py
import re
from dataclasses import dataclass

from docling.document_converter import DocumentConverter


@dataclass
class ParsedSection:
    heading: str
    order_idx: int
    page_ref: str | None
    raw_text: str


def parse_document(file_path: str) -> list[ParsedSection]:
    converter = DocumentConverter()
    result = converter.convert(file_path)
    markdown = result.document.export_to_markdown()

    parts = re.split(r"^#\s+(.+)$", markdown, flags=re.MULTILINE)
    # parts[0] is any preamble before the first heading; then alternating (heading, body)
    sections: list[ParsedSection] = []
    order_idx = 0
    for i in range(1, len(parts), 2):
        heading = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        sections.append(ParsedSection(heading=heading, order_idx=order_idx, page_ref=None, raw_text=body))
        order_idx += 1

    if not sections and markdown.strip():
        sections.append(ParsedSection(heading="Document", order_idx=0, page_ref=None, raw_text=markdown.strip()))

    return sections
```

Add a `backend/app/services/__init__.py` (empty file) so the package imports.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_docling_parser.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/__init__.py backend/app/services/docling_parser.py backend/tests/test_docling_parser.py
git commit -m "Add docling-based section parsing"
```

---

## Task 6: LLM structured extraction

**Files:**
- Create: `backend/app/services/llm.py`
- Create: `backend/app/services/extraction.py`
- Create: `backend/tests/test_extraction.py`

**Interfaces:**
- Consumes: `app.config.settings` (Task 1), `ParsedSection` (Task 5)
- Produces: `app.services.llm.get_llm() -> ChatOpenAI`. `app.services.extraction.SectionExtraction` (pydantic model: `summary: str`, `obligations: list[ExtractedObligation]`, `risks: list[ExtractedRisk]`, `deadlines: list[ExtractedDeadline]`, `action_items: list[ExtractedActionItem]`). `app.services.extraction.extract_section(section: ParsedSection) -> SectionExtraction`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_extraction.py
from unittest.mock import MagicMock, patch

from app.services.docling_parser import ParsedSection


def test_extract_section_calls_llm_with_structured_output():
    fake_extraction = MagicMock()
    fake_structured_llm = MagicMock()
    fake_structured_llm.invoke.return_value = fake_extraction

    fake_llm = MagicMock()
    fake_llm.with_structured_output.return_value = fake_structured_llm

    section = ParsedSection(heading="Obligations", order_idx=0, page_ref=None, raw_text="Staff must report incidents.")

    with patch("app.services.extraction.get_llm", return_value=fake_llm):
        from app.services.extraction import extract_section
        result = extract_section(section)

    assert result is fake_extraction
    fake_llm.with_structured_output.assert_called_once()
    fake_structured_llm.invoke.assert_called_once()
    call_arg = fake_structured_llm.invoke.call_args[0][0]
    assert "Obligations" in call_arg
    assert "Staff must report incidents." in call_arg
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_extraction.py -v`
Expected: FAIL with "No module named 'app.services.extraction'"

- [ ] **Step 3: Write implementation**

```python
# backend/app/services/llm.py
from langchain_openai import ChatOpenAI

from app.config import settings


def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        temperature=0,
    )
```

```python
# backend/app/services/extraction.py
from typing import Literal

from pydantic import BaseModel

from app.services.docling_parser import ParsedSection
from app.services.llm import get_llm


class ExtractedObligation(BaseModel):
    text: str
    responsible_role: str | None = None
    priority: Literal["high", "medium", "low"] | None = None


class ExtractedRisk(BaseModel):
    text: str
    severity: Literal["high", "medium", "low"]


class ExtractedDeadline(BaseModel):
    description: str
    due_date: str | None = None
    responsible_role: str | None = None


class ExtractedActionItem(BaseModel):
    text: str
    responsible_role: str | None = None
    timeframe: str | None = None
    priority: Literal["high", "medium", "low"] | None = None


class SectionExtraction(BaseModel):
    summary: str
    obligations: list[ExtractedObligation] = []
    risks: list[ExtractedRisk] = []
    deadlines: list[ExtractedDeadline] = []
    action_items: list[ExtractedActionItem] = []


PROMPT_TEMPLATE = """You are analysing a section of an aged-care compliance document.

Section heading: {heading}
Section text:
{text}

Extract: a short summary of this section, any obligations (things people/the \
organisation are required to do), any risks (with severity high/medium/low), \
any deadlines (with responsible role if stated), and any action items (with \
responsible role, timeframe, and priority where possible). Only extract what \
is explicitly stated or clearly implied in the text — do not invent details."""


def extract_section(section: ParsedSection) -> SectionExtraction:
    llm = get_llm()
    structured_llm = llm.with_structured_output(SectionExtraction)
    prompt = PROMPT_TEMPLATE.format(heading=section.heading, text=section.raw_text)
    return structured_llm.invoke(prompt)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_extraction.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/llm.py backend/app/services/extraction.py backend/tests/test_extraction.py
git commit -m "Add LLM structured extraction service"
```

---

## Task 7: Background processing pipeline

**Files:**
- Create: `backend/app/services/processing.py`
- Modify: `backend/app/routers/upload.py` (kick off background task)
- Create: `backend/tests/test_processing.py`

**Interfaces:**
- Consumes: `parse_document` (Task 5), `extract_section` (Task 6), `Document`/`Section`/`Summary`/`Obligation`/`Risk`/`Deadline`/`ActionItem` models (Task 2), `SessionLocal` (`backend/app/database.py:9`)
- Produces: `app.services.processing.process_document(document_id: int, file_path: str) -> None` — parses, extracts per-section (catching exceptions per section), persists all rows, sets `Document.status` to `"done"` or `"failed"` (+ `error_message`).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_processing.py
from unittest.mock import MagicMock, patch

from app.database import Base
from app.models import Document, User, Section, Summary, Obligation, Risk, Deadline, ActionItem
from app.services.docling_parser import ParsedSection
from app.services.extraction import (
    ExtractedActionItem, ExtractedDeadline, ExtractedObligation, ExtractedRisk, SectionExtraction,
)


def _make_db(engine):
    from sqlalchemy.orm import sessionmaker
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_process_document_persists_extraction(monkeypatch):
    from sqlalchemy import create_engine
    engine = create_engine("sqlite:///:memory:")
    db = _make_db(engine)

    user = User(email="a@b.com", hashed_password="h")
    db.add(user)
    db.flush()
    doc = Document(user_id=user.id, filename="doc.pdf", file_type="pdf", status="pending")
    db.add(doc)
    db.commit()

    fake_sections = [ParsedSection(heading="Obligations", order_idx=0, page_ref=None, raw_text="Staff must report incidents.")]
    fake_extraction = SectionExtraction(
        summary="Staff must report incidents.",
        obligations=[ExtractedObligation(text="Report incidents", responsible_role="Staff", priority="high")],
        risks=[ExtractedRisk(text="Delayed reporting", severity="medium")],
        deadlines=[ExtractedDeadline(description="Report within 24h", due_date=None, responsible_role="Staff")],
        action_items=[ExtractedActionItem(text="File incident report", responsible_role="Staff", timeframe="24h", priority="high")],
    )

    with patch("app.services.processing.SessionLocal", return_value=db), \
         patch("app.services.processing.parse_document", return_value=fake_sections), \
         patch("app.services.processing.extract_section", return_value=fake_extraction):
        from app.services.processing import process_document
        process_document(doc.id, "/tmp/doc.pdf")

    db.refresh(doc)
    assert doc.status == "done"
    assert db.query(Section).filter_by(document_id=doc.id).count() == 1
    assert db.query(Summary).filter_by(document_id=doc.id).count() == 1
    assert db.query(Obligation).filter_by(document_id=doc.id).count() == 1
    assert db.query(Risk).filter_by(document_id=doc.id).count() == 1
    assert db.query(Deadline).filter_by(document_id=doc.id).count() == 1
    assert db.query(ActionItem).filter_by(document_id=doc.id).count() == 1


def test_process_document_survives_section_failure():
    from sqlalchemy import create_engine
    engine = create_engine("sqlite:///:memory:")
    db = _make_db(engine)

    user = User(email="a@b.com", hashed_password="h")
    db.add(user)
    db.flush()
    doc = Document(user_id=user.id, filename="doc.pdf", file_type="pdf", status="pending")
    db.add(doc)
    db.commit()

    fake_sections = [ParsedSection(heading="Bad", order_idx=0, page_ref=None, raw_text="text")]

    with patch("app.services.processing.SessionLocal", return_value=db), \
         patch("app.services.processing.parse_document", return_value=fake_sections), \
         patch("app.services.processing.extract_section", side_effect=RuntimeError("LLM error")):
        from app.services.processing import process_document
        process_document(doc.id, "/tmp/doc.pdf")

    db.refresh(doc)
    assert doc.status == "done"
    assert db.query(Section).filter_by(document_id=doc.id).count() == 1
    assert db.query(Summary).filter_by(document_id=doc.id).count() == 0


def test_process_document_marks_failed_on_parse_error():
    from sqlalchemy import create_engine
    engine = create_engine("sqlite:///:memory:")
    db = _make_db(engine)

    user = User(email="a@b.com", hashed_password="h")
    db.add(user)
    db.flush()
    doc = Document(user_id=user.id, filename="doc.pdf", file_type="pdf", status="pending")
    db.add(doc)
    db.commit()

    with patch("app.services.processing.SessionLocal", return_value=db), \
         patch("app.services.processing.parse_document", side_effect=RuntimeError("cannot parse")):
        from app.services.processing import process_document
        process_document(doc.id, "/tmp/doc.pdf")

    db.refresh(doc)
    assert doc.status == "failed"
    assert doc.error_message == "cannot parse"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_processing.py -v`
Expected: FAIL with "No module named 'app.services.processing'"

- [ ] **Step 3: Write implementation**

```python
# backend/app/services/processing.py
from app.database import SessionLocal
from app.models import ActionItem, Deadline, Document, Obligation, Risk, Section, Summary
from app.services.docling_parser import parse_document
from app.services.extraction import extract_section


def process_document(document_id: int, file_path: str) -> None:
    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        document.status = "processing"
        db.commit()

        try:
            parsed_sections = parse_document(file_path)
        except Exception as exc:  # noqa: BLE001 - unrecoverable parse failure
            document.status = "failed"
            document.error_message = str(exc)
            db.commit()
            return

        summary_parts = []
        for parsed in parsed_sections:
            section = Section(
                document_id=document.id,
                heading=parsed.heading,
                order_idx=parsed.order_idx,
                page_ref=parsed.page_ref,
                raw_text=parsed.raw_text,
            )
            db.add(section)
            db.flush()

            try:
                extraction = extract_section(parsed)
            except Exception:  # noqa: BLE001 - one bad section shouldn't fail the doc
                continue

            summary_parts.append(extraction.summary)
            for o in extraction.obligations:
                db.add(Obligation(document_id=document.id, section_id=section.id, text=o.text, responsible_role=o.responsible_role, priority=o.priority))
            for r in extraction.risks:
                db.add(Risk(document_id=document.id, section_id=section.id, text=r.text, severity=r.severity))
            for d in extraction.deadlines:
                db.add(Deadline(document_id=document.id, section_id=section.id, description=d.description, due_date=d.due_date, responsible_role=d.responsible_role))
            for a in extraction.action_items:
                db.add(ActionItem(document_id=document.id, section_id=section.id, text=a.text, responsible_role=a.responsible_role, timeframe=a.timeframe, priority=a.priority, source_section=parsed.heading))

        if summary_parts:
            db.add(Summary(document_id=document.id, text="\n\n".join(summary_parts), model_used="section-wise"))

        document.status = "done"
        db.commit()
    finally:
        db.close()
```

Modify `backend/app/routers/upload.py` to kick off the background task — add `BackgroundTasks` param and, after saving the file:

```python
from fastapi import BackgroundTasks
from app.services.processing import process_document
...
def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ...
    background_tasks.add_task(process_document, document.id, str(dest))
    return {"id": document.id, "filename": document.filename, "status": document.status}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_processing.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/processing.py backend/app/routers/upload.py backend/tests/test_processing.py
git commit -m "Wire background extraction pipeline into upload"
```

---

## Task 8: Read endpoints (documents, summarize, obligations, risks, deadlines, actions)

**Files:**
- Create: `backend/app/routers/documents.py`
- Modify: `backend/app/routers/summarize.py`, `obligations.py`, `risks.py`, `deadlines.py`, `actions.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_documents.py`

**Interfaces:**
- Consumes: `get_current_user` (Task 3), all models (Task 2)
- Produces: `GET /api/documents` (auth, list current user's docs w/ status), `GET /api/documents/{id}` (doc + sections), `GET /api/summarize/{doc_id}`, `GET /api/obligations/{doc_id}`, `GET /api/risks/{doc_id}`, `GET /api/deadlines/{doc_id}`, `GET /api/actions/{doc_id}` — all auth-gated, 404 if the document doesn't belong to the caller.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_documents.py
import io


def _auth_header(client, email="a@b.com"):
    client.post("/api/auth/register", json={"email": email, "password": "secret123"})
    resp = client.post("/api/auth/login", data={"username": email, "password": "secret123"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_list_documents_scoped_to_user(client, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    headers_a = _auth_header(client, "a@b.com")
    headers_b = _auth_header(client, "b@b.com")

    client.post("/api/upload", headers=headers_a, files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")})

    resp_a = client.get("/api/documents", headers=headers_a)
    resp_b = client.get("/api/documents", headers=headers_b)

    assert len(resp_a.json()) == 1
    assert len(resp_b.json()) == 0


def test_get_document_not_owned_returns_404(client, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    headers_a = _auth_header(client, "a@b.com")
    headers_b = _auth_header(client, "b@b.com")

    upload_resp = client.post("/api/upload", headers=headers_a, files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")})
    doc_id = upload_resp.json()["id"]

    resp = client.get(f"/api/documents/{doc_id}", headers=headers_b)
    assert resp.status_code == 404


def test_category_endpoints_return_empty_lists_before_processing(client, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    headers = _auth_header(client)
    upload_resp = client.post("/api/upload", headers=headers, files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")})
    doc_id = upload_resp.json()["id"]

    for path in ["summarize", "obligations", "risks", "deadlines", "actions"]:
        resp = client.get(f"/api/{path}/{doc_id}", headers=headers)
        assert resp.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_documents.py -v`
Expected: FAIL (routes are `/api/summarize` with no `{doc_id}`, no `/api/documents`)

- [ ] **Step 3: Write implementation**

```python
# backend/app/routers/documents.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Document, User

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _get_owned_document(doc_id: int, db: Session, user: User) -> Document:
    document = db.query(Document).filter(Document.id == doc_id, Document.user_id == user.id).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.get("")
def list_documents(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    docs = db.query(Document).filter(Document.user_id == user.id).all()
    return [{"id": d.id, "filename": d.filename, "status": d.status, "uploaded_at": d.uploaded_at} for d in docs]


@router.get("/{doc_id}")
def get_document(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    document = _get_owned_document(doc_id, db, user)
    return {
        "id": document.id,
        "filename": document.filename,
        "status": document.status,
        "error_message": document.error_message,
        "sections": [
            {"id": s.id, "heading": s.heading, "order_idx": s.order_idx, "page_ref": s.page_ref}
            for s in sorted(document.sections, key=lambda s: s.order_idx)
        ],
    }
```

```python
# backend/app/routers/summarize.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Summary, User
from app.routers.documents import _get_owned_document

router = APIRouter(prefix="/api/summarize", tags=["summarize"])


@router.get("/{doc_id}")
def get_summaries(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _get_owned_document(doc_id, db, user)
    summaries = db.query(Summary).filter(Summary.document_id == doc_id).all()
    return [{"id": s.id, "text": s.text, "model_used": s.model_used} for s in summaries]
```

```python
# backend/app/routers/obligations.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Obligation, User
from app.routers.documents import _get_owned_document

router = APIRouter(prefix="/api/obligations", tags=["obligations"])


@router.get("/{doc_id}")
def get_obligations(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _get_owned_document(doc_id, db, user)
    rows = db.query(Obligation).filter(Obligation.document_id == doc_id).all()
    return [{"id": o.id, "section_id": o.section_id, "text": o.text, "responsible_role": o.responsible_role, "priority": o.priority} for o in rows]
```

```python
# backend/app/routers/risks.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Risk, User
from app.routers.documents import _get_owned_document

router = APIRouter(prefix="/api/risks", tags=["risks"])


@router.get("/{doc_id}")
def get_risks(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _get_owned_document(doc_id, db, user)
    rows = db.query(Risk).filter(Risk.document_id == doc_id).all()
    return [{"id": r.id, "section_id": r.section_id, "text": r.text, "severity": r.severity} for r in rows]
```

```python
# backend/app/routers/deadlines.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Deadline, User
from app.routers.documents import _get_owned_document

router = APIRouter(prefix="/api/deadlines", tags=["deadlines"])


@router.get("/{doc_id}")
def get_deadlines(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _get_owned_document(doc_id, db, user)
    rows = db.query(Deadline).filter(Deadline.document_id == doc_id).all()
    return [{"id": d.id, "section_id": d.section_id, "description": d.description, "due_date": d.due_date, "responsible_role": d.responsible_role} for d in rows]
```

```python
# backend/app/routers/actions.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import ActionItem, User
from app.routers.documents import _get_owned_document

router = APIRouter(prefix="/api/actions", tags=["actions"])


@router.get("/{doc_id}")
def get_action_items(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _get_owned_document(doc_id, db, user)
    rows = db.query(ActionItem).filter(ActionItem.document_id == doc_id).all()
    return [{"id": a.id, "section_id": a.section_id, "text": a.text, "responsible_role": a.responsible_role, "timeframe": a.timeframe, "priority": a.priority, "source_section": a.source_section} for a in rows]
```

Modify `backend/app/main.py` to add `documents` router:
```python
from app.routers import actions, auth, deadlines, documents, obligations, risks, summarize, upload
...
app.include_router(documents.router)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_documents.py -v`
Expected: PASS

- [ ] **Step 5: Run full backend test suite**

Run: `cd backend && python -m pytest -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers backend/app/main.py backend/tests/test_documents.py
git commit -m "Implement document read endpoints"
```

---

## Task 9: Frontend auth (API client, context, login page, protected routes)

**Files:**
- Create: `frontend/src/api/client.ts`, `frontend/src/api/auth.ts`
- Create: `frontend/src/context/AuthContext.tsx`
- Create: `frontend/src/components/ProtectedRoute.tsx`
- Create: `frontend/src/pages/Login.tsx`
- Modify: `frontend/src/App.tsx`, `frontend/src/pages/Landing.tsx`, `frontend/package.json`

**Interfaces:**
- Produces: `AuthContext` exposing `{ token: string | null, login: (email, password) => Promise<void>, register: (email, password) => Promise<void>, logout: () => void }`. `apiFetch(path: string, options?: RequestInit) -> Promise<Response>` — attaches `Authorization: Bearer <token>` from localStorage.

- [ ] **Step 1: Add React Query dependency**

```bash
cd frontend && npm install @tanstack/react-query
```

- [ ] **Step 2: Write API client**

```typescript
// frontend/src/api/client.ts
const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8002";

export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const token = localStorage.getItem("token");
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status}: ${body}`);
  }
  return response;
}
```

```typescript
// frontend/src/api/auth.ts
import { apiFetch } from "./client";

export async function register(email: string, password: string): Promise<void> {
  await apiFetch("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export async function login(email: string, password: string): Promise<string> {
  const form = new URLSearchParams();
  form.set("username", email);
  form.set("password", password);
  const resp = await apiFetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form,
  });
  const data = await resp.json();
  return data.access_token as string;
}
```

- [ ] **Step 3: Write auth context**

```typescript
// frontend/src/context/AuthContext.tsx
import { createContext, useContext, useState, ReactNode } from "react";
import * as authApi from "../api/auth";

interface AuthContextValue {
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(localStorage.getItem("token"));

  async function login(email: string, password: string) {
    const t = await authApi.login(email, password);
    localStorage.setItem("token", t);
    setToken(t);
  }

  async function register(email: string, password: string) {
    await authApi.register(email, password);
    await login(email, password);
  }

  function logout() {
    localStorage.removeItem("token");
    setToken(null);
  }

  return (
    <AuthContext.Provider value={{ token, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
```

```typescript
// frontend/src/components/ProtectedRoute.tsx
import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute() {
  const { token } = useAuth();
  return token ? <Outlet /> : <Navigate to="/login" replace />;
}
```

```typescript
// frontend/src/pages/Login.tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState<string | null>(null);
  const { login, register } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password);
      navigate("/dashboard");
    } catch {
      setError("Authentication failed. Check your credentials.");
    }
  }

  return (
    <div className="mx-auto mt-24 max-w-sm px-6">
      <h1 className="text-2xl font-semibold text-slate-900">
        {mode === "login" ? "Sign in" : "Create an account"}
      </h1>
      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <input
          type="email"
          required
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full rounded-md border border-slate-300 px-3 py-2"
        />
        <input
          type="password"
          required
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full rounded-md border border-slate-300 px-3 py-2"
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button type="submit" className="w-full rounded-md bg-brand-600 px-4 py-2 text-white">
          {mode === "login" ? "Sign in" : "Register"}
        </button>
      </form>
      <button
        onClick={() => setMode(mode === "login" ? "register" : "login")}
        className="mt-4 text-sm text-brand-700 underline"
      >
        {mode === "login" ? "Need an account? Register" : "Already have an account? Sign in"}
      </button>
    </div>
  );
}
```

- [ ] **Step 4: Wire routes**

Modify `frontend/src/App.tsx`:
```typescript
import { Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import DashboardLayout from "./components/DashboardLayout";
import DocumentDetail from "./pages/DocumentDetail";

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={<DashboardLayout />}>
              <Route index element={<Dashboard />} />
              <Route path="documents/:id" element={<DocumentDetail />} />
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </QueryClientProvider>
  );
}
```

Modify `frontend/src/pages/Landing.tsx` — change `navigate("/dashboard")` on the "Sign in" button (line 31) to `navigate("/login")`.

Note: `DocumentDetail` is created in Task 11 — this task's build will fail to compile until then; that's expected mid-plan and is fixed by Task 11. If executing tasks out of order, stub `frontend/src/pages/DocumentDetail.tsx` with a one-line placeholder export in this task and let Task 11 replace it.

- [ ] **Step 5: Manual verification**

Run: `make up`, open `http://localhost:3002`, click "Sign in" → register a user → confirm redirect to `/dashboard` and `localStorage` has a `token`.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api frontend/src/context frontend/src/components/ProtectedRoute.tsx frontend/src/pages/Login.tsx frontend/src/App.tsx frontend/src/pages/Landing.tsx frontend/package.json frontend/package-lock.json
git commit -m "Add frontend auth (login/register, protected routes)"
```

---

## Task 10: Dashboard — upload + document list

**Files:**
- Create: `frontend/src/api/documents.ts`
- Modify: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/App.tsx` (drop the now-unused placeholder section routes/imports)

**Interfaces:**
- Consumes: `apiFetch` (Task 9)
- Produces: `listDocuments() -> Promise<DocumentSummary[]>`, `uploadDocument(file: File) -> Promise<DocumentSummary>`, where `DocumentSummary = { id: number, filename: string, status: string, uploaded_at: string }`.

- [ ] **Step 1: Write API functions**

```typescript
// frontend/src/api/documents.ts
import { apiFetch } from "./client";

export interface DocumentSummary {
  id: number;
  filename: string;
  status: "pending" | "processing" | "done" | "failed";
  uploaded_at: string;
}

export async function listDocuments(): Promise<DocumentSummary[]> {
  const resp = await apiFetch("/api/documents");
  return resp.json();
}

export async function uploadDocument(file: File): Promise<DocumentSummary> {
  const form = new FormData();
  form.set("file", file);
  const resp = await apiFetch("/api/upload", { method: "POST", body: form });
  return resp.json();
}
```

- [ ] **Step 2: Rewrite Dashboard page**

```typescript
// frontend/src/pages/Dashboard.tsx
import { useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { listDocuments, uploadDocument } from "../api/documents";

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-slate-100 text-slate-700",
  processing: "bg-amber-100 text-amber-700",
  done: "bg-emerald-100 text-emerald-700",
  failed: "bg-red-100 text-red-700",
};

export default function Dashboard() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const fileInput = useRef<HTMLInputElement>(null);

  const { data: documents, isLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: listDocuments,
    refetchInterval: 4000,
  });

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    await uploadDocument(file);
    queryClient.invalidateQueries({ queryKey: ["documents"] });
    if (fileInput.current) fileInput.current.value = "";
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-900">Documents</h1>
        <label className="cursor-pointer rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700">
          Upload document
          <input ref={fileInput} type="file" accept=".pdf,.docx" className="hidden" onChange={handleUpload} />
        </label>
      </div>

      <div className="mt-6 rounded-xl border border-slate-200 bg-white">
        {isLoading && <p className="p-6 text-slate-500">Loading...</p>}
        {!isLoading && documents?.length === 0 && (
          <p className="p-6 text-slate-500">No documents yet. Upload a PDF or DOCX to get started.</p>
        )}
        {documents?.map((doc) => (
          <button
            key={doc.id}
            onClick={() => navigate(`/dashboard/documents/${doc.id}`)}
            className="flex w-full items-center justify-between border-b border-slate-100 px-6 py-4 text-left last:border-none hover:bg-slate-50"
          >
            <span className="text-slate-900">{doc.filename}</span>
            <span className={`rounded-full px-3 py-1 text-xs font-medium ${STATUS_STYLES[doc.status]}`}>
              {doc.status}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Remove obsolete placeholder routes**

In `frontend/src/App.tsx`, remove the `UploadSection`/`SummariesSection`/`ObligationsRisksSection`/`DeadlinesSection`/`ActionItemsSection` import and their `<Route>` entries (they were placeholders superseded by `DocumentDetail`).

- [ ] **Step 4: Manual verification**

Run: `make up`, log in, upload a small PDF, confirm it appears in the list with status `pending` and updates to `processing`/`done` within ~4s polling.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/documents.ts frontend/src/pages/Dashboard.tsx frontend/src/App.tsx
git commit -m "Wire dashboard to real upload/list endpoints"
```

---

## Task 11: Document detail page (category tabs + source traceability + disclaimer)

**Files:**
- Create: `frontend/src/api/extractions.ts`
- Create: `frontend/src/components/CategoryTable.tsx`
- Create: `frontend/src/pages/DocumentDetail.tsx` (replaces any Task-9 stub)

**Interfaces:**
- Consumes: `apiFetch` (Task 9)
- Produces: `getDocument(id)`, `getSummaries(id)`, `getObligations(id)`, `getRisks(id)`, `getDeadlines(id)`, `getActionItems(id)` in `api/extractions.ts`.

- [ ] **Step 1: Write API functions**

```typescript
// frontend/src/api/extractions.ts
import { apiFetch } from "./client";

export interface DocumentDetailData {
  id: number;
  filename: string;
  status: string;
  error_message: string | null;
  sections: { id: number; heading: string; order_idx: number; page_ref: string | null }[];
}

export async function getDocument(id: number): Promise<DocumentDetailData> {
  return (await apiFetch(`/api/documents/${id}`)).json();
}

export async function getSummaries(id: number) {
  return (await apiFetch(`/api/summarize/${id}`)).json();
}

export async function getObligations(id: number) {
  return (await apiFetch(`/api/obligations/${id}`)).json();
}

export async function getRisks(id: number) {
  return (await apiFetch(`/api/risks/${id}`)).json();
}

export async function getDeadlines(id: number) {
  return (await apiFetch(`/api/deadlines/${id}`)).json();
}

export async function getActionItems(id: number) {
  return (await apiFetch(`/api/actions/${id}`)).json();
}
```

- [ ] **Step 2: Write shared category table**

```typescript
// frontend/src/components/CategoryTable.tsx
interface Row {
  id: number;
  text: string;
  section_id?: number;
  responsible_role?: string | null;
  priority?: string | null;
  severity?: string | null;
}

export default function CategoryTable({ rows, sections }: { rows: Row[]; sections: { id: number; heading: string }[] }) {
  const headingFor = (sectionId?: number) => sections.find((s) => s.id === sectionId)?.heading ?? "—";

  if (rows.length === 0) {
    return <p className="p-6 text-slate-500">Nothing extracted for this category yet.</p>;
  }

  return (
    <table className="w-full text-left text-sm">
      <thead className="border-b border-slate-200 text-slate-500">
        <tr>
          <th className="py-2">Text</th>
          <th className="py-2">Role</th>
          <th className="py-2">Priority / Severity</th>
          <th className="py-2">Source section</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.id} className="border-b border-slate-100">
            <td className="py-2 pr-4">{row.text}</td>
            <td className="py-2 pr-4">{row.responsible_role ?? "—"}</td>
            <td className="py-2 pr-4">{row.priority ?? row.severity ?? "—"}</td>
            <td className="py-2 text-brand-700">{headingFor(row.section_id)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

- [ ] **Step 3: Write DocumentDetail page**

```typescript
// frontend/src/pages/DocumentDetail.tsx
import { useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  getDocument, getSummaries, getObligations, getRisks, getDeadlines, getActionItems,
} from "../api/extractions";
import CategoryTable from "../components/CategoryTable";

const TABS = ["Summary", "Obligations", "Risks", "Deadlines", "Actions"] as const;

export default function DocumentDetail() {
  const { id } = useParams();
  const docId = Number(id);
  const [tab, setTab] = useState<(typeof TABS)[number]>("Summary");

  const { data: document } = useQuery({ queryKey: ["document", docId], queryFn: () => getDocument(docId) });
  const { data: summaries } = useQuery({ queryKey: ["summaries", docId], queryFn: () => getSummaries(docId), enabled: !!document });
  const { data: obligations } = useQuery({ queryKey: ["obligations", docId], queryFn: () => getObligations(docId), enabled: !!document });
  const { data: risks } = useQuery({ queryKey: ["risks", docId], queryFn: () => getRisks(docId), enabled: !!document });
  const { data: deadlines } = useQuery({ queryKey: ["deadlines", docId], queryFn: () => getDeadlines(docId), enabled: !!document });
  const { data: actions } = useQuery({ queryKey: ["actions", docId], queryFn: () => getActionItems(docId), enabled: !!document });

  if (!document) return <p className="text-slate-500">Loading...</p>;

  const sections = document.sections;

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">{document.filename}</h1>
      <p className="mt-2 rounded-md bg-amber-50 px-4 py-2 text-sm text-amber-800">
        AI-generated. Verify against the original document before acting on this information.
      </p>

      <div className="mt-6 flex gap-2 border-b border-slate-200">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium ${tab === t ? "border-b-2 border-brand-600 text-brand-700" : "text-slate-500"}`}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="mt-4 rounded-xl border border-slate-200 bg-white">
        {tab === "Summary" && (
          <div className="space-y-3 p-6">
            {(summaries ?? []).map((s: { id: number; text: string }) => (
              <p key={s.id} className="text-slate-700">{s.text}</p>
            ))}
            {summaries?.length === 0 && <p className="text-slate-500">No summary yet.</p>}
          </div>
        )}
        {tab === "Obligations" && <CategoryTable rows={obligations ?? []} sections={sections} />}
        {tab === "Risks" && <CategoryTable rows={risks ?? []} sections={sections} />}
        {tab === "Deadlines" && (
          <CategoryTable
            rows={(deadlines ?? []).map((d: { id: number; description: string; section_id: number; responsible_role: string | null }) => ({ id: d.id, text: d.description, section_id: d.section_id, responsible_role: d.responsible_role }))}
            sections={sections}
          />
        )}
        {tab === "Actions" && <CategoryTable rows={actions ?? []} sections={sections} />}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Manual verification**

Run: `make up`, upload a doc with multiple headings, wait for status `done`, open its detail page, click through all 5 tabs, confirm each row shows a source section and the disclaimer banner is visible.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/extractions.ts frontend/src/components/CategoryTable.tsx frontend/src/pages/DocumentDetail.tsx
git commit -m "Add document detail page with category tabs"
```

---

## Task 12: Eval harness

**Files:**
- Create: `backend/app/routers/eval.py`
- Modify: `backend/app/main.py`
- Create: `backend/scripts/eval.py`
- Create: `backend/ground_truth/sample_doc.json`
- Create: `backend/tests/test_eval.py`
- Create: `frontend/src/api/eval.ts`, `frontend/src/pages/EvalPage.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Produces: `backend/scripts/eval.py` CLI: `python scripts/eval.py <document_id> <ground_truth_path>` → prints P/R/F1 per category, writes an `EvalRun` row. `GET /api/documents/{id}/eval` → list of `EvalRun` rows for that document.

- [ ] **Step 1: Write ground truth fixture**

```json
// backend/ground_truth/sample_doc.json
{
  "obligations": ["Staff must report incidents within 24 hours"],
  "risks": ["Delayed incident reporting"],
  "deadlines": ["Report within 24 hours"],
  "action_items": ["File incident report"]
}
```

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/test_eval.py
def test_score_category_exact_match():
    from app.services.eval_scoring import score_category
    predicted = ["Staff must report incidents within 24 hours"]
    ground_truth = ["Staff must report incidents within 24 hours"]
    precision, recall, f1 = score_category(predicted, ground_truth)
    assert precision == 1.0
    assert recall == 1.0
    assert f1 == 1.0


def test_score_category_partial_match_uses_fuzzy_threshold():
    from app.services.eval_scoring import score_category
    predicted = ["Staff should report incidents inside 24 hrs", "Unrelated extracted line"]
    ground_truth = ["Staff must report incidents within 24 hours"]
    precision, recall, f1 = score_category(predicted, ground_truth)
    assert 0 < precision < 1
    assert recall == 1.0


def test_score_category_no_match():
    from app.services.eval_scoring import score_category
    precision, recall, f1 = score_category(["completely different"], ["Staff must report incidents"])
    assert precision == 0.0
    assert recall == 0.0
    assert f1 == 0.0
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_eval.py -v`
Expected: FAIL with "No module named 'app.services.eval_scoring'"

- [ ] **Step 4: Write scoring implementation**

```python
# backend/app/services/eval_scoring.py
from rapidfuzz import fuzz

MATCH_THRESHOLD = 75


def score_category(predicted: list[str], ground_truth: list[str]) -> tuple[float, float, float]:
    if not predicted and not ground_truth:
        return 1.0, 1.0, 1.0
    if not predicted or not ground_truth:
        return 0.0, 0.0, 0.0

    matched_predicted = set()
    matched_truth = set()
    for i, p in enumerate(predicted):
        for j, g in enumerate(ground_truth):
            if j in matched_truth:
                continue
            if fuzz.token_sort_ratio(p, g) >= MATCH_THRESHOLD:
                matched_predicted.add(i)
                matched_truth.add(j)
                break

    precision = len(matched_predicted) / len(predicted)
    recall = len(matched_truth) / len(ground_truth)
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return precision, recall, f1
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_eval.py -v`
Expected: PASS

- [ ] **Step 6: Write the eval CLI script**

```python
# backend/scripts/eval.py
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app.models import ActionItem, Deadline, EvalRun, Obligation, Risk
from app.services.eval_scoring import score_category


def run_eval(document_id: int, ground_truth_path: str) -> None:
    ground_truth = json.loads(Path(ground_truth_path).read_text())
    db = SessionLocal()
    try:
        predicted = {
            "obligations": [o.text for o in db.query(Obligation).filter(Obligation.document_id == document_id)],
            "risks": [r.text for r in db.query(Risk).filter(Risk.document_id == document_id)],
            "deadlines": [d.description for d in db.query(Deadline).filter(Deadline.document_id == document_id)],
            "action_items": [a.text for a in db.query(ActionItem).filter(ActionItem.document_id == document_id)],
        }

        overall_p, overall_r, overall_f1 = [], [], []
        for category, gt_items in ground_truth.items():
            p, r, f1 = score_category(predicted.get(category, []), gt_items)
            overall_p.append(p)
            overall_r.append(r)
            overall_f1.append(f1)
            print(f"{category}: precision={p:.2f} recall={r:.2f} f1={f1:.2f}")

        avg_p = sum(overall_p) / len(overall_p)
        avg_r = sum(overall_r) / len(overall_r)
        avg_f1 = sum(overall_f1) / len(overall_f1)
        print(f"OVERALL: precision={avg_p:.2f} recall={avg_r:.2f} f1={avg_f1:.2f}")

        db.add(EvalRun(document_id=document_id, precision=avg_p, recall=avg_r, f1=avg_f1, ground_truth_ref=ground_truth_path))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/eval.py <document_id> <ground_truth_path>")
        sys.exit(1)
    run_eval(int(sys.argv[1]), sys.argv[2])
```

- [ ] **Step 7: Add the eval read endpoint**

```python
# backend/app/routers/eval.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import EvalRun, User
from app.routers.documents import _get_owned_document

router = APIRouter(prefix="/api/documents", tags=["eval"])


@router.get("/{doc_id}/eval")
def get_eval_runs(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _get_owned_document(doc_id, db, user)
    runs = db.query(EvalRun).filter(EvalRun.document_id == doc_id).order_by(EvalRun.created_at.desc()).all()
    return [{"id": r.id, "precision": r.precision, "recall": r.recall, "f1": r.f1, "ground_truth_ref": r.ground_truth_ref, "created_at": r.created_at} for r in runs]
```

Modify `backend/app/main.py`: add `eval` to the router import and `app.include_router(eval.router)`.

- [ ] **Step 8: Frontend eval page**

```typescript
// frontend/src/api/eval.ts
import { apiFetch } from "./client";

export interface EvalRun {
  id: number;
  precision: number;
  recall: number;
  f1: number;
  ground_truth_ref: string;
  created_at: string;
}

export async function getEvalRuns(docId: number): Promise<EvalRun[]> {
  return (await apiFetch(`/api/documents/${docId}/eval`)).json();
}
```

```typescript
// frontend/src/pages/EvalPage.tsx
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getEvalRuns } from "../api/eval";

export default function EvalPage() {
  const { id } = useParams();
  const docId = Number(id);
  const { data: runs } = useQuery({ queryKey: ["eval", docId], queryFn: () => getEvalRuns(docId) });

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">Evaluation results</h1>
      {(runs ?? []).length === 0 && <p className="mt-4 text-slate-500">No eval runs yet — run scripts/eval.py against this document.</p>}
      <div className="mt-4 space-y-3">
        {(runs ?? []).map((r) => (
          <div key={r.id} className="rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-sm text-slate-500">{r.ground_truth_ref}</p>
            <p className="mt-1 text-slate-900">
              Precision {r.precision.toFixed(2)} · Recall {r.recall.toFixed(2)} · F1 {r.f1.toFixed(2)}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

Modify `frontend/src/App.tsx` — add `<Route path="documents/:id/eval" element={<EvalPage />} />` under the `dashboard` layout route, and import `EvalPage`.

- [ ] **Step 9: Run full backend test suite**

Run: `cd backend && python -m pytest -v`
Expected: all PASS

- [ ] **Step 10: Commit**

```bash
git add backend/app/routers/eval.py backend/app/services/eval_scoring.py backend/app/main.py backend/scripts/eval.py backend/ground_truth backend/tests/test_eval.py frontend/src/api/eval.ts frontend/src/pages/EvalPage.tsx frontend/src/App.tsx
git commit -m "Add eval harness (scoring, CLI, endpoint, page)"
```

---

## Task 13 (stretch): Chatbot — RAG over document sections

**Files:**
- Create: `backend/app/routers/chat.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_chat.py`
- Create: `frontend/src/api/chat.ts`, `frontend/src/components/ChatPanel.tsx`
- Modify: `frontend/src/pages/DocumentDetail.tsx`

**Interfaces:**
- Produces: `POST /api/chat/{doc_id}` (body `{"question": str}`, auth required) → `{"answer": str}`. Retrieval = simple keyword/fuzzy match over the document's `sections.raw_text` (no vector DB — out of scope at this size), top-3 sections concatenated into the LLM prompt.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_chat.py
import io
from unittest.mock import MagicMock, patch


def _auth_header(client):
    client.post("/api/auth/register", json={"email": "a@b.com", "password": "secret123"})
    resp = client.post("/api/auth/login", data={"username": "a@b.com", "password": "secret123"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_chat_answers_from_document_sections(client, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    headers = _auth_header(client)
    upload_resp = client.post("/api/upload", headers=headers, files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")})
    doc_id = upload_resp.json()["id"]

    from app.database import SessionLocal
    from app.models import Section
    db = SessionLocal()
    db.add(Section(document_id=doc_id, heading="Reporting", order_idx=0, page_ref=None, raw_text="Staff must report incidents within 24 hours."))
    db.commit()
    db.close()

    fake_llm = MagicMock()
    fake_llm.invoke.return_value.content = "You must report incidents within 24 hours."

    with patch("app.routers.chat.get_llm", return_value=fake_llm):
        resp = client.post(f"/api/chat/{doc_id}", headers=headers, json={"question": "When must incidents be reported?"})

    assert resp.status_code == 200
    assert "24 hours" in resp.json()["answer"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_chat.py -v`
Expected: FAIL with 404 (route doesn't exist)

- [ ] **Step 3: Write implementation**

```python
# backend/app/routers/chat.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from rapidfuzz import fuzz
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Section, User
from app.routers.documents import _get_owned_document
from app.services.llm import get_llm

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    question: str


def _top_sections(question: str, sections: list[Section], k: int = 3) -> list[Section]:
    scored = sorted(sections, key=lambda s: fuzz.partial_ratio(question, s.raw_text), reverse=True)
    return scored[:k]


@router.post("/{doc_id}")
def chat(doc_id: int, payload: ChatRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    document = _get_owned_document(doc_id, db, user)
    top_sections = _top_sections(payload.question, document.sections)
    context = "\n\n".join(f"## {s.heading}\n{s.raw_text}" for s in top_sections)

    prompt = (
        "Answer the question using only the document excerpts below. "
        "If the answer isn't in the excerpts, say you don't know.\n\n"
        f"Excerpts:\n{context}\n\nQuestion: {payload.question}"
    )
    llm = get_llm()
    response = llm.invoke(prompt)
    return {"answer": response.content}
```

Modify `backend/app/main.py`: add `chat` to the router import and `app.include_router(chat.router)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_chat.py -v`
Expected: PASS

- [ ] **Step 5: Frontend chat panel**

```typescript
// frontend/src/api/chat.ts
import { apiFetch } from "./client";

export async function askQuestion(docId: number, question: string): Promise<string> {
  const resp = await apiFetch(`/api/chat/${docId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  const data = await resp.json();
  return data.answer as string;
}
```

```typescript
// frontend/src/components/ChatPanel.tsx
import { useState } from "react";
import { askQuestion } from "../api/chat";

export default function ChatPanel({ docId }: { docId: number }) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<{ role: "user" | "assistant"; text: string }[]>([]);
  const [loading, setLoading] = useState(false);

  async function handleAsk() {
    if (!question.trim()) return;
    const q = question;
    setMessages((m) => [...m, { role: "user", text: q }]);
    setQuestion("");
    setLoading(true);
    try {
      const answer = await askQuestion(docId, q);
      setMessages((m) => [...m, { role: "assistant", text: answer }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mt-6 rounded-xl border border-slate-200 bg-white p-4">
      <h2 className="text-lg font-semibold text-slate-900">Ask about this document</h2>
      <div className="mt-3 max-h-64 space-y-2 overflow-y-auto">
        {messages.map((m, i) => (
          <p key={i} className={m.role === "user" ? "text-slate-900" : "text-brand-700"}>
            <strong>{m.role === "user" ? "You: " : "AI: "}</strong>{m.text}
          </p>
        ))}
      </div>
      <div className="mt-3 flex gap-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAsk()}
          placeholder="Ask a question about this document..."
          className="flex-1 rounded-md border border-slate-300 px-3 py-2"
        />
        <button onClick={handleAsk} disabled={loading} className="rounded-md bg-brand-600 px-4 py-2 text-white disabled:opacity-50">
          {loading ? "Asking..." : "Ask"}
        </button>
      </div>
    </div>
  );
}
```

Modify `frontend/src/pages/DocumentDetail.tsx`: import `ChatPanel` and render `<ChatPanel docId={docId} />` below the tab content block.

- [ ] **Step 6: Manual verification**

Run: `make up`, open a processed document's detail page, ask a question referencing content from an uploaded section, confirm an answer streams back referencing that content.

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/chat.py backend/app/main.py backend/tests/test_chat.py frontend/src/api/chat.ts frontend/src/components/ChatPanel.tsx frontend/src/pages/DocumentDetail.tsx
git commit -m "Add RAG chatbot over document sections"
```

---

## Verification checklist (after all tasks)

- [ ] `cd backend && python -m pytest -v` — all tests pass
- [ ] `make up` — full stack starts clean
- [ ] Register → login → upload PDF → status progresses pending → processing → done
- [ ] Document detail shows summary + all 4 category tabs with source-section attribution
- [ ] Disclaimer banner visible on document detail
- [ ] `python backend/scripts/eval.py <doc_id> backend/ground_truth/sample_doc.json` prints P/R/F1 and appears on `/dashboard/documents/{id}/eval`
- [ ] Chat panel answers a question using uploaded document content
- [ ] Swapping `.env` `LLM_BASE_URL`/`LLM_API_KEY`/`LLM_MODEL` to OpenAI values requires no code change
