"""测试库夹具的烟雾测试。"""

from __future__ import annotations

from sqlalchemy import Engine, func, select, text
from sqlmodel import Session

from app.core.config import settings
from app.models import Analysis

APP_TABLES = {
    "analysis",
    "document",
    "parse_decision",
    "requirement_unit",
    "atomic_requirement",
    "atom_source",
    "design_element",
    "mapping",
    "finding",
    "llm_cache",
}


def test_test_database_is_separate() -> None:
    """测试库必须存在，且不能等于业务库。"""
    assert settings.TEST_DATABASE_URL
    assert str(settings.TEST_DATABASE_URL) != str(settings.DATABASE_URL)


def test_migrations_applied(test_engine: Engine) -> None:
    """测试库应已执行迁移并包含全部业务表。"""
    with test_engine.connect() as conn:
        version = conn.execute(
            text("select version_num from alembic_version")
        ).scalar()
        tables = {
            row[0]
            for row in conn.execute(
                text("select tablename from pg_tables where schemaname='public'")
            )
        }
    assert version is not None
    assert APP_TABLES <= tables


def test_session_roundtrip(session: Session) -> None:
    """测试会话可以写入业务表。"""
    session.add(Analysis(title="smoke"))
    session.commit()
    count = session.exec(select(func.count()).select_from(Analysis)).one()[0]
    assert count == 1


def test_session_starts_empty(session: Session) -> None:
    """上一个用例结束后，夹具应已清空业务表。"""
    count = session.exec(select(func.count()).select_from(Analysis)).one()[0]
    assert count == 0
