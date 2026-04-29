"""
services/api/config.py
=======================
Pydantic Settings — single source of truth for all configuration.
All values are loaded from environment variables / .env file.
"""

from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "sqlite:///./data/app.db"

    # ── Auth ──────────────────────────────────────────────────────────────────
    jwt_secret_key: str = "changeme"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # ── ML Model ──────────────────────────────────────────────────────────────
    model_path: str = "green_budget_optimizer/outputs/aqi_forest_model.pkl"
    enable_shap: bool = False
    enable_bayesian_opt: bool = False

    # ── Data ──────────────────────────────────────────────────────────────────
    data_source: str = "synthetic"
    openaq_api_key: str = ""

    # ── App ───────────────────────────────────────────────────────────────────
    app_env: str = "development"       # development | production
    log_level: str = "INFO"
    random_seed: int = 42

    # ── Service Ports ─────────────────────────────────────────────────────────
    auth_service_port: int = 8001
    data_service_port: int = 8002
    model_service_port: int = 8003
    optimization_service_port: int = 8004
    api_port: int = 8000
    frontend_port: int = 3000

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def model_path_resolved(self) -> Path:
        return Path(self.model_path)


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance — call this everywhere instead of Settings()."""
    return Settings()
