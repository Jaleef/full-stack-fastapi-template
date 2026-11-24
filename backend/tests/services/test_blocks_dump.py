"""把真实样例的切块结果导出为 JSON，便于人工审查。

样例文档放在 backend/samples/（已被 .gitignore 忽略）。
运行本测试会生成 backend/artifacts/blocks_review.json。
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.domain import CandidateBlock, DocRole, Section
from app.services.docx_reader import iter_blocks
from app.services.parsing import Profile, split_blocks

BACKEND_DIR = Path(__file__).resolve().parents[2]
SAMPLES_DIR = BACKEND_DIR / "samples"
OUTPUT_PATH = BACKEND_DIR / "artifacts" / "blocks_review.json"

DOCUMENTS = (
    ("requirements", DocRole.REQUIREMENTS, SAMPLES_DIR / "requirements.docx"),
    ("design", DocRole.DESIGN, SAMPLES_DIR / "design.docx"),
)


def _section_payload(section: Section) -> dict:
    """把章节对象转成可序列化的字典。"""
    return {
        "number": section.number,
        "title": section.title,
        "level": section.level,
        "path": section.path,
    }


def _candidate_payload(candidate: CandidateBlock, ordinal: int) -> dict:
    """把候选块转成可读的 JSON 结构。"""
    block = candidate.block
    return {
        "ordinal": ordinal,
        "reason": candidate.reason,
        "kind": block.kind.value,
        "block_index": block.index,
        "caption": block.caption,
        "context": candidate.context,
        "section": _section_payload(candidate.section),
        "text": block.text,
        "table": block.table,
    }


def test_dump_blocks_to_json() -> None:
    """执行一次切块，并把所有候选写入 JSON 供审查。"""
    missing = [str(path) for _, _, path in DOCUMENTS if not path.exists()]
    if missing:
        pytest.skip(f"样例文档不存在：{missing}")

    payload: dict = {
        "generated_at": datetime.now(UTC).isoformat(),
        "documents": {},
    }

    for name, role, path in DOCUMENTS:
        blocks = list(iter_blocks(path))
        candidates = split_blocks(blocks, role, Profile(name="generic"))
        payload["documents"][name] = {
            "role": role.value,
            "source": str(path.relative_to(BACKEND_DIR)),
            "block_count": len(blocks),
            "candidate_count": len(candidates),
            "block_kinds": dict(Counter(block.kind.value for block in blocks)),
            "reasons": dict(Counter(candidate.reason or "" for candidate in candidates)),
            "candidates": [
                _candidate_payload(candidate, ordinal)
                for ordinal, candidate in enumerate(candidates)
            ],
        }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    saved = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    assert saved["documents"]["requirements"]["candidate_count"] > 0
    assert saved["documents"]["design"]["candidate_count"] > 0
    assert saved["documents"]["requirements"]["candidates"][0]["reason"]
    assert OUTPUT_PATH.stat().st_size > 0
