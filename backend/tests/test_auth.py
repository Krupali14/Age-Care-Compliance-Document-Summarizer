def test_register_then_login(client):
    resp = client.post("/api/auth/register", json={"email": "a@b.com", "password": "secret123"})
    assert resp.status_code == 201

    resp = client.post("/api/auth/login", data={"username": "a@b.com", "password": "secret123"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password_rejected(client):
    client.post("/api/auth/register", json={"email": "a@b.com", "password": "secret123"})
    resp = client.post("/api/auth/login", data={"username": "a@b.com", "password": "wrong"})
    assert resp.status_code == 401


def test_register_rejects_weak_and_oversized_passwords(client):
    """Empty passwords were accepted, and bcrypt silently ignores everything past 72
    bytes — a long passphrase would appear to work while only its head mattered."""
    assert client.post("/api/auth/register", json={"email": "a@b.com", "password": ""}).status_code == 422
    assert client.post("/api/auth/register", json={"email": "a@b.com", "password": "short"}).status_code == 422
    assert client.post(
        "/api/auth/register", json={"email": "a@b.com", "password": "a" * 73}
    ).status_code == 422
    assert client.post(
        "/api/auth/register", json={"email": "a@b.com", "password": "a" * 72}
    ).status_code == 201


def test_register_rejects_malformed_email(client):
    assert client.post("/api/auth/register", json={"email": "notanemail", "password": "secret123"}).status_code == 422
    assert client.post("/api/auth/register", json={"email": "a@b", "password": "secret123"}).status_code == 422


def test_email_is_case_insensitive_end_to_end(client):
    """Registration lowercases the address, so sign-in has to as well or the account
    becomes unreachable from its own capitalised spelling."""
    assert client.post(
        "/api/auth/register", json={"email": "Mixed.Case@Example.com", "password": "secret123"}
    ).status_code == 201
    resp = client.post(
        "/api/auth/login", data={"username": "MIXED.case@example.COM", "password": "secret123"}
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]
