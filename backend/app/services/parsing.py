"""章节识别、文档画像与候选块切分。"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field

from app.domain import Block, CandidateBlock, DocRole, Heading, Section

HEADING_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)[\.、]?\s+(\S.*?)\s*$")
TOC_RE = re.compile(r"^\s*(\S.*?)\s*\t\s*\d+\s*$")


def is_toc_entry(text: str) -> bool:
    """判断文本是否像目录条目。"""
    ...


def parse_heading(text: str) -> Heading | None:
    """解析编号标题，返回编号、标题和层级。"""
    ...


def iter_headings(blocks: list[Block]) -> Iterator[Heading]:
    """按顺序产出标题，自动跳过目录区。"""
    ...


def assign_sections(blocks: list[Block]) -> Iterator[tuple[Block, Section]]:
    """为每个块标注它所属的章节。"""
    ...


def section_path(section: Section) -> str:
    """把章节渲染成“1.2.3 标题”的形式。"""
    ...


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


def split_blocks(
    blocks: list[Block],
    role: DocRole,
    profile: Profile,
) -> list[CandidateBlock]:
    """按表格或条款策略把块切成候选。"""
    ...


def context_for(block: Block, section: Section) -> str:
    """拼装附着在候选上的章节上下文。"""
    ...


def truncate(text: str, limit: int) -> str:
    """按长度截断文本并标记已截断。"""
    ...


def join_table_rows(rows: list[list[str]]) -> str:
    """把表格行渲染成“标签: 值”的多行文本。"""
    ...
