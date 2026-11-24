"""LLM 缓存读写测试。"""

from __future__ import annotations

from sqlmodel import Session

from app.crud import get_cached, make_cache_key, put_cached


def test_make_cache_key_is_stable_and_sensitive() -> None:
    """缓存键对键顺序不敏感，但对模型/版本/负载敏感。"""
    first = make_cache_key("model", "v1", {"a": 1, "b": 2})
    second = make_cache_key("model", "v1", {"b": 2, "a": 1})

    assert first == second
    assert first != make_cache_key("model", "v2", {"a": 1, "b": 2})
    assert first != make_cache_key("other", "v1", {"a": 1, "b": 2})
    assert first != make_cache_key("model", "v1", {"a": 1, "b": 3})


def test_cache_roundtrip(session: Session) -> None:
    """写入后应能按 key 读回同一份响应。"""
    key = make_cache_key("model", "v1", {"question": "x"})
    assert get_cached(session, key) is None

    put_cached(session, key, "model", "v1", {"answer": 42})

    assert get_cached(session, key) == {"answer": 42}


def test_cache_keeps_first_response(session: Session) -> None:
    """相同 key 重复写入时保留首次结果。"""
    key = make_cache_key("model", "v1", {"question": "x"})
    put_cached(session, key, "model", "v1", {"answer": 1})
    put_cached(session, key, "model", "v1", {"answer": 2})

    assert get_cached(session, key) == {"answer": 1}


def test_cached_call_skips_llm(session: Session) -> None:
    """第二次调用应直接命中缓存，不再调用模型。"""

    class _FakeClient:
        """记录调用次数的假客户端。"""

        def __init__(self) -> None:
            self.calls = 0

        def chat_json(self, system: str, user: str) -> dict:
            """返回固定答案并计数。"""
            self.calls += 1
            return {"ok": True, "system": system, "user": user}

    client = _FakeClient()

    def answer() -> dict:
        key = make_cache_key("model", "v1", {"q": "x"})
        cached = get_cached(session, key)
        if cached is not None:
            return cached
        response = client.chat_json("system", "user")
        put_cached(session, key, "model", "v1", response)
        return response

    assert answer() == {"ok": True, "system": "system", "user": "user"}
    assert answer() == {"ok": True, "system": "system", "user": "user"}
    assert client.calls == 1
