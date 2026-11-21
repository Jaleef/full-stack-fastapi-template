"""分析任务接口：上传、解析、运行、查询与导出。"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, File, Form, Response, UploadFile

from app.api.deps import SessionDep
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

router = APIRouter(prefix="/analyses", tags=["analyses"])


@router.post("", response_model=Analysis)
async def create_analysis(
    session: SessionDep,
    requirements: UploadFile = File(...),
    design: UploadFile = File(...),
    title: str = Form(""),
) -> Analysis:
    """上传两份文档，切块并返回解析统计。"""
    ...


@router.post("/sample", response_model=Analysis)
def create_sample_analysis(session: SessionDep) -> Analysis:
    """使用内置样例文档创建分析。"""
    ...


@router.get("", response_model=list[Analysis])
def list_analyses(
    session: SessionDep, skip: int = 0, limit: int = 50
) -> list[Analysis]:
    """按创建时间倒序列出分析记录。"""
    ...


@router.get("/{analysis_id}", response_model=Analysis)
def get_analysis(session: SessionDep, analysis_id: uuid.UUID) -> Analysis:
    """返回单次分析的进度与统计。"""
    ...


@router.get("/{analysis_id}/documents", response_model=list[AnalysisDocument])
def list_documents(
    session: SessionDep, analysis_id: uuid.UUID
) -> list[AnalysisDocument]:
    """返回该分析上传的文档信息。"""
    ...


@router.patch("/{analysis_id}/config", response_model=Analysis)
def update_analysis_config(
    session: SessionDep, analysis_id: uuid.UUID, config: dict[str, Any]
) -> Analysis:
    """更新抽取配置并重新执行结构解析。"""
    ...


@router.post("/{analysis_id}/run", response_model=Analysis)
def start_analysis(
    session: SessionDep,
    analysis_id: uuid.UUID,
    background_tasks: BackgroundTasks,
) -> Analysis:
    """在后台启动完整分析流水线。"""
    ...


@router.post("/{analysis_id}/rerun", response_model=Analysis)
def rerun_analysis(
    session: SessionDep,
    analysis_id: uuid.UUID,
    background_tasks: BackgroundTasks,
) -> Analysis:
    """复检一次分析并计算差异。"""
    ...


@router.delete("/{analysis_id}")
def delete_analysis(session: SessionDep, analysis_id: uuid.UUID) -> dict[str, str]:
    """删除分析记录及其存储文件。"""
    ...


@router.get("/{analysis_id}/parse-decisions", response_model=list[ParseDecision])
def list_parse_decisions(
    session: SessionDep, analysis_id: uuid.UUID, role: str | None = None
) -> list[ParseDecision]:
    """返回解析审计用的块级判定结果。"""
    ...


@router.get("/{analysis_id}/units", response_model=list[RequirementUnit])
def list_units(
    session: SessionDep, analysis_id: uuid.UUID, uncovered: bool = False
) -> list[RequirementUnit]:
    """返回需求单元。"""
    ...


@router.get("/{analysis_id}/atoms", response_model=list[AtomicRequirement])
def list_atoms(
    session: SessionDep, analysis_id: uuid.UUID, with_sources: bool = False
) -> list[AtomicRequirement]:
    """返回合并后的原子需求。"""
    ...


@router.get("/{analysis_id}/elements", response_model=list[DesignElement])
def list_elements(
    session: SessionDep,
    analysis_id: uuid.UUID,
    kind: str | None = None,
    domain: str | None = None,
) -> list[DesignElement]:
    """返回设计要素。"""
    ...


@router.get("/{analysis_id}/mappings", response_model=list[AtomMapping])
def list_mappings(
    session: SessionDep,
    analysis_id: uuid.UUID,
    relation: str | None = None,
    domain: str | None = None,
) -> list[AtomMapping]:
    """返回原子与要素的映射。"""
    ...


@router.get("/{analysis_id}/findings", response_model=list[Finding])
def list_findings(
    session: SessionDep,
    analysis_id: uuid.UUID,
    severity: str | None = None,
    dimension: str | None = None,
    status: str | None = None,
) -> list[Finding]:
    """返回问题清单，支持按严重度、维度和状态过滤。"""
    ...


@router.get("/{analysis_id}/export")
def export_analysis(
    session: SessionDep, analysis_id: uuid.UUID, format: str = "md"
) -> Response:
    """导出 Markdown 或 CSV 报告。"""
    ...
