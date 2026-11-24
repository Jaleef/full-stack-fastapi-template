"""核心依赖检查的单元测试。"""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.core import dependencies
from app.core.config import settings
from app.core.db import get_session
from app.main import app


def test_check_postgres_ok() -> None:
    """数据库可连接时返回版本号。"""
    session = MagicMock()
    session.execute.return_value.first.return_value = (
        "PostgreSQL 18.0 on x86_64-pc-linux-gnu",
    )
    status = dependencies.check_postgres(session)
    assert status.ok is True
    assert "18.0" in status.detail


def test_check_postgres_failure() -> None:
    """连接失败时返回错误而不是抛异常。"""
    session = MagicMock()
    session.execute.side_effect = RuntimeError("connection refused")
    status = dependencies.check_postgres(session)
    assert status.ok is False
    assert "connection refused" in status.detail


def test_check_pgvector_ok() -> None:
    """扩展存在时返回版本号。"""
    session = MagicMock()
    session.execute.return_value.first.return_value = ("0.8.0",)
    status = dependencies.check_pgvector(session)
    assert status.ok is True
    assert "0.8.0" in status.detail


def test_check_pgvector_missing() -> None:
    """扩展不存在时标记失败。"""
    session = MagicMock()
    session.execute.return_value.first.return_value = None
    status = dependencies.check_pgvector(session)
    assert status.ok is False
    assert "vector" in status.detail


def test_check_llm_requires_key(monkeypatch) -> None:
    """未配置密钥时不发起网络请求。"""
    monkeypatch.setattr(settings, "LLM_API_KEY", "")
    status = dependencies.check_llm()
    assert status.ok is False
    assert "LLM_API_KEY" in status.detail


def test_check_llm_ok(monkeypatch) -> None:
    """接口返回 choices 时判定可用。"""
    monkeypatch.setattr(settings, "LLM_API_KEY", "test-key")

    class FakeResponse:
        """模拟 httpx 响应。"""

        def raise_for_status(self) -> None:
            """模拟成功状态码。"""

        def json(self) -> dict:
            """模拟对话接口响应体。"""
            return {"choices": [{"message": {"content": "p"}}]}

    monkeypatch.setattr(
        dependencies.httpx, "post", lambda *args, **kwargs: FakeResponse()
    )
    status = dependencies.check_llm()
    assert status.ok is True
    assert settings.LLM_MODEL in status.detail


def test_check_embedding_requires_url(monkeypatch) -> None:
    """未配置地址时不发起网络请求。"""
    monkeypatch.setattr(settings, "EMBEDDING_BASE_URL", "")
    status = dependencies.check_embedding()
    assert status.ok is False
    assert "EMBEDDING_BASE_URL" in status.detail


def test_check_embedding_dimension_mismatch(monkeypatch) -> None:
    """返回维度与配置不一致时标记失败。"""
    monkeypatch.setattr(settings, "EMBEDDING_BASE_URL", "https://example.test/v1")
    monkeypatch.setattr(settings, "EMBEDDING_DIM", 8)

    class FakeResponse:
        """模拟 httpx 响应。"""

        def raise_for_status(self) -> None:
            """模拟成功状态码。"""

        def json(self) -> dict:
            """模拟向量化接口响应体。"""
            return {"data": [{"embedding": [0.1, 0.2]}]}

    monkeypatch.setattr(
        dependencies.httpx, "post", lambda *args, **kwargs: FakeResponse()
    )
    status = dependencies.check_embedding()
    assert status.ok is False
    assert "维度" in status.detail


def test_check_embedding_accepts_full_endpoint(monkeypatch) -> None:
    """配置里带 /embeddings 时不能拼出重复路径。"""
    monkeypatch.setattr(
        settings, "EMBEDDING_BASE_URL", "https://example.test/v1/embeddings"
    )
    monkeypatch.setattr(settings, "EMBEDDING_DIM", 2)
    captured: dict[str, str] = {}

    class FakeResponse:
        """模拟 httpx 响应。"""

        def raise_for_status(self) -> None:
            """模拟成功状态码。"""

        def json(self) -> dict:
            """模拟向量化接口响应体。"""
            return {"data": [{"embedding": [0.1, 0.2]}]}

    def fake_post(url: str, **_kwargs):
        captured["url"] = url
        return FakeResponse()

    monkeypatch.setattr(dependencies.httpx, "post", fake_post)
    status = dependencies.check_embedding()

    assert status.ok is True
    assert captured["url"] == "https://example.test/v1/embeddings"


def test_dependency_report_skips_pgvector(monkeypatch) -> None:
    """PostgreSQL 不可用时跳过扩展检查，仍返回四项。"""
    monkeypatch.setattr(
        dependencies,
        "check_postgres",
        lambda session: dependencies.DepStatus(
            name="postgres", ok=False, detail="down"
        ),
    )
    monkeypatch.setattr(
        dependencies,
        "check_llm",
        lambda: dependencies.DepStatus(name="llm", ok=False, detail="off"),
    )
    monkeypatch.setattr(
        dependencies,
        "check_embedding",
        lambda: dependencies.DepStatus(name="embedding", ok=False, detail="off"),
    )

    statuses = dependencies.dependency_report(MagicMock())

    assert [item.name for item in statuses] == [
        "postgres",
        "pgvector",
        "llm",
        "embedding",
    ]
    assert "跳过" in statuses[1].detail


def test_dependencies_endpoint(monkeypatch) -> None:
    """接口一次返回四项依赖状态。"""
    session = MagicMock()
    session.execute.side_effect = RuntimeError("database down")

    app.dependency_overrides[get_session] = lambda: session
    monkeypatch.setattr(settings, "LLM_API_KEY", "")
    monkeypatch.setattr(settings, "EMBEDDING_BASE_URL", "")
    try:
        response = TestClient(app).get("/api/v1/utils/dependencies/")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    names = {item["name"] for item in response.json()}
    assert names == {"postgres", "pgvector", "llm", "embedding"}
