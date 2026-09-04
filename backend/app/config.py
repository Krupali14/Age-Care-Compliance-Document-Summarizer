from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    # A working session, not an hour: the session ends when this expires, so a short
    # value is what makes the app feel like it logs you out while you are using it.
    jwt_expire_minutes: int = 480

    model_config = {"env_file": ".env"}


settings = Settings()
