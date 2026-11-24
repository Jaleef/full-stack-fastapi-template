"""检索底座端到端自测：假 embedder + 真实 PostgreSQL。"""

from __future__ import annotations

from sqlmodel import Session

from app.core.config import settings
from app.models import Analysis, AtomicRequirement, DesignElement
from app.services.retrieval import BM25FieldIndex, CandidateRetriever

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
    name: str,
    kind: str,
    code: str | None,
    embedding: list[float],
) -> DesignElement:
    """构造一个带假向量的设计要素。"""
    return DesignElement(
        analysis_id=analysis_id,
        element_key=element_key,
        kind=kind,
        code=code,
        name=name,
        embedding=embedding,
        embedding_model="fake",
    )


def _document(element: DesignElement) -> dict:
    """把设计要素转成 BM25F 的文档字典。"""
    return {
        "id": element.id,
        "element_key": element.element_key,
        "kind": element.kind,
        "code": element.code,
        "name": element.name,
        "description": element.name,
    }


def test_candidates_end_to_end(session: Session) -> None:
    """BM25F + pgvector + RRF 串起来后，显式 ID 与两路来源都应出现。"""
    analysis = Analysis(title="检索底座自测")
    session.add(analysis)
    session.commit()
    session.refresh(analysis)

    d0 = _element(
        analysis.id, "m0", "登录功能", "module", "5.2.1", _vector(**{"0": 1.0})
    )
    d1 = _element(
        analysis.id, "m1", "用户管理", "module", "5.2.2", _vector(**{"0": 0.8, "1": 0.6})
    )
    d2 = _element(
        analysis.id, "p0", "登录页面", "page", None, _vector(**{"0": 0.6, "1": 0.8})
    )
    d3 = _element(
        analysis.id, "m2", "报表导出", "module", None, _vector(**{"1": 1.0})
    )
    session.add_all([d0, d1, d2, d3])
    session.commit()

    index = BM25FieldIndex([_document(item) for item in (d0, d1, d2, d3)])
    atom = AtomicRequirement(
        analysis_id=analysis.id,
        text="依据 5.2.1，系统应支持用户登录",
        search_text="用户登录",
        kind="functional",
        embedding=_vector(**{"0": 1.0}),
    )

    candidates = CandidateRetriever(session, index).for_atom(
        analysis.id, atom, k=4
    )

    assert candidates
    assert candidates[0].element_id == d0.id
    assert "explicit" in candidates[0].sources
    assert any("vector" in item.sources for item in candidates)
    assert any("bm25" in item.sources for item in candidates)
    assert len(candidates) <= 4
    assert len({item.element_id for item in candidates}) == len(candidates)


def test_candidates_limit_same_kind(session: Session) -> None:
    """端到端流程中同一 kind 仍最多保留 3 个。"""
    analysis = Analysis(title="同 kind 限制")
    session.add(analysis)
    session.commit()
    session.refresh(analysis)

    elements = [
        _element(
            analysis.id,
            f"m{index}",
            f"登录模块{index}",
            "module",
            None,
            _vector(**{"0": 1.0}),
        )
        for index in range(6)
    ]
    page = _element(
        analysis.id, "p0", "登录页面", "page", None, _vector(**{"0": 1.0})
    )
    session.add_all([*elements, page])
    session.commit()

    index = BM25FieldIndex([_document(item) for item in (*elements, page)])
    atom = AtomicRequirement(
        analysis_id=analysis.id,
        text="系统应支持用户登录",
        search_text="登录",
        kind="functional",
        embedding=_vector(**{"0": 1.0}),
    )

    candidates = CandidateRetriever(session, index).for_atom(
        analysis.id, atom, k=8
    )

    assert sum(1 for item in candidates if item.kind == "module") <= 3
