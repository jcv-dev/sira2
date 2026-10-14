from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SIRA_",
        extra="ignore",
    )

    base_url: str = "https://sira1.univalle.edu.co/sra"
    username: str = ""
    password: str = ""
    cache_ttl_seconds: int = 300
    timeout_seconds: float = 30.0
    api_token: str = ""
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    user_agent: str = "sira-api/0.1 (personal read-only client; https://github.com/)"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
