"""Application configuration via environment variables."""
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://orbiteus:orbiteus@localhost:5432/orbiteus"

    # Auth
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15      # PR 6 — was 60; tighter blast radius
    refresh_token_expire_days: int = 7         # PR 6 — was 30; aligns with rotation
    refresh_token_rotate_on_use: bool = True

    # Redis (cache, jti revocation, rate limit, pubsub backplane).
    redis_url: str = "redis://localhost:6379/0"

    # Rate limit defaults (per minute). Override in production via env.
    rate_limit_tenant_per_minute: int = 1000
    rate_limit_user_per_minute: int = 60
    rate_limit_ip_per_minute: int = 120
    rate_limit_anonymous_per_minute: int = 30

    # AI provider key encryption (Fernet) — used in PR 8.
    ai_secret_key: str = "change-me-with-fernet-key"

    # App
    app_name: str = "Orbiteus"
    environment: str = "development"
    debug: bool = True
    cors_origins: list[str] = ["http://localhost:3000"]
    allow_public_registration: bool = True
    bootstrap_admin_email: str = "admin@example.com"
    bootstrap_admin_password: str = "admin1234"

    @model_validator(mode="after")
    def validate_production_safety(self) -> "Settings":
        if self.environment.lower() == "production":
            if self.secret_key in {"change-me-in-production", "change-me-in-production-use-openssl-rand-hex-32"}:
                raise ValueError("SECRET_KEY must be changed in production")
            if self.debug:
                raise ValueError("DEBUG must be false in production")
            if self.bootstrap_admin_password == "admin1234":
                raise ValueError("Set BOOTSTRAP_ADMIN_PASSWORD in production")
        return self


settings = Settings()
