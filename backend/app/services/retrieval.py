"""候选召回：BM25F、pgvector 相似度与 RRF 融合。"""

from __future__ import annotations

import logging
import math
import re
import uuid
from collections import Counter
from typing import Any

import jieba
from sqlalchemy import select, text
from sqlmodel import Session

from app.domain import Candidate
from app.models import AtomicRequirement, DesignElement

jieba.setLogLevel(logging.WARNING)

TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+")
DEFAULT_FIELD_WEIGHTS: dict[str, float] = {
    "name": 3.0,
    "caption": 2.0,
    "description": 1.0,
    "fields": 1.0,
}


def tokenize(text: str) -> list[str]:
    """用 jieba 分词，并过滤空白与纯标点 token。"""
    if not text:
        return []
    tokens: list[str] = []
    for raw in jieba.lcut(text.lower()):
        token = raw.strip()
        if token and TOKEN_RE.fullmatch(token):
            tokens.append(token)
    return tokens


def _field_text(value: Any) -> str:
    """把字段值拍平成可分词文本。"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return " ".join(_field_text(item) for item in value)
    if isinstance(value, dict):
        return " ".join(f"{key} {_field_text(item)}" for key, item in value.items())
    return str(value)


class BM25FieldIndex:
    """对设计要素按字段建立的 BM25F 索引。"""

    def __init__(
        self,
        documents: list[dict[str, Any]],
        field_weights: dict[str, float] | None = None,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        """保存字段化文档并构建字段词频、长度与文档频率。"""
        self.documents = list(documents)
        self.field_weights = dict(field_weights or DEFAULT_FIELD_WEIGHTS)
        self.k1 = k1
        self.b = b
        self._doc_count = len(self.documents)

        self._field_tfs: dict[str, list[Counter[str]]] = {
            field: [] for field in self.field_weights
        }
        self._field_lengths: list[dict[str, int]] = []
        self._doc_freq: Counter[str] = Counter()
        self._avg_lengths: dict[str, float] = {}

        for document in self.documents:
            lengths: dict[str, int] = {}
            for field in self.field_weights:
                tokens = tokenize(_field_text(document.get(field)))
                lengths[field] = len(tokens)
                self._field_tfs[field].append(Counter(tokens))
            self._field_lengths.append(lengths)

        for field in self.field_weights:
            total = sum(lengths[field] for lengths in self._field_lengths)
            self._avg_lengths[field] = (
                total / self._doc_count if self._doc_count else 0.0
            )

        for index in range(self._doc_count):
            terms: set[str] = set()
            for field in self.field_weights:
                terms.update(self._field_tfs[field][index])
            self._doc_freq.update(terms)

    def search(self, query: str, k: int = 10) -> list[tuple[int, float]]:
        """返回得分最高的 k 个文档下标及分数。"""
        if k <= 0 or not self.documents:
            return []

        terms = set(tokenize(query))
        if not terms:
            return []

        scores = [0.0] * self._doc_count
        for term in terms:
            document_freq = self._doc_freq.get(term, 0)
            if document_freq == 0:
                continue
            idf = math.log(
                1
                + (self._doc_count - document_freq + 0.5)
                / (document_freq + 0.5)
            )

            for index in range(self._doc_count):
                weighted_tf = 0.0
                for field, weight in self.field_weights.items():
                    term_freq = self._field_tfs[field][index].get(term, 0)
                    if term_freq == 0:
                        continue
                    avg_length = self._avg_lengths[field] or 1.0
                    length = self._field_lengths[index][field]
                    norm = 1 - self.b + self.b * length / avg_length
                    weighted_tf += weight * term_freq / norm

                if weighted_tf:
                    scores[index] += (
                        idf
                        * weighted_tf
                        * (self.k1 + 1)
                        / (self.k1 + weighted_tf)
                    )

        ranked = [
            (index, score) for index, score in enumerate(scores) if score > 0
        ]
        ranked.sort(key=lambda item: (-item[1], item[0]))
        return ranked[:k]


def rrf_fuse(rankings: list[list[int]], k: int = 60) -> list[tuple[int, float]]:
    """用倒数排名融合多路召回结果。

    每一路按“越靠前越重要”给分：score += 1 / (k + rank)。
    同一个文档在同一路里重复出现只算第一次。
    """
    if k <= 0:
        k = 1

    scores: dict[int, float] = {}
    for ranking in rankings:
        seen: set[int] = set()
        for rank, index in enumerate(ranking, start=1):
            if index in seen:
                continue
            seen.add(index)
            scores[index] = scores.get(index, 0.0) + 1.0 / (k + rank)

    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))


def ensure_heads(
    fused: list[tuple[int, float]],
    bm25: list[int],
    vector: list[int],
    k: int,
    explicit: list[int] | None = None,
) -> list[int]:
    """保证显式 ID 与两路召回的 top-1 一定入选。"""
    if k <= 0:
        return []

    heads: list[int] = []
    candidates = list(explicit or [])
    if bm25:
        candidates.append(bm25[0])
    if vector:
        candidates.append(vector[0])

    for index in candidates:
        if index not in heads:
            heads.append(index)

    ordered = heads + [index for index, _score in fused if index not in heads]
    return ordered[:k]


def diversify(
    candidates: list[Candidate],
    max_per_kind: int = 3,
    k: int = 8,
) -> list[Candidate]:
    """限制同一类型候选数量，并按输入顺序去重。"""
    if k <= 0:
        return []

    result: list[Candidate] = []
    seen: set[uuid.UUID] = set()
    kind_counts: Counter[str] = Counter()

    for candidate in candidates:
        if candidate.element_id in seen:
            continue
        if max_per_kind > 0 and kind_counts[candidate.kind] >= max_per_kind:
            continue

        seen.add(candidate.element_id)
        kind_counts[candidate.kind] += 1
        result.append(candidate)
        if len(result) >= k:
            break

    return result


def vector_candidates(
    session: Session,
    analysis_id: uuid.UUID,
    embedding: list[float],
    k: int = 10,
) -> list[tuple[uuid.UUID, float]]:
    """用 pgvector 查询最近的设计要素，返回 (id, 余弦相似度)。

    内部取 4×k 个候选，并开启 HNSW 迭代扫描，尽量在 analysis_id
    过滤后仍能拿满 k 条；最终只返回前 k 条。
    """
    if k <= 0 or not embedding:
        return []

    limit = k * 4
    ef_search = max(limit, 40)
    session.exec(text("SET LOCAL hnsw.iterative_scan = 'relaxed_order'"))
    session.exec(text(f"SET LOCAL hnsw.ef_search = {int(ef_search)}"))

    embedding_col = DesignElement.__table__.c.embedding
    distance = embedding_col.cosine_distance(embedding)
    statement = (
        select(DesignElement.id, distance.label("distance"))
        .where(DesignElement.analysis_id == analysis_id)    # 针对特定一次 analysis 的设计要素
        .where(embedding_col.is_not(None))                  # 过滤掉没有 embedding 的设计要素
        .order_by(distance)                                 # 按余弦距离升序排序，距离越小相似度越高
        .limit(limit)                                       # 取前 limit 条
    )

    rows = session.exec(statement).all()
    return [(row[0], 1.0 - float(row[1])) for row in rows][:k]


class CandidateRetriever:
    """为一个原子需求召回设计要素候选。"""

    def __init__(self, session: Session, index: BM25FieldIndex) -> None:
        """保存数据库会话与关键词索引。"""
        self.session = session
        self.index = index

    def for_atom(
        self,
        analysis_id: uuid.UUID,
        atom: AtomicRequirement,
        k: int = 8,
    ) -> list[Candidate]:
        """返回融合、去重并做过多样性裁剪的候选。"""
        documents = self.index.documents
        if not documents or k <= 0:
            return []

        query = atom.search_text or atom.text
        bm25_hits = [
            index for index, _score in self.index.search(query, k=max(k * 2, 10))
        ]

        vector_hits: list[int] = []
        if atom.embedding:
            id_to_index = {
                str(document.get("id")): index
                for index, document in enumerate(documents)
                if document.get("id") is not None
            }
            for element_id, _score in vector_candidates(
                self.session,
                analysis_id,
                atom.embedding,
                k=k,
            ):
                index = id_to_index.get(str(element_id))
                if index is not None and index not in vector_hits:
                    vector_hits.append(index)

        explicit = [
            index
            for index, document in enumerate(documents)
            if document.get("code") and str(document["code"]) in atom.text
        ]

        fused = rrf_fuse([bm25_hits, vector_hits])
        fused_scores = dict(fused)
        chosen = ensure_heads(
            fused,
            bm25_hits,
            vector_hits,
            k,
            explicit=explicit,
        )

        candidates: list[Candidate] = []
        for index in chosen:
            document = documents[index]
            element_id = document.get("id")
            if element_id is None:
                continue
            if not isinstance(element_id, uuid.UUID):
                element_id = uuid.UUID(str(element_id))

            sources: list[str] = []
            if index in explicit:
                sources.append("explicit")
            if index in bm25_hits:
                sources.append("bm25")
            if index in vector_hits:
                sources.append("vector")

            candidates.append(
                Candidate(
                    element_id=element_id,
                    element_key=str(
                        document.get("element_key") or document.get("id")
                    ),
                    score=fused_scores.get(
                        index, 1.0 if index in explicit else 0.0
                    ),
                    sources=sources,
                    kind=str(document.get("kind") or ""),
                )
            )

        return diversify(candidates, max_per_kind=3, k=k)
