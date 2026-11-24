"""B 阶段自测：两份样例的解析与切块快照。"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.domain import DocRole
from app.services.docx_reader import iter_blocks
from app.services.parsing import (
    MAX_TEXT_LENGTH,
    Profile,
    iter_headings,
    parse_toc,
    split_blocks,
)

BACKEND_DIR = Path(__file__).resolve().parents[2]
SAMPLES_DIR = BACKEND_DIR / "samples"

CASES = (
    ("requirements.docx", DocRole.REQUIREMENTS, 567, 90, 122, 401),
    ("design.docx", DocRole.DESIGN, 1653, 109, 91, 1329),
)


@pytest.mark.parametrize(
    (
        "filename",
        "role",
        "block_count",
        "table_count",
        "heading_count",
        "candidate_count",
    ),
    CASES,
)
def test_stage_snapshot(
    filename: str,
    role: DocRole,
    block_count: int,
    table_count: int,
    heading_count: int,
    candidate_count: int,
) -> None:
    """两份样例的内容统计应与当前解析策略一致。"""
    path = SAMPLES_DIR / filename
    if not path.exists():
        pytest.skip(f"样例文档不存在：{path}")

    blocks = list(iter_blocks(path))
    headings = list(iter_headings(blocks))
    toc = parse_toc(blocks)
    candidates = split_blocks(blocks, role, Profile(name="generic"))

    assert len(blocks) == block_count
    assert sum(1 for block in blocks if block.kind.value == "table") == table_count
    assert len(headings) == heading_count == len(toc)
    assert len(candidates) == candidate_count
    assert all(
        len(candidate.block.text) <= MAX_TEXT_LENGTH for candidate in candidates
    )
    assert all(
        "\t" not in candidate.block.text
        for candidate in candidates
        if candidate.block.kind.value == "paragraph"
    )
