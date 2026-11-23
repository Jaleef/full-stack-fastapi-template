"""章节识别与目录过滤的单元测试。"""

from __future__ import annotations

from pathlib import Path

from docx import Document

from app.services.docx_reader import iter_blocks
from app.services.parsing import (
    assign_sections,
    is_toc_entry,
    iter_headings,
    parse_heading,
    section_path,
)


def _build_docx(path: Path) -> None:
    """生成包含目录、三级标题和正文的测试文档。"""
    document = Document()
    document.add_paragraph("修改页")
    document.add_paragraph("目   录")
    document.add_paragraph("1 范围\t1")
    document.add_paragraph("1.1 标识\t1")
    document.add_paragraph("2 引用文档\t1")
    document.add_paragraph("1 范围")
    document.add_paragraph("1.1 标识")
    document.add_paragraph("正文段落")
    document.add_paragraph("2 引用文档")
    document.add_paragraph("引用段落")
    document.save(str(path))


def test_is_toc_entry() -> None:
    """目录条目识别。"""
    assert is_toc_entry("1 范围\t1")
    assert is_toc_entry("1.1 标识    1")
    assert not is_toc_entry("1 范围")


def test_parse_heading() -> None:
    """编号标题解析与层级推导。"""
    heading = parse_heading("1.1 标识")
    assert heading is not None
    assert heading.number == "1.1"
    assert heading.title == "标识"
    assert heading.level == 2
    assert parse_heading("1 范围\t1") is None
    assert parse_heading("正文段落") is None


def test_iter_headings_skips_toc(tmp_path: Path) -> None:
    """标题迭代应跳过目录区。"""
    path = tmp_path / "sample.docx"
    _build_docx(path)

    headings = list(iter_headings(list(iter_blocks(path))))

    assert [item.number for item in headings] == ["1", "1.1", "2"]
    assert [item.title for item in headings] == ["范围", "标识", "引用文档"]


def test_assign_sections(tmp_path: Path) -> None:
    """正文块应带上正确章节，目录条目被跳过。"""
    path = tmp_path / "sample.docx"
    _build_docx(path)

    pairs = list(assign_sections(list(iter_blocks(path))))

    assert all("\t" not in block.text for block, _section in pairs)
    by_text = {block.text: section for block, section in pairs}
    assert by_text["正文段落"].number == "1.1"
    assert by_text["引用段落"].number == "2"

    body_section = by_text["正文段落"]
    assert section_path(body_section) == "1 范围 / 1.1 标识"


def test_auto_numbered_headings_use_toc(tmp_path: Path) -> None:
    """正文标题只有文字时，用目录里的编号重建标题。"""
    path = tmp_path / "auto_numbered.docx"
    document = Document()
    document.add_paragraph("目   录")
    document.add_paragraph("1 范围\t1")
    document.add_paragraph("1.1 标识\t1")
    document.add_paragraph("范围")
    document.add_paragraph("标识")
    document.add_paragraph("正文段落")
    document.save(str(path))

    blocks = list(iter_blocks(path))
    headings = list(iter_headings(blocks))
    pairs = list(assign_sections(blocks))

    assert [item.number for item in headings] == ["1", "1.1"]
    assert [item.title for item in headings] == ["范围", "标识"]
    by_text = {block.text: section for block, section in pairs}
    assert by_text["正文段落"].number == "1.1"

