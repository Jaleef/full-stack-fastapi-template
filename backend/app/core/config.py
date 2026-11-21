"""应用配置。"""

from pathlib import Path

from pydantic import PostgresDsn, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    """运行时配置，来自 .env 与 .env.local。"""

    model_config = SettingsConfigDict(
        env_file=(
            str(PROJECT_DIR / ".env"),
        ),
        env_ignore_empty=True,
        extra="ignore",
    )

    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Consistency Analyzer"
    FRONTEND_HOST: str = "http://localhost:5173"

    DATABASE_URL: PostgresDsn
    TEST_DATABASE_URL: str | None = None

    LLM_BASE_URL: str = "https://api.deepseek.com"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "deepseek-flash"
    LLM_TIMEOUT: int = 60
    LLM_CONCURRENCY: int = 8
    LLM_MAX_CALLS: int = 800

    EMBEDDING_BASE_URL: str = ""
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_MODEL: str = "bge-m3"
    EMBEDDING_DIM: int = 1024

    CANDIDATE_K: int = 8

    DATA_DIR: Path = BACKEND_DIR / "data"
    SAMPLE_DIR: Path = BACKEND_DIR / "samples"

    SENTRY_DSN: str | None = None

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def _use_psycopg_driver(cls, value: str | PostgresDsn) -> str:
        """把 postgres:// 统一改成 psycopg 驱动。"""
        database_url = str(value)
        for scheme in ("postgres://", "postgresql://"):
            if database_url.startswith(scheme):
                return database_url.replace(scheme, "postgresql+psycopg://", 1)
        return database_url

    @computed_field  # type: ignore[prop-decorator]
    @property
    def llm_enabled(self) -> bool:
        """是否已配置对话模型。"""
        return bool(self.LLM_API_KEY)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def embedding_enabled(self) -> bool:
        """是否已配置向量化服务。"""
        return bool(self.EMBEDDING_BASE_URL)


settings = Settings()  # type: ignore[call-arg]
