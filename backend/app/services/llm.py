"""对话模型与向量模型客户端。"""

from __future__ import annotations

from typing import Any

from app.core.config import Settings


class LLMError(Exception):
    """对话模型调用失败或响应无法解析。"""


class LLMClient:
    """基于 OpenAI 兼容接口的对话模型客户端。"""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: int = 60,
        max_retries: int = 3,
    ) -> None:
        """保存连接参数，延迟创建底层客户端。"""
        ...

    def chat_json(self, system: str, user: str) -> dict[str, Any]:
        """发送 JSON 模式请求并返回解析后的对象。"""
        ...

    @property
    def usage(self) -> dict[str, int]:
        """返回累计的 token 用量。"""
        ...


def build_client(settings: Settings) -> LLMClient:
    """根据配置创建对话模型客户端。"""
    ...


class EmbeddingError(Exception):
    """向量化请求失败，或返回维度与配置不一致。"""


class EmbeddingClient:
    """批量向量化客户端，带维度校验。"""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        dim: int,
        batch_size: int = 32,
    ) -> None:
        """保存连接参数与目标维度。"""
        ...

    def embed(self, texts: list[str]) -> list[list[float]]:
        """批量向量化，并返回 L2 归一化后的向量。"""
        ...

    @property
    def dim(self) -> int:
        """返回配置的向量维度。"""
        ...


def normalize(vector: list[float]) -> list[float]:
    """对向量做 L2 归一化。"""
    ...


def build_embedding_client(settings: Settings) -> EmbeddingClient:
    """根据配置创建向量化客户端。"""
    ...
