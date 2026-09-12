"""Regression cover for the input ceilings.

Each of these was unbounded: a 300-character email reached the database, and a
200KB chat question was forwarded to the model verbatim.
"""

from app.routers.chat import MAX_QUESTION_CHARS
from app.schemas import MAX_EMAIL_LENGTH


def _auth(client, email="limits@b.com"):
    client.post("/api/auth/register", json={"email": email, "password": "secret123"})
    r = client.post("/api/auth/login", data={"username": email, "password": "secret123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _doc(db_session, email="limits@b.com"):
    from app.models import Document, Section, User

    user = db_session.query(User).filter_by(email=email).one()
    doc = Document(user_id=user.id, filename="d.pdf", file_type="pdf", status="done")
    db_session.add(doc)
    db_session.flush()
    db_session.add(Section(
        document_id=doc.id, heading="Reporting", order_idx=0, page_ref=None,
        raw_text="The provider must report every reportable incident within 24 hours.",
    ))
    db_session.commit()
    return doc


def test_an_over_long_email_is_refused(client):
    long_email = "a" * (MAX_EMAIL_LENGTH + 1) + "@example.com"
    resp = client.post("/api/auth/register", json={"email": long_email, "password": "secret123"})
    assert resp.status_code == 422
    assert "at most" in resp.text


def test_an_email_at_the_limit_is_accepted(client):
    local = "a" * (MAX_EMAIL_LENGTH - len("@example.com"))
    resp = client.post("/api/auth/register", json={"email": f"{local}@example.com", "password": "secret123"})
    assert resp.status_code == 201


def test_an_over_long_question_is_refused_before_reaching_the_model(client, db_session):
    from unittest.mock import MagicMock, patch

    headers = _auth(client)
    doc = _doc(db_session)
    fake = MagicMock()

    with patch("app.routers.chat.get_llm", return_value=fake):
        resp = client.post(
            f"/api/chat/{doc.id}", headers=headers,
            json={"question": "a" * (MAX_QUESTION_CHARS + 1)},
        )

    assert resp.status_code == 422
    fake.invoke.assert_not_called()


def test_a_question_at_the_limit_is_accepted(client, db_session):
    from unittest.mock import MagicMock, patch

    headers = _auth(client, "atlimit@b.com")
    doc = _doc(db_session, "atlimit@b.com")
    fake = MagicMock()
    fake.invoke.return_value = MagicMock(content="ok")

    with patch("app.routers.chat.get_llm", return_value=fake):
        resp = client.post(
            f"/api/chat/{doc.id}", headers=headers,
            json={"question": "incident " * (MAX_QUESTION_CHARS // 9)},
        )

    assert resp.status_code == 200
