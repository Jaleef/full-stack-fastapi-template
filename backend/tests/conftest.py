"""后端测试夹具。

约定：
- 测试只允许连接 TEST_DATABASE_URL 指向的独立库，绝不回退到业务库。
- 首次使用时对测试库执行 alembic upgrade head。
- 每个用例结束后清空业务表，保留 alembic_version。
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlmodel import Session, create_engine

from app.core.config import BACKEND_DIR, settings
from app.core.db import get_session
from app.main import app
from app.services.llm import (
    EmbeddingClient,
    LLMClient,
    build_client,
    build_embedding_client,
)

# 清表顺序无关紧要，CASCADE 会处理外键
APP_TABLES = (
    "analysis",
    "document",
    "parse_decision",
    "requirement_unit",
    "atomic_requirement",
    "atom_source",
    "design_element",
    "mapping",
    "finding",
    "llm_cache",
)

ALEMBIC_INI = BACKEND_DIR / "alembic.ini"
ALEMBIC_DIR = BACKEND_DIR / "app" / "alembic"


def _test_url() -> str:
    """返回测试库 DSN；未配置或与业务库相同时直接失败。"""
    url = str(settings.TEST_DATABASE_URL or "")
    if not url:
        pytest.fail("TEST_DATABASE_URL 未配置；请指向独立的测试库")
    if url == str(settings.DATABASE_URL):
        pytest.fail("TEST_DATABASE_URL 不能与 DATABASE_URL 相同")
    return url


def _ensure_vector_extension(url: str) -> None:
    """测试库是独立数据库，需要单独安装 pgvector 扩展。"""
    engine = create_engine(url, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    finally:
        engine.dispose()


def _run_migrations(url: str) -> None:
    """在测试库上执行 alembic upgrade head。"""
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(ALEMBIC_DIR))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")


def _truncate(engine: Engine) -> None:
    """清空业务表，保留 alembic_version。"""
    statement = text(f"TRUNCATE {', '.join(APP_TABLES)} RESTART IDENTITY CASCADE")
    with engine.begin() as conn:
        conn.execute(statement)


@pytest.fixture(scope="session")
def test_engine() -> Generator[Engine]:
    """创建测试库引擎，并保证迁移已执行、库是干净的。"""
    url = _test_url()
    _ensure_vector_extension(url)
    _run_migrations(url)
    engine = create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )
    _truncate(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def real_llm() -> LLMClient:
    """真实对话客户端；未配置密钥时跳过，不使用假客户端。"""
    if not settings.llm_enabled:
        pytest.skip("LLM_API_KEY 未配置")
    return build_client(settings)


@pytest.fixture(scope="session")
def real_embedder() -> EmbeddingClient:
    """真实向量客户端；未配置地址时跳过，不使用假 embedder。"""
    if not settings.embedding_enabled:
        pytest.skip("EMBEDDING_BASE_URL 未配置")
    return build_embedding_client(settings)


@pytest.fixture()
def session(test_engine: Engine) -> Generator[Session]:
    """提供一个测试会话，用例结束后清空业务表。"""
    with Session(test_engine) as session:
        yield session
    _truncate(test_engine)


@pytest.fixture()
def client(session: Session) -> Generator[TestClient]:
    """提供使用测试库的 FastAPI 客户端。"""
    app.dependency_overrides[get_session] = lambda: session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
