"""原子需求与设计要素的裁决、校验、反向判定与聚合。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, Field

from app.domain import Candidate
from app.models import AtomMapping, DesignElement, Finding, RequirementUnit
from app.services.llm import LLMClient


class EvidenceModel(BaseModel):
    """判定所引用的双侧原文片段。"""

    atom: str = ""
    element: str = ""


class LinkVerdict(BaseModel):
    """原子与某个候选要素之间的一条判定。"""

    element: str
    relation: str
    confidence: float
    cross_domain: bool = False
    evidence: EvidenceModel = Field(default_factory=EvidenceModel)
    rationale: str = ""


class AtomVerdict(BaseModel):
    """一个原子需求的全部判定结果。"""

    atom: str
    links: list[LinkVerdict] = Field(default_factory=list)
    unmatched: bool = False
    conflicts: list[dict[str, Any]] = Field(default_factory=list)


def judge_atom(
    client: LLMClient,
    atom_text: str,
    context: str,
    candidates: list[Candidate],
) -> AtomVerdict:
    """让模型针对候选要素裁决一个原子需求。"""
    ...


def validate_refs(
    verdict: AtomVerdict,
    candidates: list[Candidate],
) -> AtomVerdict:
    """丢弃引用了候选集之外要素的判定。"""
    ...


def validate_evidence(
    verdict: AtomVerdict,
    atom_text: str,
    element_texts: dict[str, str],
) -> AtomVerdict:
    """校验证据是否为两侧原文的逐字片段。"""
    ...


def apply_cross_domain_guard(
    verdict: AtomVerdict,
    atom_domain: str,
    element_domains: dict[str, str],
) -> AtomVerdict:
    """把没有理由的跨域 satisfy 降级为 partial。"""
    ...


def apply_numeric_override(
    verdict: AtomVerdict,
    atom_text: str,
    element_text: str,
) -> AtomVerdict:
    """指标更差或缺失时用规则覆盖模型结论。"""
    ...


def apply_protocol_override(
    verdict: AtomVerdict,
    atom_text: str,
    element_text: str,
) -> AtomVerdict:
    """协议不兼容时用规则覆盖模型结论。"""
    ...


def apply_placeholder_override(
    verdict: AtomVerdict,
    atom_text: str,
    element_text: str,
) -> AtomVerdict:
    """设计只写占位符时压低判定等级。"""
    ...


def finalize_links(verdict: AtomVerdict) -> AtomVerdict:
    """去重并限制单原子最多三条边。"""
    ...


class ReverseVerdict(BaseModel):
    """一个无入边设计要素的反向判定结果。"""

    element_key: str
    verdict: str
    atom_ref: str | None = None
    relation: str | None = None
    evidence: dict[str, str] = Field(default_factory=dict)


def judge_orphan_element(
    client: LLMClient,
    element: DesignElement,
    units: list[RequirementUnit],
) -> ReverseVerdict:
    """判断无入边要素是否有需求依据或属于公共能力。"""
    ...


class Coverage(BaseModel):
    """概览页展示的覆盖率指标。"""

    atom_count: int = 0
    covered_atoms: int = 0
    atom_coverage: float = 0.0
    element_count: int = 0
    supported_elements: int = 0
    element_support: float = 0.0


def compute_coverage(
    atoms: Sequence[Any],
    elements: Sequence[Any],
    links: Sequence[Any],
) -> Coverage:
    """计算原子覆盖率与要素支持率。"""
    ...


def collect_findings(
    analysis_id: Any,
    atoms: Sequence[Any],
    elements: Sequence[Any],
    links: Sequence[Any],
) -> list[Finding]:
    """根据判定结果生成语义类问题。"""
    ...


def pending_reviews(links: Sequence[AtomMapping]) -> list[AtomMapping]:
    """返回需要人工复核的映射。"""
    ...
