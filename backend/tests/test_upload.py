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


def _upload_auth(client, email="fname@b.com"):
    client.post("/api/auth/register", json={"email": email, "password": "secret123"})
    r = client.post("/api/auth/login", data={"username": email, "password": "secret123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_a_very_long_filename_is_trimmed_not_a_500(client, tmp_path, monkeypatch):
    """A 254-character name raised OSError deep inside the write — the filesystem
    caps one path component at 255 bytes and the stored name adds an "{id}_"
    prefix — and it escaped to the caller as a 500."""
    import io

    from app.routers.upload import MAX_FILENAME_BYTES

    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    headers = _upload_auth(client)

    resp = client.post(
        "/api/upload", headers=headers,
        files={"file": ("a" * 300 + ".pdf", io.BytesIO(b"%PDF-1.4 body"), "application/pdf")},
    )

    assert resp.status_code == 201
    stored = resp.json()["filename"]
    assert len(stored.encode("utf-8")) <= MAX_FILENAME_BYTES
    assert stored.endswith(".pdf")


def test_a_multibyte_filename_is_trimmed_by_bytes_not_characters(client, tmp_path, monkeypatch):
    """90 CJK characters is 270 bytes. Counting characters would have let it through
    and hit the same OSError, and slicing bytes naively would leave half a
    character behind."""
    import io

    from app.routers.upload import MAX_FILENAME_BYTES

    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    headers = _upload_auth(client, "cjk@b.com")

    resp = client.post(
        "/api/upload", headers=headers,
        files={"file": ("文" * 90 + ".pdf", io.BytesIO(b"%PDF-1.4 body"), "application/pdf")},
    )

    assert resp.status_code == 201
    stored = resp.json()["filename"]
    assert len(stored.encode("utf-8")) <= MAX_FILENAME_BYTES
    assert stored.endswith(".pdf")
    stored.encode("utf-8").decode("utf-8")  # no half-character survived


def test_a_write_failure_leaves_no_orphan_document(client, db_session, tmp_path, monkeypatch):
    """Only HTTPException used to trigger cleanup, so any other failure during the
    write left a Document row with no file behind it — a document on the dashboard
    that could never finish processing."""
    import io
    from unittest.mock import patch

    from app.models import Document

    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    headers = _upload_auth(client, "orphan@b.com")
    before = db_session.query(Document).count()

    with patch("pathlib.Path.open", side_effect=OSError("disk is full")):
        try:
            client.post(
                "/api/upload", headers=headers,
                files={"file": ("x.pdf", io.BytesIO(b"%PDF-1.4 body"), "application/pdf")},
            )
        except OSError:
            pass  # TestClient re-raises; what matters is the state it left behind

    assert db_session.query(Document).count() == before
