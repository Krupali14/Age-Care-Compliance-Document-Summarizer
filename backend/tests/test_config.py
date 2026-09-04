import os

def test_settings_load_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/db")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.com/v1")
    monkeypatch.setenv("LLM_API_KEY", "key123")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("JWT_SECRET", "secret123")

    from app.config import Settings
    settings = Settings()

    assert settings.database_url == "postgresql://u:p@localhost/db"
    assert settings.llm_base_url == "https://example.com/v1"
    assert settings.llm_model == "test-model"
    assert settings.jwt_algorithm == "HS256"
    assert settings.jwt_expire_minutes == 480


def test_session_length_is_configurable(monkeypatch):
    """Deployments set their own session length; the default is only a default."""
    for name, value in [
        ("DATABASE_URL", "postgresql://u:p@localhost/db"), ("LLM_BASE_URL", "https://example.com/v1"),
        ("LLM_API_KEY", "key123"), ("LLM_MODEL", "test-model"), ("JWT_SECRET", "secret123"),
        ("JWT_EXPIRE_MINUTES", "120"),
    ]:
        monkeypatch.setenv(name, value)

    from app.config import Settings
    assert Settings().jwt_expire_minutes == 120
