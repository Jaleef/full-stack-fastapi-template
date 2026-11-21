"""确定性一致性规则。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.domain import Dimension, Severity


@dataclass(slots=True)
class Rule:
    """一条确定性规则。"""

    code: str
    dimension: Dimension
    severity: Severity
    func: Callable[[Any], list[Any]]


RULES: list[Rule] = []


def run_rules(context: Any) -> list[Any]:
    """执行全部规则并返回问题列表。"""
    ...


def check_unit_id_duplicates(context: Any) -> list[Any]:
    """检查需求编号重复。"""
    ...


def check_parent_self(context: Any) -> list[Any]:
    """检查父需求编号指向自身。"""
    ...


def check_parent_missing(context: Any) -> list[Any]:
    """检查父需求编号不存在。"""
    ...


def check_parent_cross(context: Any) -> list[Any]:
    """检查父需求跨域或前向引用。"""
    ...


def check_empty_sections(context: Any) -> list[Any]:
    """检查有标题但没有需求单元的章节。"""
    ...


def check_missing_fields(context: Any) -> list[Any]:
    """检查设计要素缺少关键字段。"""
    ...


def check_element_code_duplicates(context: Any) -> list[Any]:
    """检查设计要素编号重复。"""
    ...


def check_caption_mismatch(context: Any) -> list[Any]:
    """检查表题与要素名称或描述不一致。"""
    ...


def check_version_refs(context: Any) -> list[Any]:
    """检查引用文档版本与实际版本不一致。"""
    ...


def check_constraints(context: Any) -> list[Any]:
    """检查技术选型或环境约束冲突。"""
    ...


def check_term_drift(context: Any) -> list[Any]:
    """检查同一实体使用了不同名称。"""
    ...


def check_placeholders(context: Any) -> list[Any]:
    """检查文档中残留的 XX 占位符。"""
    ...


def check_perf_placeholder(context: Any) -> list[Any]:
    """检查设计性能字段仍为占位符。"""
    ...


def check_perf_mismatch(context: Any) -> list[Any]:
    """检查需求与设计的性能指标不一致。"""
    ...


def check_data_tables_missing(context: Any) -> list[Any]:
    """检查需求中的数据表在设计里缺失。"""
    ...
