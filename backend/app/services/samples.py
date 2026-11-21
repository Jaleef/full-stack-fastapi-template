"""内置样例文档定位。"""

from __future__ import annotations

from pathlib import Path


def sample_pair() -> tuple[Path, Path] | None:
    """返回内置的需求与设计样例路径。"""
    ...


def ensure_sample_docs() -> None:
    """确认两份样例文档存在，否则抛出异常。"""
    ...
