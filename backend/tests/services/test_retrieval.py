"""BM25F 关键词索引与候选策略测试。"""

from __future__ import annotations

import uuid

from app.domain import Candidate
from app.models import AtomicRequirement
from app.services import retrieval
from app.services.retrieval import (
    BM25FieldIndex,
    CandidateRetriever,
    diversify,
    ensure_heads,
    rrf_fuse,
    tokenize,
)


def test_tokenize_mixed_text() -> None:
    """中文分词与英文小写化。"""
    tokens = tokenize("用户登录 PostgreSQL 数据库")

    assert "登录" in tokens
    assert "postgresql" in tokens


def test_name_match_outranks_long_description() -> None:
    """名称命中应排在长描述命中之前。"""
    documents = [
        {"name": "登录功能", "description": "支持用户登录。"},
        {
            "name": "用户管理",
            "description": (
                "本模块负责用户管理、权限分配、日志审计、配置维护等大量功能，"
                "登录只是其中一项。"
            ),
        },
        {"name": "报表导出", "description": "导出统计报表。"},
    ]
    index = BM25FieldIndex(documents)

    results = index.search("登录")

    assert results
    assert results[0][0] == 0


def test_field_weights_change_ranking() -> None:
    """调整字段权重应改变排序。"""
    documents = [
        {"name": "登录功能", "description": ""},
        {"name": "用户管理", "description": "登录"},
    ]

    default = BM25FieldIndex(documents)
    description_only = BM25FieldIndex(
        documents,
        field_weights={"name": 0.0, "description": 1.0},
    )

    assert default.search("登录")[0][0] == 0
    assert description_only.search("登录")[0][0] == 1


def test_unknown_query_and_empty_index() -> None:
    """未知词、空查询、空索引都返回空列表。"""
    index = BM25FieldIndex([{"name": "登录功能"}])

    assert index.search("不存在的词") == []
    assert index.search("") == []
    assert BM25FieldIndex([]).search("登录") == []


def test_search_respects_k() -> None:
    """结果数量不超过 k。"""
    documents = [
        {"name": "登录功能"},
        {"name": "登录日志"},
        {"name": "登录审计"},
    ]
    index = BM25FieldIndex(documents)

    assert len(index.search("登录", k=1)) == 1
    assert len(index.search("登录", k=10)) == 3


def test_rrf_fuse_is_deterministic() -> None:
    """RRF 分数与顺序应稳定，重复项只算第一次。"""
    fused = rrf_fuse([[1, 2, 3], [3, 1, 2]])

    assert [index for index, _score in fused] == [1, 3, 2]
    assert rrf_fuse([[1, 1, 2]])[0][0] == 1


def test_ensure_heads_injects_top1_and_explicit() -> None:
    """显式 ID 与两路 top-1 必须进入结果。"""
    fused = [(2, 0.9), (3, 0.8)]

    result = ensure_heads(fused, bm25=[1, 2], vector=[4, 3], k=3, explicit=[5])

    assert result == [5, 1, 4]


def test_diversify_limits_same_kind() -> None:
    """同一 kind 最多保留 max_per_kind 个。"""
    candidates = [
        Candidate(uuid.uuid4(), f"m{index}", 1.0, kind="module")
        for index in range(4)
    ] + [Candidate(uuid.uuid4(), "p0", 0.5, kind="page")]

    result = diversify(candidates, max_per_kind=3, k=8)

    assert sum(1 for item in result if item.kind == "module") == 3
    assert sum(1 for item in result if item.kind == "page") == 1


def test_candidate_retriever_injects_explicit_code(monkeypatch) -> None:
    """原子文本里出现的模块编号应被显式注入。"""
    analysis_id = uuid.uuid4()
    d0 = uuid.uuid4()
    d1 = uuid.uuid4()
    documents = [
        {
            "id": d0,
            "element_key": "m0",
            "kind": "module",
            "code": "5.2.1",
            "name": "登录功能",
        },
        {
            "id": d1,
            "element_key": "m1",
            "kind": "module",
            "code": "5.2.2",
            "name": "用户管理",
        },
    ]
    index = BM25FieldIndex(documents)
    atom = AtomicRequirement(
        analysis_id=analysis_id,
        text="依据 5.2.1，用户管理需要登录",
        search_text="用户管理",
        kind="functional",
        embedding=[1.0, 0.0],
    )

    monkeypatch.setattr(
        retrieval,
        "vector_candidates",
        lambda *_args, **_kwargs: [(d1, 0.9)],
    )
    retriever = CandidateRetriever(None, index)  # type: ignore[arg-type]

    results = retriever.for_atom(analysis_id, atom, k=2)

    assert [item.element_id for item in results] == [d0, d1]
    assert "explicit" in results[0].sources
    assert "bm25" in results[1].sources or "vector" in results[1].sources
