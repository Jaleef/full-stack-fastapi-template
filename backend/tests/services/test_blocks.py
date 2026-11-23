"""候选切块策略的单元测试。"""

from __future__ import annotations

from pathlib import Path

from docx import Document

from app.domain import DocRole
from app.services.docx_reader import iter_blocks
from app.services.parsing import Profile, split_blocks


def _build_docx(path: Path) -> None:
    """生成包含四类表格和段落的测试文档。"""
    document = Document()

    document.add_paragraph("记录表")
    record = document.add_table(rows=3, cols=2)
    record.cell(0, 0).text = "需求ID"
    record.cell(0, 1).text = "需求描述"
    record.cell(1, 0).text = "DT_REQ_001"
    record.cell(1, 1).text = "系统应支持登录"

    document.add_paragraph("大表")
    large = document.add_table(rows=12, cols=2)
    large.cell(0, 0).text = "序号"
    large.cell(0, 1).text = "内容"
    for row_index in range(1, 12):
        large.cell(row_index, 0).text = str(row_index)
        large.cell(row_index, 1).text = f"第{row_index}行"

    document.add_paragraph("数据表")
    data = document.add_table(rows=10, cols=3)
    data.cell(0, 0).text = "编号"
    data.cell(0, 1).text = "字段名称"
    data.cell(0, 2).text = "字段类型"
    for row_index in range(1, 10):
        data.cell(row_index, 1).text = f"field_{row_index}"
        data.cell(row_index, 2).text = "varchar"

    document.add_paragraph("约束表")
    constraint = document.add_table(rows=4, cols=2)
    constraint.cell(0, 0).text = "开发环境或相关约束项"
    constraint.cell(0, 1).text = "限制"
    constraint.cell(1, 0).text = "操作系统"
    constraint.cell(1, 1).text = "Linux"
    constraint.cell(2, 0).text = "数据库"
    constraint.cell(2, 1).text = "PostgreSQL"
    constraint.cell(3, 0).text = "语言"
    constraint.cell(3, 1).text = "Python"

    document.save(str(path))


def _reasons(candidates) -> list[str]:
    return [candidate.reason or "" for candidate in candidates]


def test_split_tables_for_design(tmp_path: Path) -> None:
    """设计文档：记录表整表、大表分块、字段表整表、约束表按行。"""
    path = tmp_path / "blocks.docx"
    _build_docx(path)

    blocks = list(iter_blocks(path))
    candidates = split_blocks(blocks, DocRole.DESIGN, Profile(name="generic"))
    reasons = _reasons(candidates)

    assert reasons.count("paragraph") == 4
    assert reasons.count("table:record") == 1
    assert reasons.count("table:data") == 1
    assert sum(1 for reason in reasons if reason.startswith("table:chunk:")) == 3
    assert sum(1 for reason in reasons if reason.startswith("table:constraint:")) == 3

    chunks = [
        candidate
        for candidate in candidates
        if (candidate.reason or "").startswith("table:chunk:")
    ]
    assert [len(candidate.block.table) for candidate in chunks] == [6, 6, 2]

    data = [c for c in candidates if c.reason == "table:data"][0]
    assert len(data.block.table) == 10

    constraint_rows = [
        candidate
        for candidate in candidates
        if (candidate.reason or "").startswith("table:constraint:")
    ]
    assert constraint_rows[0].block.table == [
        ["开发环境或相关约束项", "限制"],
        ["操作系统", "Linux"],
    ]


def test_requirements_tables_use_record_rules(tmp_path: Path) -> None:
    """需求文档不做字段表/约束表特判，统一走记录/分块。"""
    path = tmp_path / "blocks.docx"
    _build_docx(path)

    blocks = list(iter_blocks(path))
    candidates = split_blocks(blocks, DocRole.REQUIREMENTS, Profile(name="generic"))
    reasons = _reasons(candidates)

    assert "table:data" not in reasons
    assert not any(reason.startswith("table:constraint:") for reason in reasons)


def test_split_skips_toc(tmp_path: Path) -> None:
    """目录条目不应成为候选块。"""
    path = tmp_path / "toc.docx"
    document = Document()
    document.add_paragraph("目   录")
    document.add_paragraph("1 范围\t1")
    document.add_paragraph("范围")
    document.add_paragraph("正文段落")
    document.save(str(path))

    blocks = list(iter_blocks(path))
    candidates = split_blocks(blocks, DocRole.REQUIREMENTS, Profile(name="generic"))
    texts = [candidate.block.text for candidate in candidates]

    assert "1 范围\t1" not in texts
    assert "正文段落" in texts
