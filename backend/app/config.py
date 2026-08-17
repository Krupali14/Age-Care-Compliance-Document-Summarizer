from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    model_config = {"env_file": ".env"}


settings = Settings()
