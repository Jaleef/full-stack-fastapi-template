"""需求文档抽取：块判定、原子拆分与语义合并。"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

from app.domain import CandidateBlock
from app.models import AtomicRequirement
from app.services.llm import LLMClient


class Decision(BaseModel):
    """一个候选块的需求判定结果。"""

    index: int
    verdict: str
    kind: str | None = None
    reason: str | None = None
    confidence: float | None = None


def judge_blocks(
    client: LLMClient,
    blocks: list[CandidateBlock],
    batch_size: int = 12,
) -> list[Decision]:
    """批量判定候选块是否为真实需求。"""
    ...


def fill_missing(
    client: LLMClient,
    blocks: list[CandidateBlock],
    decisions: list[Decision],
) -> list[Decision]:
    """对未返回判定的块补问一次。"""
    ...


class AtomDraft(BaseModel):
    """模型拆分出的一条原子需求。"""

    text: str
    spans: list[str]
    kind: str
    note: str = ""


def split_atoms(
    client: LLMClient,
    unit_text: str,
    context: str,
) -> list[AtomDraft]:
    """把一个需求单元拆成原子断言。"""
    ...


def validate_spans(draft: AtomDraft, unit_text: str) -> list[str]:
    """只保留能在单元原文中逐字找到的片段。"""
    ...


def dedupe_atoms(drafts: list[AtomDraft]) -> list[AtomDraft]:
    """去掉同一单元内的重复原子。"""
    ...


@dataclass(slots=True)
class MergeCandidate:
    """可能表达同一断言的原子对。"""

    left: int
    right: int
    score: float


def find_merge_candidates(
    atoms: list[AtomicRequirement],
    k: int = 5,
) -> list[MergeCandidate]:
    """用 BM25F 与向量召回近似重复的原子对。"""
    ...


def confirm_equivalence(
    client: LLMClient,
    atoms: list[AtomicRequirement],
    pairs: list[MergeCandidate],
) -> list[bool]:
    """让模型确认每一对原子是否语义等价。"""
    ...


def merge_atoms(
    atoms: list[AtomicRequirement],
    pairs: list[MergeCandidate],
) -> list[AtomicRequirement]:
    """合并确认等价的原子，并保留全部来源单元。"""
    ...
