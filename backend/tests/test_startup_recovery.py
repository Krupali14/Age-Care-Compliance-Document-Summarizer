"""Regression cover for documents stranded by a restart.

Extraction runs in a FastAPI background task, so it lives and dies with the
process. A restart mid-extraction left the row on "processing" forever — the
dashboard polled it indefinitely and nothing would ever pick it up again. Ten
documents were found stranded that way after one deploy-sized restart.
"""

from app.main import (
    CHECK_INTERRUPTED_MESSAGE,
    INTERRUPTED_MESSAGE,
    _release_interrupted_checks,
    _release_interrupted_documents,
)
from app.models import ComplianceCheck, Document, User


def _doc(db, status, email="restart@b.com"):
    user = db.query(User).filter_by(email=email).first()
    if user is None:
        user = User(email=email, hashed_password="x")
        db.add(user)
        db.flush()
    doc = Document(user_id=user.id, filename="d.pdf", file_type="pdf", status=status)
    db.add(doc)
    db.commit()
    return doc


def _check(db, status, email="restart@b.com"):
    doc = _doc(db, "done", email)
    check = ComplianceCheck(document_id=doc.id, filename="case.pdf", file_type="pdf", status=status)
    db.add(check)
    db.commit()
    return check


def test_documents_left_mid_processing_are_failed_with_a_reason(db_session, monkeypatch, session_local):
    monkeypatch.setattr("app.main.SessionLocal", session_local)
    processing = _doc(db_session, "processing")
    pending = _doc(db_session, "pending")

    _release_interrupted_documents()

    for doc in (processing, pending):
        db_session.refresh(doc)
        assert doc.status == "failed"
        assert doc.error_message == INTERRUPTED_MESSAGE
        # The message has to tell the user what to do, not just that it broke.
        assert "again" in doc.error_message


def test_finished_documents_are_untouched(db_session, monkeypatch, session_local):
    """A restart must not undo work that completed before it."""
    monkeypatch.setattr("app.main.SessionLocal", session_local)
    done = _doc(db_session, "done", "keep@b.com")
    unsupported = _doc(db_session, "unsupported", "keep@b.com")
    already_failed = _doc(db_session, "failed", "keep@b.com")

    _release_interrupted_documents()

    for doc, expected in ((done, "done"), (unsupported, "unsupported"), (already_failed, "failed")):
        db_session.refresh(doc)
        assert doc.status == expected
        assert doc.error_message is None


def test_a_database_failure_at_startup_does_not_stop_the_app(monkeypatch):
    """Startup must survive cleanup failing — the API coming up matters more."""
    def boom():
        raise RuntimeError("database unreachable")

    monkeypatch.setattr("app.main.SessionLocal", boom)
    _release_interrupted_documents()  # must not raise


def test_checks_left_mid_processing_are_failed_with_a_reason(db_session, monkeypatch, session_local):
    """run_check is a background task too, so a restart mid-check strands it on
    "processing" the same way extraction strands a document — the panel polls a
    status that will never change."""
    monkeypatch.setattr("app.main.SessionLocal", session_local)
    processing = _check(db_session, "processing")
    pending = _check(db_session, "pending")

    _release_interrupted_checks()

    for check in (processing, pending):
        db_session.refresh(check)
        assert check.status == "failed"
        assert check.error_message == CHECK_INTERRUPTED_MESSAGE
        assert "again" in check.error_message


def test_finished_checks_are_untouched(db_session, monkeypatch, session_local):
    monkeypatch.setattr("app.main.SessionLocal", session_local)
    done = _check(db_session, "done", "keep2@b.com")
    already_failed = _check(db_session, "failed", "keep2@b.com")

    _release_interrupted_checks()

    for check, expected in ((done, "done"), (already_failed, "failed")):
        db_session.refresh(check)
        assert check.status == expected
        assert check.error_message is None


def test_a_database_failure_at_startup_does_not_stop_the_app_for_checks(monkeypatch):
    def boom():
        raise RuntimeError("database unreachable")

    monkeypatch.setattr("app.main.SessionLocal", boom)
    _release_interrupted_checks()  # must not raise
