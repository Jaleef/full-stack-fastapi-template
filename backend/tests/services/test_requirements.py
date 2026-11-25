"""需求判定提示词与真实客户端测试。"""

from __future__ import annotations

import pytest
from sqlmodel import select

from app.crud import save_decisions
from app.domain import Block, BlockKind, CandidateBlock, DocRole, Section
from app.models import Analysis, ParseDecision
from app.services.prompts import (
    REQUIREMENT_KINDS,
    REQUIREMENT_VERDICTS,
    build_requirement_judge_messages,
)
from app.services.requirements import (
    Decision,
    _parse_decisions,
    build_parse_decisions,
    fill_missing,
    judge_blocks,
)


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


def test_fill_missing_uses_real_client(real_llm) -> None:
    """缺少判定时应补问缺失块，已有判定保持不变。"""
    blocks = [
        _candidate(0, "系统应支持用户登录。"),
        _candidate(1, "系统应支持导出报表。"),
    ]
    existing = [
        Decision(
            index=0,
            verdict="requirement",
            kind="functional",
            reason="已有判定",
            confidence=0.9,
        )
    ]
    client = _CountingClient(real_llm)

    decisions = fill_missing(client, blocks, existing)

    assert client.calls == 1
    assert {item.index for item in decisions} == {0, 1}
    assert decisions[0] is existing[0]
    assert decisions[1].verdict in REQUIREMENT_VERDICTS


def test_fill_missing_noop_skips_client(real_llm) -> None:
    """没有缺项时不应发起补问。"""
    blocks = [_candidate(0, "系统应支持登录。"), _candidate(1, "系统应支持导出。")]
    existing = [
        Decision(index=0, verdict="requirement", kind="functional"),
        Decision(index=1, verdict="requirement", kind="functional"),
    ]
    client = _CountingClient(real_llm)

    decisions = fill_missing(client, blocks, existing)

    assert client.calls == 0
    assert [item.index for item in decisions] == [0, 1]


def test_build_and_save_parse_decisions(session) -> None:
    """判定结果应能转成 parse_decision 行并落库。"""
    analysis = Analysis(title="D2 判定落库")
    session.add(analysis)
    session.commit()
    session.refresh(analysis)

    blocks = [_candidate(0, "系统应支持登录。"), _candidate(1, "目录")]
    decisions = [
        Decision(
            index=0,
            verdict="requirement",
            kind="functional",
            reason="规定登录行为",
            confidence=0.95,
        ),
        Decision(
            index=1,
            verdict="not_requirement",
            kind=None,
            reason="目录不是需求",
            confidence=0.99,
        ),
    ]

    rows = build_parse_decisions(analysis.id, blocks, decisions)
    save_decisions(session, rows)

    assert len(rows) == 2
    assert rows[0].role == DocRole.REQUIREMENTS.value
    assert rows[0].block_index == 0
    assert rows[0].section_no == "3"
    assert rows[0].text == "系统应支持登录。"
    assert rows[1].order_index == 1

    saved = session.exec(select(ParseDecision)).all()
    assert len(saved) == 2
    assert {row.order_index for row in saved} == {0, 1}
    assert {row.verdict for row in saved} == {"requirement", "not_requirement"}
