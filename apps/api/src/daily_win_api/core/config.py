from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_API_ROOT = Path(__file__).resolve().parents[3]
_DEMO_APP_ENVS = frozenset({"local", "development", "dev", "test"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_API_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "local"
    database_url: str = (
        "postgresql+psycopg://daily_win:daily_win_local@127.0.0.1:5432/daily_win"
    )

    @property
    def demo_routes_enabled(self) -> bool:
        """Demo routes are development-only and are not production authorization."""
        return self.app_env.strip().lower() in _DEMO_APP_ENVS


@lru_cache
def get_settings() -> Settings:
    return Settings()
