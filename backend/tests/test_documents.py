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


def test_get_document_includes_section_raw_text(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    headers = _auth_header(client)

    upload_resp = client.post("/api/upload", headers=headers, files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")})
    doc_id = upload_resp.json()["id"]

    from app.models import Section

    db_session.add(Section(document_id=doc_id, heading="Obligations", order_idx=0, page_ref=None, raw_text="Staff must report incidents within 24 hours."))
    db_session.commit()

    resp = client.get(f"/api/documents/{doc_id}", headers=headers)
    section = resp.json()["sections"][0]
    assert section["heading"] == "Obligations"
    assert section["raw_text"] == "Staff must report incidents within 24 hours."


def test_category_endpoints_return_empty_lists_before_processing(client, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    headers = _auth_header(client)
    upload_resp = client.post("/api/upload", headers=headers, files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")})
    doc_id = upload_resp.json()["id"]

    for path in ["summarize", "obligations", "risks", "deadlines", "actions"]:
        resp = client.get(f"/api/{path}/{doc_id}", headers=headers)
        assert resp.status_code == 200


def test_category_endpoints_not_owned_returns_404(client, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    headers_a = _auth_header(client, "a@b.com")
    headers_b = _auth_header(client, "b@b.com")

    upload_resp = client.post("/api/upload", headers=headers_a, files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")})
    doc_id = upload_resp.json()["id"]

    for path in ["summarize", "obligations", "risks", "deadlines", "actions"]:
        resp = client.get(f"/api/{path}/{doc_id}", headers=headers_b)
        assert resp.status_code == 404, f"{path} did not return 404 for non-owning user"


def test_delete_document_removes_it_and_its_file(client, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    headers = _auth_header(client)

    upload_resp = client.post("/api/upload", headers=headers, files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")})
    doc_id = upload_resp.json()["id"]
    saved_files = list(tmp_path.iterdir())
    assert len(saved_files) == 1

    resp = client.delete(f"/api/documents/{doc_id}", headers=headers)
    assert resp.status_code == 204

    get_resp = client.get(f"/api/documents/{doc_id}", headers=headers)
    assert get_resp.status_code == 404

    list_resp = client.get("/api/documents", headers=headers)
    assert list_resp.json() == []

    assert list(tmp_path.iterdir()) == []


def test_delete_document_not_owned_returns_404(client, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    headers_a = _auth_header(client, "a@b.com")
    headers_b = _auth_header(client, "b@b.com")

    upload_resp = client.post("/api/upload", headers=headers_a, files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")})
    doc_id = upload_resp.json()["id"]

    resp = client.delete(f"/api/documents/{doc_id}", headers=headers_b)
    assert resp.status_code == 404

    get_resp = client.get(f"/api/documents/{doc_id}", headers=headers_a)
    assert get_resp.status_code == 200


def test_delete_document_requires_auth(client):
    resp = client.delete("/api/documents/1")
    assert resp.status_code == 401


def test_delete_document_removes_extracted_rows(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    headers = _auth_header(client)

    upload_resp = client.post("/api/upload", headers=headers, files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")})
    doc_id = upload_resp.json()["id"]

    from app.models import Section, Summary, Obligation, Risk, Deadline, ActionItem

    section = Section(document_id=doc_id, heading="H", order_idx=0, page_ref=None, raw_text="text")
    db_session.add(section)
    db_session.flush()
    db_session.add(Summary(document_id=doc_id, text="s", model_used="m"))
    db_session.add(Obligation(document_id=doc_id, section_id=section.id, text="o", responsible_role=None, priority=None))
    db_session.add(Risk(document_id=doc_id, section_id=section.id, text="r", severity="low"))
    db_session.add(Deadline(document_id=doc_id, section_id=section.id, description="d", due_date=None, responsible_role=None))
    db_session.add(ActionItem(document_id=doc_id, section_id=section.id, text="a", responsible_role=None, timeframe=None, priority=None, source_section="H"))
    db_session.commit()
    section_id = section.id

    resp = client.delete(f"/api/documents/{doc_id}", headers=headers)
    assert resp.status_code == 204

    db_session.expire_all()
    assert db_session.query(Section).filter_by(id=section_id).first() is None
    assert db_session.query(Summary).filter_by(document_id=doc_id).count() == 0
    assert db_session.query(Obligation).filter_by(document_id=doc_id).count() == 0
    assert db_session.query(Risk).filter_by(document_id=doc_id).count() == 0
    assert db_session.query(Deadline).filter_by(document_id=doc_id).count() == 0
    assert db_session.query(ActionItem).filter_by(document_id=doc_id).count() == 0


def test_deadlines_endpoint_hides_dates_that_have_already_passed(client, session_local):
    """Rows stored before the stale-date rule existed — and rows whose date has since
    gone by — must not be served to the UI as though they were still due."""
    from datetime import date, timedelta
    from app.models import Deadline, Document, Section, User

    headers = _auth_header(client)
    db = session_local()
    user = db.query(User).filter_by(email="a@b.com").one()
    doc = Document(user_id=user.id, filename="d.pdf", file_type="pdf", status="done")
    db.add(doc)
    db.flush()
    section = Section(document_id=doc.id, heading="S", order_idx=0, page_ref=None, raw_text="t")
    db.add(section)
    db.flush()

    future = (date.today() + timedelta(days=30)).isoformat()
    for description, due in [
        ("Past ISO date", "2024-01-15"),
        ("Past worded date", "August 2025"),
        ("Future date", future),
        ("Relative timeframe", "within 30 days of the incident"),
    ]:
        db.add(Deadline(document_id=doc.id, section_id=section.id, description=description, due_date=due))
    db.commit()

    rows = client.get(f"/api/deadlines/{doc.id}", headers=headers).json()
    served = {r["description"]: r["due_date"] for r in rows}

    assert served["Past ISO date"] is None
    assert served["Past worded date"] is None
    assert served["Future date"] == future
    assert served["Relative timeframe"] == "within 30 days of the incident"
