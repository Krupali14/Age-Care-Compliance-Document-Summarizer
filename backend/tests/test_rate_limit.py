"""Regression cover for the auth rate limits.

Unlimited password guessing against a known address was possible before these:
twelve wrong passwords in a row all returned a clean 401.

The limits are pinned here rather than imported from `app.rate_limit`, because
those values come from the environment — and the end-to-end suite runs the stack
with them raised to 1000. A test that read them would then perform a thousand bcrypt
verifications and take a quarter of an hour to assert the same thing.
"""

import pytest

from app.rate_limit import clear, enforce

TEST_LOGIN_MAX = 3
TEST_REGISTER_MAX = 3


@pytest.fixture(autouse=True)
def _small_limits(monkeypatch):
    """Pin the router's limits to something small and deterministic."""
    monkeypatch.setattr("app.routers.auth.LOGIN_MAX_ATTEMPTS", TEST_LOGIN_MAX)
    monkeypatch.setattr("app.routers.auth.REGISTER_MAX_ATTEMPTS", TEST_REGISTER_MAX)
    monkeypatch.setattr("app.routers.auth.LOGIN_WINDOW_SECONDS", 900)
    monkeypatch.setattr("app.routers.auth.REGISTER_WINDOW_SECONDS", 3600)


def _register(client, email="rl@b.com", password="secret123"):
    return client.post("/api/auth/register", json={"email": email, "password": password})


def _login(client, email="rl@b.com", password="wrong"):
    return client.post("/api/auth/login", data={"username": email, "password": password})


def test_login_locks_out_after_the_attempt_limit(client):
    _register(client)
    for _ in range(TEST_LOGIN_MAX):
        assert _login(client).status_code == 401

    blocked = _login(client)
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers
    # The lockout must not hand back a hint about whether the account exists.
    assert "password" not in blocked.json()["detail"].lower()


def test_the_lockout_also_blocks_the_correct_password(client):
    """Otherwise an attacker learns they found it from the response changing."""
    _register(client)
    for _ in range(TEST_LOGIN_MAX):
        _login(client)

    assert _login(client, password="secret123").status_code == 429


def test_registration_is_capped_per_address(client):
    for i in range(TEST_REGISTER_MAX):
        assert _register(client, f"flood{i}@b.com").status_code == 201
    assert _register(client, "flood-over@b.com").status_code == 429


def test_a_different_account_is_unaffected_by_another_s_lockout(client):
    """The per-address counter must not lock out the whole application."""
    _register(client, "victim@b.com")
    _register(client, "bystander@b.com")
    for _ in range(TEST_LOGIN_MAX):
        _login(client, "victim@b.com")

    ok = _login(client, "bystander@b.com", password="secret123")
    assert ok.status_code == 200


def test_the_window_is_per_key_and_clears():
    clear()
    for _ in range(3):
        enforce("k", 3, 60)
    with pytest.raises(Exception):
        enforce("k", 3, 60)
    enforce("other-key", 3, 60)  # a different key has its own budget
    clear()
    enforce("k", 3, 60)  # cleared
