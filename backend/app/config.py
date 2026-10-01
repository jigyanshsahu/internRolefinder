from functools import lru_cache
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://internrolefinder:change-me@db:5432/internrolefinder"
    redis_url: str = "redis://redis:6379/0"
    frontend_origin: str = "http://localhost:3000"
    public_ats_company_catalog_url: str = "https://raw.githubusercontent.com/ConorsCode/open-jobs-data/main/companies.json"
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-2.5-flash"
    startup_discovery_limit: int = 40
    startup_discovery_interval_hours: int = 168
    crawl_interval_minutes: int = 360
    verify_interval_minutes: int = 180
    verification_max_age_hours: int = 24
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
