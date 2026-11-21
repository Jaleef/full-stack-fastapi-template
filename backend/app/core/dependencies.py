"""外部依赖连通性检查。"""

from __future__ import annotations

from pydantic import BaseModel
from sqlmodel import Session


class DepStatus(BaseModel):
    """单个外部依赖的状态。"""

    name: str
    ok: bool
    detail: str = ""


def check_postgres(session: Session) -> DepStatus:
    """检查数据库连通性。"""
    ...


def check_pgvector(session: Session) -> DepStatus:
    """检查 pgvector 扩展是否已安装。"""
    ...


def check_llm() -> DepStatus:
    """探测对话模型接口。"""
    ...


def check_embedding() -> DepStatus:
    """探测向量化接口及其维度。"""
    ...


def dependency_report(session: Session) -> list[DepStatus]:  # noqa: ARG001
    """返回全部外部依赖的状态列表。"""
    return []
