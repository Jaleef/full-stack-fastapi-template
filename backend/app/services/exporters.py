"""报告导出。"""

from __future__ import annotations

import uuid

from sqlmodel import Session


def render_markdown(session: Session, analysis_id: uuid.UUID) -> str:
    """生成 Markdown 一致性报告。"""
    ...


def render_csv(session: Session, analysis_id: uuid.UUID) -> bytes:
    """生成带 UTF-8 BOM 的问题清单 CSV。"""
    ...


def safe_filename(name: str) -> str:
    """生成可用于下载的文件名。"""
    ...
