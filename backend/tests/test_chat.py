import io
from unittest.mock import MagicMock, patch


def _auth_header(client, email="a@b.com"):
    client.post("/api/auth/register", json={"email": email, "password": "secret123"})
    resp = client.post("/api/auth/login", data={"username": email, "password": "secret123"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_chat_answers_from_document_sections(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    headers = _auth_header(client)
    upload_resp = client.post("/api/upload", headers=headers, files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")})
    doc_id = upload_resp.json()["id"]

    from app.models import Section
    db_session.add(Section(document_id=doc_id, heading="Reporting", order_idx=0, page_ref=None, raw_text="Staff must report incidents within 24 hours."))
    db_session.commit()

    fake_llm = MagicMock()
    fake_llm.invoke.return_value.content = "You must report incidents within 24 hours."

    with patch("app.routers.chat.get_llm", return_value=fake_llm):
        resp = client.post(f"/api/chat/{doc_id}", headers=headers, json={"question": "When must incidents be reported?"})

    assert resp.status_code == 200
    body = resp.json()
    assert "24 hours" in body["answer"]
    assert body["sources"] == [{"id": db_session.query(Section).filter_by(document_id=doc_id).first().id, "heading": "Reporting"}]

    # Prove retrieval actually ran: the prompt sent to the (mocked) LLM must
    # contain the section we seeded, not just the LLM's canned return value.
    prompt_sent = fake_llm.invoke.call_args[0][0]
    assert "Reporting" in prompt_sent
    assert "Staff must report incidents within 24 hours." in prompt_sent


def test_chat_not_owned_returns_404(client, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    headers_a = _auth_header(client, "a@b.com")
    headers_b = _auth_header(client, "b@b.com")

    upload_resp = client.post("/api/upload", headers=headers_a, files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")})
    doc_id = upload_resp.json()["id"]

    resp = client.post(f"/api/chat/{doc_id}", headers=headers_b, json={"question": "test?"})
    assert resp.status_code == 404


def _chat_auth(client, email="chat2@b.com"):
    client.post("/api/auth/register", json={"email": email, "password": "secret123"})
    r = client.post("/api/auth/login", data={"username": email, "password": "secret123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _doc_with_sections(db_session, email="chat2@b.com"):
    from app.models import Document, Section, User
    user = db_session.query(User).filter_by(email=email).one()
    doc = Document(user_id=user.id, filename="d.pdf", file_type="pdf", status="done")
    db_session.add(doc)
    db_session.flush()
    db_session.add_all([
        # A contents scrap: partial_ratio scored these top and starved the model of context.
        Section(document_id=doc.id, heading="Contents", order_idx=0, page_ref=None, raw_text="registrations"),
        Section(document_id=doc.id, heading="Contents", order_idx=1, page_ref=None, raw_text="reporting 12"),
        Section(
            document_id=doc.id, heading="Reporting", order_idx=2, page_ref=None,
            raw_text="The registered provider must report every reportable incident to the Commission within 24 hours of becoming aware of it.",
        ),
    ])
    db_session.commit()
    return doc


def test_chat_ranks_real_content_above_contents_scraps(client, db_session):
    """A 13-character contents fragment used to outrank the section that actually
    answered the question, leaving the model almost no context to work from."""
    from unittest.mock import MagicMock, patch
    headers = _chat_auth(client)
    doc = _doc_with_sections(db_session)

    fake = MagicMock()
    fake.invoke.return_value = MagicMock(content="Within 24 hours.")
    with patch("app.routers.chat.get_llm", return_value=fake):
        resp = client.post(f"/api/chat/{doc.id}", headers=headers,
                           json={"question": "What are the reporting obligations?"})

    assert resp.status_code == 200
    assert resp.json()["sources"][0]["heading"] == "Reporting"
    prompt = fake.invoke.call_args[0][0]
    assert "within 24 hours" in prompt.lower()


def test_chat_rejects_a_blank_question(client, db_session):
    headers = _chat_auth(client, "blank@b.com")
    doc = _doc_with_sections(db_session, "blank@b.com")
    assert client.post(f"/api/chat/{doc.id}", headers=headers, json={"question": "   "}).status_code == 422


def test_chat_reports_a_model_failure_as_unavailable_not_500(client, db_session):
    from unittest.mock import MagicMock, patch
    headers = _chat_auth(client, "down@b.com")
    doc = _doc_with_sections(db_session, "down@b.com")

    fake = MagicMock()
    fake.invoke.side_effect = RuntimeError("provider exploded")
    with patch("app.routers.chat.get_llm", return_value=fake):
        resp = client.post(f"/api/chat/{doc.id}", headers=headers, json={"question": "anything?"})

    assert resp.status_code == 503
    assert "provider exploded" not in resp.text


def test_chat_refuses_a_document_with_no_sections(client, db_session):
    from app.models import Document, User
    headers = _chat_auth(client, "nosec@b.com")
    user = db_session.query(User).filter_by(email="nosec@b.com").one()
    doc = Document(user_id=user.id, filename="d.pdf", file_type="pdf", status="failed")
    db_session.add(doc)
    db_session.commit()
    assert client.post(f"/api/chat/{doc.id}", headers=headers, json={"question": "hi?"}).status_code == 409
