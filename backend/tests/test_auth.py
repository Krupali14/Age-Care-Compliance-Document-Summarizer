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
