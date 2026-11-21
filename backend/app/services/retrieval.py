"""候选召回：BM25F、pgvector 相似度与 RRF 融合。"""

from __future__ import annotations

import uuid
from typing import Any

from sqlmodel import Session

from app.domain import Candidate
from app.models import AtomicRequirement


class BM25FieldIndex:
    """对设计要素按字段建立的 BM25 索引。"""

    def __init__(self, documents: list[dict[str, Any]]) -> None:
        """保存字段化文档并构建索引。"""
        ...

    def search(self, query: str, k: int = 10) -> list[tuple[int, float]]:
        """返回得分最高的 k 个文档下标及分数。"""
        ...


def rrf_fuse(rankings: list[list[int]], k: int = 60) -> list[tuple[int, float]]:
    """用倒数排名融合多路召回结果。"""
    ...


def ensure_heads(
    fused: list[tuple[int, float]],
    bm25: list[int],
    vector: list[int],
    k: int,
) -> list[int]:
    """保证两路召回的头部结果一定入选。"""
    ...


def diversify(
    candidates: list[Candidate],
    max_per_kind: int = 3,
    k: int = 8,
) -> list[Candidate]:
    """限制同一类型候选数量，避免候选单一化。"""
    ...


def vector_candidates(
    session: Session,
    analysis_id: uuid.UUID,
    embedding: list[float],
    k: int = 10,
) -> list[tuple[uuid.UUID, float]]:
    """用 pgvector 查询最近的设计要素。"""
    ...


class CandidateRetriever:
    """为一个原子需求召回设计要素候选。"""

    def __init__(self, session: Session, index: BM25FieldIndex) -> None:
        """保存数据库会话与关键词索引。"""
        ...

    def for_atom(
        self,
        analysis_id: uuid.UUID,
        atom: AtomicRequirement,
        k: int = 8,
    ) -> list[Candidate]:
        """返回融合、去重并做过多样性裁剪的候选。"""
        ...
