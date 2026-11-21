"""后端测试夹具。"""

from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlmodel import Session, create_engine

from app.core.config import settings
from app.main import app


@pytest.fixture(scope="session")
def test_engine() -> Engine:
    """创建指向独立测试库的引擎。"""
    url = os.environ.get("TEST_DATABASE_URL") or str(settings.DATABASE_URL)
    return create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )


@pytest.fixture()
def session(test_engine: Engine) -> Generator[Session]:
    """提供一个测试数据库会话。"""
    with Session(test_engine) as session:
        yield session


@pytest.fixture()
def client() -> Generator[TestClient]:
    """提供一个 FastAPI 测试客户端。"""
    with TestClient(app) as test_client:
        yield test_client
