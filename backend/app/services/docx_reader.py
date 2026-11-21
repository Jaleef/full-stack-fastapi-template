"""读取 docx，并按文档顺序输出结构块。"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from app.domain import Block


def iter_blocks(path: Path) -> Iterator[Block]:
    """按文档顺序逐个产出段落和表格块。"""
    ...


def read_table(table: Any) -> list[list[str]]:
    """把 python-docx 表格读成规整的文本行。"""
    ...


def iter_row_cells(row: Any) -> list[str]:
    """读取一行单元格，并合并单元格去重。"""
    ...


def caption_for_table(previous: Block | None) -> str | None:
    """当上一块是表题时返回表题文本。"""
    ...


def normalize_cell(text: str) -> str:
    """规范化单元格里的空白与全角字符。"""
    ...
