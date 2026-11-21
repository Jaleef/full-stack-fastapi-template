"""数据库读写封装。"""

from __future__ import annotations

import uuid
from typing import Any

from sqlmodel import Session

from app.models import (
    Analysis,
    AnalysisDocument,
    AtomicRequirement,
    AtomMapping,
    DesignElement,
    Finding,
    ParseDecision,
    RequirementUnit,
)


def create_analysis(
    session: Session,
    title: str,
    config: dict[str, Any],
) -> Analysis:
    """写入一条新的分析记录。"""
    ...


def update_status(
    session: Session,
    analysis_id: uuid.UUID,
    status: str,
    progress: int,
    stage: str | None = None,
) -> Analysis:
    """更新分析状态、进度和阶段。"""
    ...


def save_documents(
    session: Session,
    documents: list[AnalysisDocument],
) -> None:
    """保存上传文档的元数据。"""
    ...


def save_decisions(session: Session, decisions: list[ParseDecision]) -> None:
    """保存块级判定结果。"""
    ...


def save_units(session: Session, units: list[RequirementUnit]) -> None:
    """保存需求单元。"""
    ...


def save_atoms(session: Session, atoms: list[AtomicRequirement]) -> None:
    """保存原子需求及其来源。"""
    ...


def save_elements(session: Session, elements: list[DesignElement]) -> None:
    """保存设计要素。"""
    ...


def save_links(session: Session, links: list[AtomMapping]) -> None:
    """保存原子与要素的映射。"""
    ...


def save_findings(session: Session, findings: list[Finding]) -> None:
    """保存问题清单。"""
    ...


def load_context(session: Session, analysis_id: uuid.UUID) -> dict[str, Any]:
    """加载判定阶段所需的全部数据。"""
    ...


def make_cache_key(model: str, prompt_version: str, payload: Any) -> str:
    """根据模型、提示词版本和负载生成缓存键。"""
    ...


def get_cached(session: Session, key: str) -> dict[str, Any] | None:
    """读取缓存的模型响应。"""
    ...


def put_cached(
    session: Session,
    key: str,
    model: str,
    prompt_version: str,
    response: dict[str, Any],
) -> None:
    """写入模型响应缓存。"""
    ...
