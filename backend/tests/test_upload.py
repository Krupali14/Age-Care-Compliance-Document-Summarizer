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


def _auth(client, email="up@b.com"):
    client.post("/api/auth/register", json={"email": email, "password": "secret123"})
    r = client.post("/api/auth/login", data={"username": email, "password": "secret123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_upload_rejects_a_file_that_is_not_really_a_pdf(client, tmp_path, monkeypatch):
    """A renamed text file used to be accepted and only failed minutes later, deep in
    the parser, with a message no user could act on."""
    import io
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    resp = client.post(
        "/api/upload", headers=_auth(client, "sig@b.com"),
        files={"file": ("notreally.pdf", io.BytesIO(b"just some text"), "application/pdf")},
    )
    assert resp.status_code == 400
    assert "not a readable PDF" in resp.json()["detail"]


def test_upload_rejects_an_empty_file(client, tmp_path, monkeypatch):
    import io
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    resp = client.post(
        "/api/upload", headers=_auth(client, "empty2@b.com"),
        files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
    )
    assert resp.status_code == 400


def test_upload_rejects_a_file_over_the_size_limit(client, tmp_path, monkeypatch):
    """Unbounded uploads were read wholly into memory."""
    import io
    from app.routers import upload as upload_module
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(upload_module, "MAX_UPLOAD_BYTES", 1024)
    resp = client.post(
        "/api/upload", headers=_auth(client, "big@b.com"),
        files={"file": ("big.pdf", io.BytesIO(b"%PDF-1.4" + b"0" * 5000), "application/pdf")},
    )
    assert resp.status_code == 413


def test_rejected_upload_leaves_no_document_row_or_file(client, tmp_path, monkeypatch):
    """A rejected upload must not leave a half-created document behind."""
    import io
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    headers = _auth(client, "clean@b.com")
    client.post(
        "/api/upload", headers=headers,
        files={"file": ("bad.pdf", io.BytesIO(b"nope"), "application/pdf")},
    )
    assert client.get("/api/documents", headers=headers).json() == []
    assert list(tmp_path.glob("*.pdf")) == []
