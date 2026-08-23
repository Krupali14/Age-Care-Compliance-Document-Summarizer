import io
from unittest.mock import MagicMock, patch

from app.database import Base
from app.models import Document, User, Section, Summary, Obligation, Risk, Deadline, ActionItem
from app.services.docling_parser import ParsedSection
from app.services.extraction import (
    ExtractedActionItem, ExtractedDeadline, ExtractedObligation, ExtractedRisk, SectionExtraction,
)


def _auth_header(client):
    client.post("/api/auth/register", json={"email": "a@b.com", "password": "secret123"})
    resp = client.post("/api/auth/login", data={"username": "a@b.com", "password": "secret123"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


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


def test_upload_to_read_endpoint_end_to_end(client, session_local, tmp_path, monkeypatch):
    """Upload -> (real, TestClient-synchronous) background processing -> read
    endpoint, all through the same in-memory DB the client uses. Proves the
    whole spine works together, not just each piece in isolation."""
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    headers = _auth_header(client)

    fake_sections = [ParsedSection(heading="Obligations", order_idx=0, page_ref=None, raw_text="Staff must report incidents.")]
    fake_extraction = SectionExtraction(
        summary="Staff must report incidents.",
        obligations=[ExtractedObligation(text="Report incidents", responsible_role="Staff", priority="high")],
        risks=[],
        deadlines=[],
        action_items=[],
    )

    with patch("app.services.processing.SessionLocal", session_local), \
         patch("app.services.processing.parse_document", return_value=fake_sections), \
         patch("app.services.processing.extract_section", return_value=fake_extraction):
        upload_resp = client.post(
            "/api/upload", headers=headers,
            files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
        )
        doc_id = upload_resp.json()["id"]

    resp = client.get(f"/api/obligations/{doc_id}", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["text"] == "Report incidents"
    assert body[0]["responsible_role"] == "Staff"

    doc_resp = client.get(f"/api/documents/{doc_id}", headers=headers)
    assert doc_resp.json()["status"] == "done"
