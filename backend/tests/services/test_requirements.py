"""需求判定提示词与真实客户端测试。"""

from __future__ import annotations

import pytest

from app.domain import Block, BlockKind, CandidateBlock, DocRole, Section
from app.services.prompts import (
    REQUIREMENT_KINDS,
    REQUIREMENT_VERDICTS,
    build_requirement_judge_messages,
)
from app.services.requirements import _parse_decisions, judge_blocks


def _candidate(index: int, text: str) -> CandidateBlock:
    """构造一个最小候选块。"""
    return CandidateBlock(
        block=Block(kind=BlockKind.PARAGRAPH, text=text, index=index),
        section=Section(number="3", title="需求分析"),
        role=DocRole.REQUIREMENTS,
        reason="paragraph",
        context="章节：3 需求分析",
    )


class _CountingClient:
    """真实客户端的薄包装，只用于统计批次数。"""

    def __init__(self, client) -> None:
        self._client = client
        self.calls = 0

    def chat_json(self, system: str, user: str) -> dict:
        """透传给真实客户端并计数。"""
        self.calls += 1
        return self._client.chat_json(system, user)


def test_build_requirement_judge_messages() -> None:
    """提示词应保持通用，不绑定特定行业或模板。"""
    messages = build_requirement_judge_messages(
        {"blocks": [{"index": 0, "text": "系统应支持登录"}]}
    )

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "任意行业" in messages[0]["content"]
    assert "not_requirement" in messages[0]["content"]
    assert "系统应支持登录" in messages[1]["content"]


def test_judge_blocks_with_real_client(real_llm) -> None:
    """真实客户端应返回 12 条合法判定。"""
    texts = [
        "目 录",
        "表3-1 登录字段",
        "系统应支持用户通过用户名和密码登录。",
        "登录失败时，系统应提示错误信息。",
        "系统应支持不少于 1000 个并发用户。",
        "系统应提供用户管理、权限分配和日志审计功能。",
        "本文档适用于系统开发、测试和维护人员。",
        "修改记录：V1.0 初稿。",
        "界面应提供登录和退出按钮。",
        "登录接口应采用 HTTPS。",
        "数据库应使用 PostgreSQL 16。",
        "系统应支持中英文界面。",
    ]
    blocks = [_candidate(index, text) for index, text in enumerate(texts)]

    decisions = judge_blocks(real_llm, blocks, batch_size=12)

    assert len(decisions) == 12
    assert {item.index for item in decisions} == set(range(12))
    assert all(item.verdict in REQUIREMENT_VERDICTS for item in decisions)
    assert all(
        item.kind is None or item.kind in REQUIREMENT_KINDS for item in decisions
    )
    assert all(
        item.confidence is None or 0.0 <= item.confidence <= 1.0
        for item in decisions
    )

    verdicts = {item.index: item.verdict for item in decisions}
    assert verdicts[0] == "not_requirement"
    assert verdicts[1] == "not_requirement"
    assert verdicts[6] == "not_requirement"
    assert verdicts[7] == "not_requirement"
    for index in (2, 3, 4, 5, 8, 9, 10, 11):
        assert verdicts[index] == "requirement"


def test_judge_blocks_splits_by_12_with_real_client(real_llm) -> None:
    """13 个块应通过真实客户端分两批判定。"""
    blocks = [
        _candidate(index, f"系统应支持功能{index}。")
        for index in range(13)
    ]
    client = _CountingClient(real_llm)

    decisions = judge_blocks(client, blocks)

    assert client.calls == 2
    assert len(decisions) == 13
    assert {item.index for item in decisions} == set(range(13))


def test_parse_decisions_filters_invalid_enums() -> None:
    """非法枚举应被丢弃，重复 index 以后出现者为准。"""
    response = {
        "decisions": [
            {
                "index": 0,
                "verdict": "requirement",
                "kind": "not-a-kind",
                "confidence": 2.0,
            },
            {"index": 1, "verdict": "maybe", "kind": "functional"},
            {"index": 0, "verdict": "group", "kind": "other"},
        ]
    }

    decisions = _parse_decisions(response, offset=10, batch_size=2)

    assert len(decisions) == 1
    assert decisions[0].index == 10
    assert decisions[0].verdict == "group"
    assert decisions[0].kind == "other"
    assert decisions[0].confidence is None


def test_judge_blocks_empty_and_invalid_batch_size(real_llm) -> None:
    """空输入返回空；非法 batch_size 抛错。"""
    assert judge_blocks(real_llm, []) == []

    with pytest.raises(ValueError, match="batch_size"):
        judge_blocks(real_llm, [_candidate(0, "系统应支持登录。")], batch_size=0)
