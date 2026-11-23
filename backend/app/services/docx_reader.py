"""读取 docx，并按文档顺序输出结构块。"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.domain import Block, BlockKind

CAPTION_RE = re.compile(r"^\s*(?:图|表)\s*\d+(?:[.\-]\d+)*\s*[.、]?\s*\S")
BLOCK_CONTAINERS = ("sdt", "customXml", "ins")


def _iter_block_elements(parent: Any) -> Iterator[Any]:
    """递归遍历块级元素，穿透 sdt / customXml / ins 等包装。

    设计文档的目录被包在 w:sdt 里，只遍历 body 直接子元素会漏掉整份目录。
    """
    for child in parent.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag in ("p", "tbl"):
            yield child
        elif tag == "sdt":
            content = child.find(qn("w:sdtContent"))
            if content is not None:
                yield from _iter_block_elements(content)
        elif tag in BLOCK_CONTAINERS:
            yield from _iter_block_elements(child)


def iter_blocks(path: Path) -> Iterator[Block]:
    """按文档顺序逐个产出段落、表题、图片和表格块。

    - 空段落跳过
    - 只有图片没有文字的段落产出 IMAGE 块
    - “表6-1 …”这类段落产出 CAPTION 块，并作为下一张表的 caption
    - 表格产出 TABLE 块，行文本放在 block.table
    """
    document = Document(str(path))
    index = 0
    previous: Block | None = None

    for child in _iter_block_elements(document.element.body):
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            text = normalize_cell(Paragraph(child, document).text)
            if not text:
                if child.xpath(".//w:drawing") or child.xpath(".//w:pict"):
                    block = Block(kind=BlockKind.IMAGE, text="", index=index)
                else:
                    continue
            elif CAPTION_RE.match(text):
                block = Block(kind=BlockKind.CAPTION, text=text, index=index)
            else:
                block = Block(kind=BlockKind.PARAGRAPH, text=text, index=index)
        elif tag == "tbl":
            rows = read_table(Table(child, document))
            if not rows:
                continue
            block = Block(
                kind=BlockKind.TABLE,
                text="",
                index=index,
                table=rows,
                caption=caption_for_table(previous),
            )
        else:
            continue

        yield block
        previous = block
        index += 1


def read_table(table: Table) -> list[list[str]]:
    """把 python-docx 表格读成规整的文本行，跳过全空行。"""
    rows: list[list[str]] = []
    for row in table.rows:
        cells = iter_row_cells(row)
        if any(cells):
            rows.append(cells)
    return rows


def iter_row_cells(row: Any) -> list[str]:
    """读取一行单元格文本，按底层 tc 去重合并单元格。

    合并单元格在 python-docx 中会返回多个指向同一 tc 的 cell，
    如果不去重，“需求ID / 需求描述”这类标签列会重复，值和标签会错位。
    """
    cells: list[str] = []
    seen: set[int] = set()
    for cell in row.cells:
        key = id(cell._tc)
        if key in seen:
            continue
        seen.add(key)
        cells.append(normalize_cell(cell.text))
    return cells


def caption_for_table(previous: Block | None) -> str | None:
    """当上一块是表题时返回表题文本。"""
    if previous is not None and previous.kind == BlockKind.CAPTION:
        return previous.text
    return None


def normalize_cell(text: str) -> str:
    """规范化单元格空白：全角空格转半角、统一换行、去掉首尾空白。"""
    if not text:
        return ""
    normalized = text.replace("\u3000", " ")
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.strip() for line in normalized.split("\n")).strip()
