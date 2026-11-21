"""覆盖率指标与最终结论。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel


class Metrics(BaseModel):
    """一次分析的聚合指标。"""

    unit_count: int = 0
    atom_count: int = 0
    element_count: int = 0
    atom_coverage: float = 0.0
    unit_coverage: float = 0.0
    element_support: float = 0.0
    pending_review: int = 0


def compute_metrics(
    units: Sequence[Any],
    atoms: Sequence[Any],
    elements: Sequence[Any],
    links: Sequence[Any],
) -> Metrics:
    """计算原子、单元与要素三个口径的覆盖率。"""
    ...


def final_verdict(metrics: Metrics, has_blocker: bool) -> str:
    """根据指标与阻断项给出最终结论。"""
    ...
