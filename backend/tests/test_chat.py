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
