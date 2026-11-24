"""pgvector 向量召回测试。"""

from __future__ import annotations

import pytest
from sqlmodel import Session

from app.core.config import settings
from app.models import Analysis, DesignElement
from app.services.retrieval import vector_candidates

DIM = settings.EMBEDDING_DIM


def _vector(**components: float) -> list[float]:
    """构造指定维度的稀疏向量，键是维度下标。"""
    vector = [0.0] * DIM
    for index, value in components.items():
        vector[int(index)] = value
    return vector


def _element(
    analysis_id,
    element_key: str,
    embedding: list[float] | None,
) -> DesignElement:
    """构造一个最小可用的设计要素。"""
    return DesignElement(
        analysis_id=analysis_id,
        element_key=element_key,
        kind="module",
        name=element_key,
        embedding=embedding,
        embedding_model="test",
    )


def test_vector_candidates_sorted_and_filtered(session: Session) -> None:
    """按余弦相似度排序，并过滤其他分析与空向量。"""
    analysis = Analysis(title="A")
    other = Analysis(title="B")
    session.add_all([analysis, other])
    session.commit()
    session.refresh(analysis)
    session.refresh(other)

    e0 = _element(analysis.id, "e0", _vector(**{"0": 1.0}))
    e1 = _element(analysis.id, "e1", _vector(**{"0": 0.8, "1": 0.6}))
    e2 = _element(analysis.id, "e2", _vector(**{"1": 1.0}))
    e3 = _element(other.id, "e3", _vector(**{"0": 1.0}))
    e4 = _element(analysis.id, "e4", None)
    session.add_all([e0, e1, e2, e3, e4])
    session.commit()

    results = vector_candidates(
        session,
        analysis.id,
        _vector(**{"0": 1.0}),
        k=2,
    )

    assert [item[0] for item in results] == [e0.id, e1.id]
    assert results[0][1] == pytest.approx(1.0, abs=1e-5)
    assert results[1][1] == pytest.approx(0.8, abs=1e-5)


def test_vector_candidates_returns_k_after_filter(session: Session) -> None:
    """过滤掉大量其他分析后，仍应返回 k 条。"""
    analysis = Analysis(title="A")
    other = Analysis(title="B")
    session.add_all([analysis, other])
    session.commit()
    session.refresh(analysis)
    session.refresh(other)

    for index in range(6):
        session.add(
            _element(
                analysis.id,
                f"a{index}",
                _vector(**{"0": 1.0}),
            )
        )
    for index in range(20):
        session.add(
            _element(
                other.id,
                f"b{index}",
                _vector(**{"0": 1.0}),
            )
        )
    session.commit()

    results = vector_candidates(
        session,
        analysis.id,
        _vector(**{"0": 1.0}),
        k=3,
    )

    assert len(results) == 3


def test_vector_candidates_empty_inputs(session: Session) -> None:
    """空向量或非正 k 返回空列表。"""
    analysis = Analysis(title="A")
    session.add(analysis)
    session.commit()
    session.refresh(analysis)

    assert vector_candidates(session, analysis.id, [], k=3) == []
    assert vector_candidates(
        session,
        analysis.id,
        _vector(**{"0": 1.0}),
        k=0,
    ) == []
