"""对话客户端的单元测试。"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import app.services.llm as llm_module
from app.core.config import settings
from app.services.llm import LLMClient, LLMError, build_client


class _FakeCompletions:
    """模拟 chat.completions.create。"""

    def __init__(self, content: str | None, has_choices: bool = True) -> None:
        self.content = content
        self.has_choices = has_choices

    def create(self, **_kwargs):
        """返回固定响应。"""
        usage = SimpleNamespace(
            prompt_tokens=3,
            completion_tokens=4,
            total_tokens=7,
        )
        choices = (
            [SimpleNamespace(message=SimpleNamespace(content=self.content))]
            if self.has_choices
            else []
        )
        return SimpleNamespace(choices=choices, usage=usage)


class _FakeChat:
    """模拟 client.chat。"""

    def __init__(self, completions: _FakeCompletions) -> None:
        self.completions = completions


class _FakeClient:
    """模拟 OpenAI 客户端。"""

    def __init__(self, content: str | None, has_choices: bool = True) -> None:
        self.chat = _FakeChat(_FakeCompletions(content, has_choices))


def _client_with(monkeypatch, content: str | None, has_choices: bool = True) -> LLMClient:
    """构造一个使用假 SDK 客户端的 LLMClient，避免真实网络与 SSL 初始化。"""
    monkeypatch.setattr(
        llm_module,
        "OpenAI",
        lambda **_kwargs: _FakeClient(content, has_choices),
    )
    return LLMClient("https://example.test", "test-key", "test-model")


def test_build_client_requires_key(monkeypatch) -> None:
    """未配置密钥时给出明确错误。"""
    monkeypatch.setattr(settings, "LLM_API_KEY", "")
    with pytest.raises(LLMError, match="LLM_API_KEY"):
        build_client(settings)


def test_chat_json_parses_object(monkeypatch) -> None:
    """正常 JSON 响应应被解析为字典。"""
    client = _client_with(monkeypatch, '{"ok": true}')
    assert client.chat_json("system", "user") == {"ok": True}
    assert client.usage["total_tokens"] == 7


def test_chat_json_strips_code_fence(monkeypatch) -> None:
    """容忍 ```json 代码围栏。"""
    client = _client_with(monkeypatch, '```json\n{"ok": true}\n```')
    assert client.chat_json("system", "user") == {"ok": True}


def test_chat_json_invalid_json(monkeypatch) -> None:
    """非 JSON 响应应抛出可读错误。"""
    client = _client_with(monkeypatch, "不是 JSON")
    with pytest.raises(LLMError, match="合法 JSON"):
        client.chat_json("system", "user")


def test_chat_json_empty_choices(monkeypatch) -> None:
    """响应没有 choices 时应抛出错误。"""
    client = _client_with(monkeypatch, None, has_choices=False)
    with pytest.raises(LLMError, match="choices"):
        client.chat_json("system", "user")


def test_usage_accumulates(monkeypatch) -> None:
    """多次调用的 token 用量应累加。"""
    client = _client_with(monkeypatch, '{"ok": true}')
    client.chat_json("system", "user")
    client.chat_json("system", "user")
    assert client.usage == {
        "prompt_tokens": 6,
        "completion_tokens": 8,
        "total_tokens": 14,
    }
