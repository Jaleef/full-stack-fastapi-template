"""BM25F 关键词索引测试。"""

from __future__ import annotations

from app.services.retrieval import BM25FieldIndex, tokenize


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
