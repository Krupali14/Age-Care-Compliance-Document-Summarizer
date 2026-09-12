"""Regression cover for documents stranded by a restart.

Extraction runs in a FastAPI background task, so it lives and dies with the
process. A restart mid-extraction left the row on "processing" forever — the
dashboard polled it indefinitely and nothing would ever pick it up again. Ten
documents were found stranded that way after one deploy-sized restart.
"""

from app.main import INTERRUPTED_MESSAGE, _release_interrupted_documents
from app.models import Document, User


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
