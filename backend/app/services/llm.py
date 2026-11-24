"""对话模型与向量模型客户端。"""

from __future__ import annotations

import json
import math
import threading
from typing import Any

import httpx
from openai import OpenAI

from app.core.config import Settings


class LLMError(Exception):
    """对话模型调用失败，或返回内容无法解析。"""


def _parse_json_object(content: str) -> dict[str, Any]:
    """解析模型返回的 JSON 对象，容忍 ```json 代码围栏。"""
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMError(f"模型返回不是合法 JSON：{content[:200]}") from exc

    if not isinstance(data, dict):
        raise LLMError(f"模型返回的不是 JSON 对象：{content[:200]}")
    return data


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
        """保存连接参数并创建底层 SDK 客户端。"""
        self.model = model
        self._client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )
        self._usage: dict[str, int] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
        # 流水线可能并发调用同一个客户端，用量累加需要加锁
        self._lock = threading.Lock()

    def chat_json(self, system: str, user: str) -> dict[str, Any]:
        """发送 JSON 模式请求并返回解析后的对象。"""
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0,
                response_format={"type": "json_object"},
            )
        except Exception as exc:  # noqa: BLE001 —— 统一包装成可读错误
            raise LLMError(f"对话请求失败（model={self.model}）：{exc}") from exc

        if not response.choices:
            raise LLMError(f"对话响应没有 choices（model={self.model}）")

        content = response.choices[0].message.content or ""
        if not content.strip():
            raise LLMError(f"对话响应内容为空（model={self.model}）")

        self._accumulate_usage(response.usage)
        return _parse_json_object(content)

    def _accumulate_usage(self, usage: Any) -> None:
        """累加本次调用的 token 用量。"""
        if usage is None:
            return
        with self._lock:
            self._usage["prompt_tokens"] += int(
                getattr(usage, "prompt_tokens", 0) or 0
            )
            self._usage["completion_tokens"] += int(
                getattr(usage, "completion_tokens", 0) or 0
            )
            self._usage["total_tokens"] += int(
                getattr(usage, "total_tokens", 0) or 0
            )

    @property
    def usage(self) -> dict[str, int]:
        """返回累计的 token 用量副本。"""
        with self._lock:
            return dict(self._usage)


def build_client(settings: Settings) -> LLMClient:
    """根据配置创建对话模型客户端。"""
    if not settings.LLM_API_KEY:
        raise LLMError("LLM_API_KEY 未配置")
    return LLMClient(
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
        model=settings.LLM_MODEL,
        timeout=settings.LLM_TIMEOUT,
    )


class EmbeddingError(Exception):
    """向量化请求失败，或返回维度与配置不一致。"""


class EmbeddingClient:
    """批量向量化客户端，带维度校验与 L2 归一化。"""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        dim: int,
        batch_size: int = 32,
        timeout: int = 60,
    ) -> None:
        """保存连接参数、目标维度与批大小。"""
        self.model = model
        self._dim = dim
        self._batch_size = batch_size
        self._base_url = base_url
        self._api_key = api_key
        self._timeout = timeout

    def embed(self, texts: list[str]) -> list[list[float]]:
        """批量向量化，返回 L2 归一化后的向量。"""
        if not texts:
            return []

        headers = (
            {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        )
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = texts[start : start + self._batch_size]
            try:
                response = httpx.post(
                    self._base_url,
                    json={"model": self.model, "input": batch},
                    headers=headers,
                    timeout=self._timeout,
                )
                response.raise_for_status()
                payload = response.json()
            except Exception as exc:  # noqa: BLE001 —— 统一包装成可读错误
                batch_no = start // self._batch_size + 1
                raise EmbeddingError(
                    f"向量化请求失败（model={self.model}，batch={batch_no}）：{exc}"
                ) from exc

            data = list(payload.get("data") or [])
            if len(data) != len(batch):
                raise EmbeddingError(
                    f"向量化返回数量不符：期望 {len(batch)}，实际 {len(data)}"
                )
            if data and all("index" in item for item in data):
                data.sort(key=lambda item: item["index"])

            for item in data:
                vector = [float(value) for value in item.get("embedding", [])]
                if len(vector) != self._dim:
                    raise EmbeddingError(
                        f"向量维度不符：期望 {self._dim}，实际 {len(vector)}"
                        f"（model={self.model}）"
                    )
                vectors.append(normalize(vector))

        return vectors

    @property
    def dim(self) -> int:
        """返回配置的向量维度。"""
        return self._dim


def normalize(vector: list[float]) -> list[float]:
    """对向量做 L2 归一化；零向量返回全零。"""
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return [0.0 for _ in vector]
    return [value / norm for value in vector]


def build_embedding_client(settings: Settings) -> EmbeddingClient:
    """根据配置创建向量化客户端。"""
    if not settings.EMBEDDING_BASE_URL:
        raise EmbeddingError("EMBEDDING_BASE_URL 未配置")

    # 仅在配置了 API Key 时才传给 SDK，避免在本地开发时触发 SSL 初始化
    api_key = settings.EMBEDDING_API_KEY if settings.EMBEDDING_API_KEY else None

    return EmbeddingClient(
        base_url=settings.EMBEDDING_BASE_URL,
        api_key=api_key,
        model=settings.EMBEDDING_MODEL,
        dim=settings.EMBEDDING_DIM,
        timeout=settings.LLM_TIMEOUT,
    )
