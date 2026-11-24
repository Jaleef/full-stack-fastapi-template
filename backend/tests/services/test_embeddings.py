"""向量客户端测试。"""

from __future__ import annotations

import pytest

import app.services.llm as llm_module
from app.core.config import settings
from app.services.llm import (
    EmbeddingClient,
    EmbeddingError,
    build_embedding_client,
    normalize,
)


class _FakeResponse:
    """模拟 httpx 响应。"""

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        """模拟成功状态码。"""

    def json(self) -> dict:
        """返回固定响应体。"""
        return self._payload


def _client_with(
    monkeypatch,
    *,
    dim: int = 2,
    embedding_dim: int = 2,
    batch_size: int = 2,
) -> tuple[EmbeddingClient, list[list[str]]]:
    """构造一个使用假 httpx.post 的向量客户端。"""
    calls: list[list[str]] = []

    def fake_post(_url: str, *, json: dict, **_kwargs):
        calls.append(list(json["input"]))
        data = [
            {
                "index": index,
                "embedding": [3.0, 4.0]
                if embedding_dim == 2
                else [1.0] * embedding_dim,
            }
            for index in range(len(json["input"]))
        ]
        return _FakeResponse({"data": data})

    monkeypatch.setattr(llm_module.httpx, "post", fake_post)
    client = EmbeddingClient(
        "https://example.test/v1/embeddings",
        "test-key",
        "test-model",
        dim=dim,
        batch_size=batch_size,
    )
    return client, calls


def test_normalize() -> None:
    """L2 归一化与零向量处理。"""
    assert normalize([3.0, 4.0]) == [0.6, 0.8]
    assert normalize([0.0, 0.0]) == [0.0, 0.0]


def test_embed_splits_batches(monkeypatch) -> None:
    """按 batch_size 分批请求，返回顺序与输入一致。"""
    client, calls = _client_with(monkeypatch, batch_size=2)

    vectors = client.embed(["a", "b", "c", "d", "e"])

    assert len(vectors) == 5
    assert [len(call) for call in calls] == [2, 2, 1]
    assert vectors[0] == [0.6, 0.8]


def test_embed_dimension_mismatch(monkeypatch) -> None:
    """返回维度与配置不一致时抛错。"""
    client, _calls = _client_with(monkeypatch, dim=3, embedding_dim=2)

    with pytest.raises(EmbeddingError, match="维度不符"):
        client.embed(["a"])


def test_embed_api_failure(monkeypatch) -> None:
    """向量化接口失败时包装成 EmbeddingError。"""
    def fake_post(*_args, **_kwargs):
        raise RuntimeError("embedding service down")

    monkeypatch.setattr(llm_module.httpx, "post", fake_post)
    client = EmbeddingClient(
        "https://example.test/v1/embeddings",
        "test-key",
        "test-model",
        dim=2,
    )

    with pytest.raises(EmbeddingError, match="向量化请求失败"):
        client.embed(["a"])


def test_embed_empty_input(monkeypatch) -> None:
    """空输入不发起请求。"""
    client, calls = _client_with(monkeypatch)

    assert client.embed([]) == []
    assert calls == []


def test_build_requires_base_url(monkeypatch) -> None:
    """未配置地址时给出明确错误。"""
    monkeypatch.setattr(settings, "EMBEDDING_BASE_URL", "")
    with pytest.raises(EmbeddingError, match="EMBEDDING_BASE_URL"):
        build_embedding_client(settings)


def test_build_without_key(monkeypatch) -> None:
    """本地向量服务可能不需要密钥，未配置时不报错。"""
    captured: dict = {}

    class _Recorder:
        def __init__(self, **kwargs) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(llm_module, "EmbeddingClient", _Recorder)
    monkeypatch.setattr(settings, "EMBEDDING_BASE_URL", "https://example.test/v1/embeddings")
    monkeypatch.setattr(settings, "EMBEDDING_API_KEY", "")

    build_embedding_client(settings)

    assert captured["api_key"] is None


def test_uses_configured_url_exactly(monkeypatch) -> None:
    """配置的 URL 原样使用，不追加任何路径。"""
    captured: dict[str, str] = {}

    def fake_post(url: str, **_kwargs):
        captured["url"] = url
        return _FakeResponse({"data": [{"index": 0, "embedding": [1.0, 0.0]}]})

    monkeypatch.setattr(llm_module.httpx, "post", fake_post)
    client = EmbeddingClient(
        "https://example.test/v1/embeddings",
        "test-key",
        "test-model",
        dim=2,
    )

    client.embed(["a"])

    assert captured["url"] == "https://example.test/v1/embeddings"
