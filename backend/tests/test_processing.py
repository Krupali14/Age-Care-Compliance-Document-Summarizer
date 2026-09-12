import io
from unittest.mock import MagicMock, patch

from app.database import Base
from app.models import Document, User, Section, Summary, Obligation, Risk, Deadline, ActionItem
from app.services.docling_parser import ParsedSection
from app.services.extraction import (
    ExtractedActionItem, ExtractedDeadline, ExtractedObligation, ExtractedRisk, RelevanceCheck,
    SectionExtraction,
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

    fake_sections = [ParsedSection(heading="Obligations", order_idx=0, page_ref=None, raw_text="Staff must report all incidents to the Commission within 24 hours.")]
    fake_extraction = SectionExtraction(
        summary="Staff must report incidents.",
        obligations=[ExtractedObligation(text="Report incidents", responsible_role="Staff", priority="high")],
        risks=[ExtractedRisk(text="Delayed reporting", severity="medium")],
        deadlines=[ExtractedDeadline(description="Report within 24h", due_date=None, responsible_role="Staff")],
        action_items=[ExtractedActionItem(text="File incident report", responsible_role="Staff", timeframe="24h", priority="high")],
    )

    with patch("app.services.processing.SessionLocal", return_value=db), \
         patch("app.services.processing.parse_document", return_value=fake_sections), \
         patch("app.services.processing.check_relevance", return_value=RelevanceCheck(is_relevant=True, reason="ok")), \
         patch("app.services.processing.extract_batch", return_value={0: fake_extraction}):
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


def test_process_document_survives_one_section_failing():
    """One bad batch must not cost the document the rest of its content.

    This test used to drive *every* call to failure and still assert "done" — which
    described the bug rather than the contract: a document nothing was read from was
    shown as Ready over six empty tabs. Total failure is covered separately, in
    test_a_document_that_extracts_nothing_is_failed_not_done.
    """
    from sqlalchemy import create_engine
    engine = create_engine("sqlite:///:memory:")
    db = _make_db(engine)

    user = User(email="a@b.com", hashed_password="h")
    db.add(user)
    db.flush()
    doc = Document(user_id=user.id, filename="doc.pdf", file_type="pdf", status="pending")
    db.add(doc)
    db.commit()

    fake_sections = [
        ParsedSection(heading="Good", order_idx=0, page_ref=None,
                      raw_text="A section with enough text in it to be extracted."),
        ParsedSection(heading="Bad", order_idx=1, page_ref=None,
                      raw_text="Another section with enough text in it to be extracted."),
    ]

    # The first section extracts; everything after it fails, retries included.
    calls = {"n": 0}

    def flaky(batch):
        calls["n"] += 1
        if calls["n"] == 1:
            return {batch[0][0]: SectionExtraction(
                summary="- something", obligations=[], risks=[], deadlines=[], action_items=[],
            )}
        raise RuntimeError("LLM error")

    with patch("app.services.processing.SessionLocal", return_value=db), \
         patch("app.services.processing.parse_document", return_value=fake_sections), \
         patch("app.services.processing.check_relevance", return_value=RelevanceCheck(is_relevant=True, reason="ok")), \
         patch("app.services.processing.extract_batch", side_effect=flaky):
        from app.services.processing import process_document
        process_document(doc.id, "/tmp/doc.pdf")

    db.refresh(doc)
    # Partial content is still content — the document stays usable.
    assert doc.status == "done"
    assert db.query(Section).filter_by(document_id=doc.id).count() == 2
    assert db.query(Summary).filter_by(document_id=doc.id).count() == 1


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
    # The parser's own wording names internal paths and library internals, so the
    # stored message is one a user can act on and the detail stays in the log.
    assert "cannot parse" not in doc.error_message
    assert "could not be read" in doc.error_message


def test_upload_to_read_endpoint_end_to_end(client, session_local, tmp_path, monkeypatch):
    """Upload -> (real, TestClient-synchronous) background processing -> read
    endpoint, all through the same in-memory DB the client uses. Proves the
    whole spine works together, not just each piece in isolation."""
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    headers = _auth_header(client)

    fake_sections = [ParsedSection(heading="Obligations", order_idx=0, page_ref=None, raw_text="Staff must report all incidents to the Commission within 24 hours.")]
    fake_extraction = SectionExtraction(
        summary="Staff must report incidents.",
        obligations=[ExtractedObligation(text="Report incidents", responsible_role="Staff", priority="high")],
        risks=[],
        deadlines=[],
        action_items=[],
    )

    with patch("app.services.processing.SessionLocal", session_local), \
         patch("app.services.processing.parse_document", return_value=fake_sections), \
         patch("app.services.processing.check_relevance", return_value=RelevanceCheck(is_relevant=True, reason="ok")), \
         patch("app.services.processing.extract_batch", return_value={0: fake_extraction}):
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


def test_process_document_marks_irrelevant_document_unsupported():
    """An out-of-scope upload gets one warning, not obligations/risks/deadlines."""
    from sqlalchemy import create_engine
    engine = create_engine("sqlite:///:memory:")
    db = _make_db(engine)

    user = User(email="a@b.com", hashed_password="h")
    db.add(user)
    db.flush()
    doc = Document(user_id=user.id, filename="receipt.pdf", file_type="pdf", status="pending")
    db.add(doc)
    db.commit()

    fake_sections = [ParsedSection(heading="Total", order_idx=0, page_ref=None, raw_text="Amount due $42.00 including GST. Paid by Visa card ending 4412.")]
    irrelevant = RelevanceCheck(is_relevant=False, reason="This looks like a receipt.")

    with patch("app.services.processing.SessionLocal", return_value=db), \
         patch("app.services.processing.parse_document", return_value=fake_sections), \
         patch("app.services.processing.check_relevance", return_value=irrelevant), \
         patch("app.services.processing.extract_batch") as extract:
        from app.services.processing import process_document
        process_document(doc.id, "/tmp/receipt.pdf")

    db.refresh(doc)
    assert doc.status == "unsupported"
    assert doc.error_message == "This looks like a receipt."
    extract.assert_not_called()
    assert db.query(Obligation).filter_by(document_id=doc.id).count() == 0
    assert db.query(Risk).filter_by(document_id=doc.id).count() == 0
    assert db.query(Deadline).filter_by(document_id=doc.id).count() == 0
    assert db.query(Summary).filter_by(document_id=doc.id).count() == 0


def test_process_document_retries_sections_the_batch_call_missed():
    """Nothing may be silently dropped: a section missing from a batch result is
    re-extracted on its own before the document is marked done."""
    from sqlalchemy import create_engine
    engine = create_engine("sqlite:///:memory:")
    db = _make_db(engine)

    user = User(email="a@b.com", hashed_password="h")
    db.add(user)
    db.flush()
    doc = Document(user_id=user.id, filename="act.pdf", file_type="pdf", status="pending")
    db.add(doc)
    db.commit()

    fake_sections = [
        ParsedSection(heading=f"S{i}", order_idx=i, page_ref=None, raw_text=f"Section {i} carries enough substantive text to be extracted.")
        for i in range(3)
    ]
    made = SectionExtraction(
        summary="- covered",
        obligations=[ExtractedObligation(text="Do the thing", responsible_role="Staff")],
    )

    calls = []

    def fake_extract_batch(batch):
        indexes = [i for i, _ in batch]
        calls.append(indexes)
        # First call covers section 0 only; 1 and 2 go missing and must be retried.
        if calls == [indexes]:
            return {0: made}
        return {i: made for i in indexes}

    with patch("app.services.processing.SessionLocal", return_value=db), \
         patch("app.services.processing.parse_document", return_value=fake_sections), \
         patch("app.services.processing.check_relevance", return_value=RelevanceCheck(is_relevant=True, reason="ok")), \
         patch("app.services.processing.extract_batch", side_effect=fake_extract_batch):
        from app.services.processing import process_document
        process_document(doc.id, "/tmp/act.pdf")

    db.refresh(doc)
    assert doc.status == "done"
    # The two missed sections were retried, and only those two.
    assert [i for call in calls[1:] for i in call] == [1, 2]
    # Every section ended up with its extraction persisted.
    assert db.query(Obligation).filter_by(document_id=doc.id).count() == 3


def test_process_document_skips_table_of_contents_fragments():
    """Heading-only scraps ("ii Aged Care Act 2024") are stored as sections but never
    sent to the model — extracting them wastes calls and invites invented summaries."""
    from sqlalchemy import create_engine
    engine = create_engine("sqlite:///:memory:")
    db = _make_db(engine)

    user = User(email="a@b.com", hashed_password="h")
    db.add(user)
    db.flush()
    doc = Document(user_id=user.id, filename="act.pdf", file_type="pdf", status="pending")
    db.add(doc)
    db.commit()

    fake_sections = [
        ParsedSection(heading="Contents", order_idx=0, page_ref=None, raw_text="ii Aged Care Act 2024"),
        ParsedSection(heading="Division 1", order_idx=1, page_ref=None, raw_text="system 77"),
        ParsedSection(
            heading="Incident reporting", order_idx=2, page_ref=None,
            raw_text="The registered provider must notify the Commission of a reportable incident.",
        ),
    ]
    made = SectionExtraction(summary="- covered")
    sent = []

    def fake_extract_batch(batch):
        sent.extend(i for i, _ in batch)
        return {i: made for i, _ in batch}

    with patch("app.services.processing.SessionLocal", return_value=db), \
         patch("app.services.processing.parse_document", return_value=fake_sections), \
         patch("app.services.processing.check_relevance", return_value=RelevanceCheck(is_relevant=True, reason="ok")), \
         patch("app.services.processing.extract_batch", side_effect=fake_extract_batch):
        from app.services.processing import process_document
        process_document(doc.id, "/tmp/act.pdf")

    db.refresh(doc)
    assert doc.status == "done"
    # Only the section with real content was sent for extraction...
    assert sent == [2]
    # ...but every parsed section is still stored, so the document reads complete.
    assert db.query(Section).filter_by(document_id=doc.id).count() == 3


def test_a_document_that_extracts_nothing_is_failed_not_done(db_session, monkeypatch, tmp_path):
    """Observed on a real run: "75 of 75 extractable sections have no result", yet
    the document was marked done — a Ready badge over six empty tabs, with nothing
    to tell the user the AI service had been unreachable the whole time."""
    from unittest.mock import patch

    from app.models import Document, Summary, User
    from app.services.docling_parser import ParsedSection
    from app.services.extraction import RelevanceCheck

    user = User(email="nothing@b.com", hashed_password="x")
    db_session.add(user)
    db_session.flush()
    doc = Document(user_id=user.id, filename="d.pdf", file_type="pdf", status="pending")
    db_session.add(doc)
    db_session.commit()

    sections = [
        ParsedSection(heading=f"Section {i}", order_idx=i, page_ref=None,
                      raw_text="The provider must do the thing described in this clause.")
        for i in range(3)
    ]

    with (
        patch("app.services.processing.SessionLocal", return_value=db_session),
        patch("app.services.processing.parse_document", return_value=sections),
        patch("app.services.processing.check_relevance",
              return_value=RelevanceCheck(is_relevant=True, reason="ok")),
        # Every call fails, as it would with the provider down or the account
        # rate-limited for long enough to burn every retry.
        patch("app.services.processing.extract_batch", side_effect=RuntimeError("provider down")),
    ):
        from app.services.processing import process_document

        process_document(doc.id, str(tmp_path / "d.pdf"))

    db_session.refresh(doc)
    assert doc.status == "failed"
    assert "again" in doc.error_message
    # The sections were still stored, so the document is readable even though
    # nothing was extracted from it.
    assert len(doc.sections) == 3
    assert db_session.query(Summary).filter_by(document_id=doc.id).count() == 0
