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


def test_upload_sanitizes_path_traversal_filename(client, tmp_path, monkeypatch):
    upload_dir = tmp_path / "uploads"
    monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))
    headers = _auth_header(client)
    resp = client.post(
        "/api/upload",
        headers=headers,
        files={"file": ("../../evil.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["filename"] == "evil.pdf"

    saved_files = list(upload_dir.iterdir())
    assert len(saved_files) == 1
    assert saved_files[0].resolve().parent == upload_dir.resolve()
    assert not (tmp_path / "evil.pdf").exists()


def test_upload_rejects_unsupported_type(client):
    headers = _auth_header(client)
    resp = client.post(
        "/api/upload",
        headers=headers,
        files={"file": ("doc.txt", io.BytesIO(b"plain text"), "text/plain")},
    )
    assert resp.status_code == 400
