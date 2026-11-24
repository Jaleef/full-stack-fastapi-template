"""对话模型与向量模型客户端。"""

from __future__ import annotations

import json
import threading
from typing import Any

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
