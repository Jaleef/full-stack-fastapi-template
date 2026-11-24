"""外部依赖连通性检查。

检查项：
- PostgreSQL：能否连接、服务端版本
- pgvector：扩展是否存在、版本
- chat：模型接口是否可调用
- embedding：向量化接口是否可用、维度是否与配置一致

所有检查都返回状态对象而不是抛异常，方便接口一次性展示全部结果。
"""

from __future__ import annotations

from typing import Any

import httpx
from pydantic import BaseModel
from sqlalchemy import text
from sqlmodel import Session

from app.core.config import settings


class DepStatus(BaseModel):
    """单个外部依赖的状态。"""

    name: str
    ok: bool
    detail: str = ""


def _short_error(exc: Exception) -> str:
    """把异常压缩成适合展示的一行短文本。"""
    message = str(exc).replace("\n", " ").strip()
    return message[:200] or exc.__class__.__name__


def _post_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: int,
) -> dict[str, Any]:
    """发送一次 JSON 请求并返回解析后的对象。"""
    response = httpx.post(url, json=payload, headers=headers, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError("响应不是 JSON 对象")
    return data


def check_postgres(session: Session) -> DepStatus:
    """检查数据库连通性并返回服务端版本。"""
    try:
        row = session.execute(text("SELECT version()")).first()
        raw = str(row[0]) if row and row[0] else ""
        parts = raw.split(" ")
        version = parts[1] if len(parts) > 1 else raw
        detail = f"server={version}" if version else "connected"
        return DepStatus(name="postgres", ok=True, detail=detail)
    except Exception as exc:  # noqa: BLE001  —— 探针需要吞掉所有连接/权限错误
        return DepStatus(name="postgres", ok=False, detail=_short_error(exc))


def check_pgvector(session: Session) -> DepStatus:
    """检查 pgvector 扩展是否已安装，并返回版本。"""
    try:
        row = session.execute(
            text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        ).first()
        if not row:
            return DepStatus(
                name="pgvector",
                ok=False,
                detail="扩展 vector 未安装（需要外部库启用 pgvector）",
            )
        return DepStatus(name="pgvector", ok=True, detail=f"version={row[0]}")
    except Exception as exc:  # noqa: BLE001
        return DepStatus(name="pgvector", ok=False, detail=_short_error(exc))


def check_llm() -> DepStatus:
    """探测对话模型接口是否可用。"""
    if not settings.LLM_API_KEY:
        return DepStatus(
            name="llm",
            ok=False,
            detail=f"LLM_API_KEY 未配置（model={settings.LLM_MODEL}）",
        )

    url = f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions"
    payload = {
        "model": settings.LLM_MODEL,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 1,
        "temperature": 0,
    }
    headers = {"Authorization": f"Bearer {settings.LLM_API_KEY}"}
    try:
        data = _post_json(url, payload, headers, settings.LLM_TIMEOUT)
        if not data.get("choices"):
            return DepStatus(name="llm", ok=False, detail="响应缺少 choices")
        return DepStatus(name="llm", ok=True, detail=f"model={settings.LLM_MODEL}")
    except httpx.HTTPStatusError as exc:
        body = exc.response.text.replace("\n", " ")[:160]
        return DepStatus(
            name="llm",
            ok=False,
            detail=f"HTTP {exc.response.status_code}: {body}",
        )
    except Exception as exc:  # noqa: BLE001
        return DepStatus(name="llm", ok=False, detail=_short_error(exc))


def check_embedding() -> DepStatus:
    """探测向量化接口，并校验返回维度与配置一致。"""
    if not settings.EMBEDDING_BASE_URL:
        return DepStatus(
            name="embedding",
            ok=False,
            detail=f"EMBEDDING_BASE_URL 未配置（model={settings.EMBEDDING_MODEL}）",
        )

    url = settings.EMBEDDING_BASE_URL
    api_key = settings.EMBEDDING_API_KEY if settings.EMBEDDING_API_KEY else None
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    payload = {"model": settings.EMBEDDING_MODEL, "input": ["ping"]}
    try:
        data = _post_json(url, payload, headers, settings.LLM_TIMEOUT)
        items = data.get("data") or []
        vector = items[0].get("embedding") if items else None
        if not isinstance(vector, list) or not vector:
            return DepStatus(name="embedding", ok=False, detail="响应缺少 embedding")
        if len(vector) != settings.EMBEDDING_DIM:
            return DepStatus(
                name="embedding",
                ok=False,
                detail=(
                    f"维度 {len(vector)} ≠ EMBEDDING_DIM {settings.EMBEDDING_DIM}"
                ),
            )
        return DepStatus(
            name="embedding",
            ok=True,
            detail=f"model={settings.EMBEDDING_MODEL} dim={len(vector)}",
        )
    except httpx.HTTPStatusError as exc:
        body = exc.response.text.replace("\n", " ")[:160]
        return DepStatus(
            name="embedding",
            ok=False,
            detail=f"HTTP {exc.response.status_code}: {body}",
        )
    except Exception as exc:  # noqa: BLE001
        return DepStatus(name="embedding", ok=False, detail=_short_error(exc))


def dependency_report(session: Session) -> list[DepStatus]:
    """依次检查全部外部依赖，返回四项状态。

    PostgreSQL 不可用时跳过 pgvector 检查，避免重复等待连接超时。
    """
    postgres = check_postgres(session)
    if postgres.ok:
        pgvector = check_pgvector(session)
    else:
        pgvector = DepStatus(
            name="pgvector",
            ok=False,
            detail="PostgreSQL 不可用，跳过检查",
        )
    return [postgres, pgvector, check_llm(), check_embedding()]
