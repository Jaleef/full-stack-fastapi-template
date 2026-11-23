"""docx 块读取的单元测试。"""

from __future__ import annotations

from pathlib import Path

from docx import Document

from app.domain import BlockKind
from app.services.docx_reader import iter_blocks, normalize_cell


def _build_docx(path: Path) -> None:
    """生成一个包含段落、空段落和表格的测试文档。"""
    document = Document()
    document.add_paragraph("1 范围")
    document.add_paragraph("")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "需求ID"
    table.cell(0, 1).text = "DT_REQ_001"
    table.cell(1, 0).text = "需求描述"
    table.cell(1, 1).text = "  系统应支持登录  "
    document.add_paragraph("3.2 用例描述")
    document.save(str(path))


def test_iter_blocks_order(tmp_path: Path) -> None:
    """段落、表格、段落应按文档顺序产出，空段落被跳过。"""
    path = tmp_path / "sample.docx"
    _build_docx(path)

    blocks = list(iter_blocks(path))

    assert [block.kind for block in blocks] == [
        BlockKind.PARAGRAPH,
        BlockKind.TABLE,
        BlockKind.PARAGRAPH,
    ]
    assert blocks[0].text == "1 范围"
    assert blocks[2].text == "3.2 用例描述"
    assert blocks[1].table == [
        ["需求ID", "DT_REQ_001"],
        ["需求描述", "系统应支持登录"],
    ]


def test_block_index_is_sequential(tmp_path: Path) -> None:
    """块的 index 从 0 开始连续递增。"""
    path = tmp_path / "sample.docx"
    _build_docx(path)

    blocks = list(iter_blocks(path))

    assert [block.index for block in blocks] == [0, 1, 2]


def test_merged_cells_are_deduplicated(tmp_path: Path) -> None:
    """横向合并单元格只保留一次文本。"""
    path = tmp_path / "merged.docx"
    document = Document()
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "合并"
    table.cell(0, 0).merge(table.cell(0, 1))
    table.cell(1, 0).text = "a"
    table.cell(1, 1).text = "b"
    document.save(str(path))

    blocks = list(iter_blocks(path))

    assert blocks[0].table == [["合并"], ["a", "b"]]


def test_caption_binding(tmp_path: Path) -> None:
    """表题应绑定到紧随其后的表格。"""
    path = tmp_path / "caption.docx"
    document = Document()
    document.add_paragraph("表6-1. 登录信息表")
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "编号"
    table.cell(0, 1).text = "字段名称"
    document.save(str(path))

    blocks = list(iter_blocks(path))

    assert [block.kind for block in blocks] == [BlockKind.CAPTION, BlockKind.TABLE]
    assert blocks[1].caption == "表6-1. 登录信息表"


def test_normalize_cell() -> None:
    """全角空格与换行应被规范化。"""
    assert normalize_cell("  第一行 \u3000 第二行  \r\n 第三行 ") == (
        "第一行   第二行\n第三行"
    )
