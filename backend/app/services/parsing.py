"""章节识别与目录过滤。

说明：样例文档的正文标题使用了 Word 自动编号，`paragraph.text` 里只有标题文字、
没有“1”“1.1”这样的编号。因此标题解析以目录条目为准：先从目录提取
“编号 + 标题”的有序列表，再在正文里按顺序匹配标题文字，重建编号与层级。
没有目录或正文自带编号时，退回文本正则解析。
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from dataclasses import dataclass, field, replace

from app.domain import Block, BlockKind, CandidateBlock, DocRole, Heading, Section

logger = logging.getLogger(__name__)

HEADING_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)[\.、]?\s+(\S.*?)\s*$")
TOC_RE = re.compile(r"^\s*(\S.*?)\s*(?:\t|\s{2,})\s*\d+\s*$")
TOC_ENTRY_RE = re.compile(
    r"^\s*(\d+(?:\.\d+)*)[\.、]?\s+(.*?)\s*(?:\t|\s{2,})\s*\d+\s*$"
)
TOC_TITLE_RE = re.compile(r"^\s*目\s*录\s*$")

# 单个候选的文本上限与整个分析的候选上限
MAX_TEXT_LENGTH = 800
MAX_CANDIDATES = 2000


def is_toc_entry(text: str) -> bool:
    """判断文本是否像目录条目（标题 + 页码）。"""
    return bool(TOC_RE.match(text))


def parse_heading(text: str) -> Heading | None:
    """解析正文中自带编号的标题；目录条目不算标题。"""
    if not text or is_toc_entry(text):
        return None
    match = HEADING_RE.match(text)
    if match is None:
        return None
    number = match.group(1)
    title = match.group(2).strip()
    return Heading(number=number, title=title, level=number.count(".") + 1)


def parse_toc(blocks: list[Block]) -> list[Heading]:
    """从目录区提取“编号 + 标题”的有序列表；目录结束即停止。"""
    headings: list[Heading] = []
    in_toc = False

    for block in blocks:
        text = block.text
        if TOC_TITLE_RE.match(text):
            in_toc = True
            continue
        if not in_toc:
            continue
        entry = _parse_toc_entry(text)
        if entry is not None:
            headings.append(entry)
        elif headings:
            break

    return headings


def _parse_toc_entry(text: str) -> Heading | None:
    """解析单条目录条目，取编号、标题与层级。"""
    match = TOC_ENTRY_RE.match(text)
    if match is None:
        return None
    number = match.group(1)
    title = match.group(2).strip()
    return Heading(number=number, title=title, level=number.count(".") + 1)


def _normalize_title(text: str) -> str:
    """去掉标题里的所有空白，便于目录与正文匹配。"""
    return re.sub(r"\s+", "", text)


def _matches_heading(text: str, expected: Heading) -> bool:
    """判断正文段落是否就是目录里的这个标题。

    支持两种写法：
    - 正文只有标题文字（Word 自动编号）
    - 正文自带编号（“1 范围”）
    """
    if _normalize_title(text) == _normalize_title(expected.title):
        return True
    literal = parse_heading(text)
    return (
        literal is not None
        and literal.number == expected.number
        and _normalize_title(literal.title) == _normalize_title(expected.title)
    )


def _walk(blocks: list[Block]) -> Iterator[tuple[Block, Section, Heading | None]]:
    """遍历正文块，产出块、所属章节、以及它是否为标题。

    目录区只用来构建标题索引，不产出块。有目录时只认目录里的标题，
    避免把“1. 本文一号标题……”这类编号列表误判成章节。
    """
    toc = parse_toc(blocks)
    toc_index = 0
    stack: list[Heading] = []
    in_toc = False

    for block in blocks:
        text = block.text

        if TOC_TITLE_RE.match(text):
            in_toc = True
            continue

        if in_toc:
            if is_toc_entry(text):
                continue
            in_toc = False

        heading: Heading | None = None

        if toc:
            if toc_index < len(toc) and _matches_heading(text, toc[toc_index]):
                heading = toc[toc_index]
                toc_index += 1
        else:
            heading = parse_heading(text)

        if heading is not None:
            while stack and stack[-1].level >= heading.level:
                stack.pop()
            stack.append(heading)

        section = Section(
            number=stack[-1].number if stack else "",
            title=stack[-1].title if stack else "",
            level=stack[-1].level if stack else 0,
            path=[f"{item.number} {item.title}" for item in stack],
        )
        yield block, section, heading


def iter_headings(blocks: list[Block]) -> Iterator[Heading]:
    """按顺序产出正文标题，自动跳过目录区。"""
    for _block, _section, heading in _walk(blocks):
        if heading is not None:
            yield heading


def assign_sections(blocks: list[Block]) -> Iterator[tuple[Block, Section]]:
    """为每个正文块标注所属章节，跳过目录标题与目录条目。"""
    for block, section, _heading in _walk(blocks):
        yield block, section


def section_path(section: Section) -> str:
    """把章节渲染成“1.2.3 标题”的形式。"""
    if section.path:
        return " / ".join(section.path)
    if section.number:
        return f"{section.number} {section.title}".strip()
    return ""


def truncate(text: str, limit: int = MAX_TEXT_LENGTH) -> str:
    """按长度截断文本，并在末尾标记已截断。"""
    if len(text) <= limit:
        return text
    marker = "…（已截断）"
    if limit <= len(marker):
        return marker[:limit]
    return text[: limit - len(marker)] + marker


def join_table_rows(rows: list[list[str]]) -> str:
    """把表格行渲染成“标签: 值”或“列 | 列”的文本。"""
    lines: list[str] = []
    for row in rows:
        if len(row) == 2:
            lines.append(f"{row[0]}: {row[1]}")
        else:
            lines.append(" | ".join(row))
    return "\n".join(lines)


def context_for(block: Block, section: Section) -> str:
    """返回候选的章节上下文，形如“章节：1 范围 / 1.1 标识”。"""
    _ = block  # 目前只用章节；保留 block 以便后续补充相邻标题
    path = section_path(section)
    return f"章节：{path}" if path else ""


@dataclass(slots=True)
class Profile:
    """某类文档的结构画像：字段别名与抽取来源。"""

    name: str
    unit_source: str = "table"
    element_source: str = "table"
    id_aliases: list[str] = field(default_factory=list)
    unit_fields: dict[str, list[str]] = field(default_factory=dict)
    element_fields: dict[str, list[str]] = field(default_factory=dict)
    id_patterns: list[str] = field(default_factory=list)
    expected_chapters: list[str] = field(default_factory=list)


def load_profile(name: str) -> Profile:
    """按名称加载内置文档画像。"""
    ...


def list_profiles() -> list[str]:
    """列出内置文档画像名称。"""
    ...


def detect_profile(blocks: list[Block]) -> tuple[Profile, float]:
    """根据文档结构猜测画像并给出置信度。"""
    ...


def match_field(labels: list[str], aliases: list[str]) -> int | None:
    """返回首个命中别名的标签下标。"""
    ...


def field_map(profile: Profile, labels: list[str]) -> dict[str, str]:
    """把标准字段名映射到表头中实际出现的标签。"""
    ...


def _is_data_table(header: list[str]) -> bool:
    """判断表头是否像数据库字段表。"""
    labels = " ".join(header)
    return "字段名称" in labels or "字段类型" in labels


def _is_constraint_table(header: list[str]) -> bool:
    """判断表头是否像技术选型/环境约束表。"""
    labels = " ".join(header)
    return any(key in labels for key in ("约束", "开发环境", "限制"))


def _make_table_candidate(
    block: Block,
    rows: list[list[str]],
    section: Section,
    role: DocRole,
    reason: str,
) -> CandidateBlock:
    """用一组表格行构造一个候选块。"""
    return CandidateBlock(
        block=Block(
            kind=BlockKind.TABLE,
            text=truncate(join_table_rows(rows)),
            index=block.index,
            table=rows,
            caption=block.caption,
        ),
        section=section,
        role=role,
        reason=reason,
        context=context_for(block, section),
    )


def split_blocks(
    blocks: list[Block],
    role: DocRole,
    profile: Profile,
) -> list[CandidateBlock]:
    """按表格或条款策略把块切成候选。

    - 段落：每个非空段落一个候选
    - 设计文档的字段表：整表一个候选
    - 设计文档的约束表：每行一个候选
    - 其余表格：≤8 行整表一个候选；>8 行按“表头 + 5 行”切块
    """
    _ = profile  # 文档画像在 B7 之后才会影响切块
    candidates: list[CandidateBlock] = []

    for block, section in assign_sections(blocks):
        if block.kind == BlockKind.PARAGRAPH:
            text = truncate(block.text)
            payload = replace(block, text=text) if text != block.text else block
            candidates.append(
                CandidateBlock(
                    block=payload,
                    section=section,
                    role=role,
                    reason="paragraph",
                    context=context_for(block, section),
                )
            )
            continue

        if block.kind != BlockKind.TABLE or not block.table:
            continue

        rows = block.table
        header = rows[0]

        if role == DocRole.DESIGN and _is_data_table(header):
            candidates.append(
                _make_table_candidate(block, rows, section, role, "table:data")
            )
            continue

        if role == DocRole.DESIGN and _is_constraint_table(header):
            for row_index, row in enumerate(rows[1:], start=1):
                candidates.append(
                    _make_table_candidate(
                        block,
                        [header, row],
                        section,
                        role,
                        f"table:constraint:{row_index}",
                    )
                )
            continue

        if len(rows) <= 8:
            candidates.append(
                _make_table_candidate(block, rows, section, role, "table:record")
            )
            continue

        data_rows = rows[1:]
        total = (len(data_rows) + 4) // 5
        for part_index in range(total):
            chunk = [header] + data_rows[part_index * 5 : (part_index + 1) * 5]
            candidates.append(
                _make_table_candidate(
                    block,
                    chunk,
                    section,
                    role,
                    f"table:chunk:{part_index + 1}/{total}",
                )
            )

    if len(candidates) > MAX_CANDIDATES:
        logger.warning(
            "候选数 %d 超过上限 %d，已截断", len(candidates), MAX_CANDIDATES
        )
        candidates = candidates[:MAX_CANDIDATES]

    return candidates
