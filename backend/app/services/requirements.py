"""需求文档抽取：块判定、原子拆分与语义合并。"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from pydantic import BaseModel

from app.domain import CandidateBlock, DocRole
from app.models import AtomicRequirement, ParseDecision
from app.services.llm import LLMClient
from app.services.prompts import (
    REQUIREMENT_KINDS,
    REQUIREMENT_VERDICTS,
    build_requirement_judge_messages,
)


class Decision(BaseModel):
    """一个候选块的需求判定结果。"""

    index: int
    verdict: str
    kind: str | None = None
    reason: str | None = None
    confidence: float | None = None


def _block_payload(block: CandidateBlock, index: int) -> dict:
    """把候选块转成提示词里的精简结构。"""
    return {
        "index": index,
        "text": block.block.text,
        "context": block.context,
        "reason": block.reason,
    }


def _normalize_decision(item: dict, index: int) -> Decision | None:
    """校验并规范化模型返回的一条判定。"""
    verdict = str(item.get("verdict") or "").strip().lower()
    if verdict not in REQUIREMENT_VERDICTS:
        return None

    kind = item.get("kind")
    if kind is not None:
        kind = str(kind).strip().lower()
        if kind not in REQUIREMENT_KINDS:
            kind = None

    reason = item.get("reason")
    if reason is not None:
        reason = str(reason).strip() or None

    confidence = item.get("confidence")
    if confidence is not None:
        try:
            confidence = max(0.0, min(1.0, float(confidence)))
        except (TypeError, ValueError):
            confidence = None

    return Decision(
        index=index,
        verdict=verdict,
        kind=kind,
        reason=reason,
        confidence=confidence,
    )


def _parse_decisions(response: dict, offset: int, batch_size: int) -> list[Decision]:
    """解析一批响应，只保留索引与枚举合法的判定。"""
    items = response.get("decisions")
    if not isinstance(items, list):
        return []

    by_index: dict[int, Decision] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            local_index = int(item.get("index"))
        except (TypeError, ValueError):
            continue
        if local_index < 0 or local_index >= batch_size:
            continue

        decision = _normalize_decision(item, offset + local_index)
        if decision is not None:
            by_index[local_index] = decision

    return [by_index[index] for index in sorted(by_index)]


def judge_blocks(
    client: LLMClient,
    blocks: list[CandidateBlock],
    batch_size: int = 12,
) -> list[Decision]:
    """批量判定候选块是否为真实需求。"""
    if batch_size <= 0:
        raise ValueError("batch_size 必须大于 0")
    if not blocks:
        return []

    decisions: list[Decision] = []
    for offset in range(0, len(blocks), batch_size):
        batch = blocks[offset : offset + batch_size]
        payload = {
            "blocks": [
                _block_payload(block, index)
                for index, block in enumerate(batch)
            ]
        }
        messages = build_requirement_judge_messages(payload)
        response = client.chat_json(
            messages[0]["content"],
            messages[1]["content"],
        )
        decisions.extend(
            _parse_decisions(response, offset=offset, batch_size=len(batch))
        )

    return decisions


def fill_missing(
    client: LLMClient,
    blocks: list[CandidateBlock],
    decisions: list[Decision],
) -> list[Decision]:
    """对未返回判定的块补问一次。"""
    if not blocks:
        return []

    existing = {
        decision.index: decision
        for decision in decisions
        if 0 <= decision.index < len(blocks)
    }
    missing = [index for index in range(len(blocks)) if index not in existing]
    if not missing:
        return [existing[index] for index in sorted(existing)]

    extra = judge_blocks(client, [blocks[index] for index in missing])
    for decision in extra:
        if not 0 <= decision.index < len(missing):
            continue
        global_index = missing[decision.index]
        existing[global_index] = Decision(
            index=global_index,
            verdict=decision.verdict,
            kind=decision.kind,
            reason=decision.reason,
            confidence=decision.confidence,
        )

    return [existing[index] for index in sorted(existing)]


def build_parse_decisions(
    analysis_id: uuid.UUID,
    blocks: list[CandidateBlock],
    decisions: list[Decision],
    role: DocRole = DocRole.REQUIREMENTS,
) -> list[ParseDecision]:
    """把判定结果转成可落库的 parse_decision 行。"""
    by_index = {decision.index: decision for decision in decisions}
    rows: list[ParseDecision] = []

    for order, block in enumerate(blocks):
        decision = by_index.get(order)
        if decision is None:
            continue

        text = block.block.text or block.block.caption or ""
        rows.append(
            ParseDecision(
                analysis_id=analysis_id,
                role=role.value,
                block_index=block.block.index,
                section_no=block.section.number or None,
                section_title=block.section.title or None,
                text=text,
                verdict=decision.verdict,
                kind=decision.kind,
                reason=decision.reason[:512] if decision.reason else None,
                confidence=decision.confidence,
                order_index=order,
            )
        )

    return rows


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
