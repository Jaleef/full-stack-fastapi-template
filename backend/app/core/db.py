"""数据库引擎与会话。"""

from collections.abc import Generator

from sqlmodel import Session, create_engine

from app.core.config import settings

engine = create_engine(str(settings.DATABASE_URL), pool_pre_ping=True)


def get_session() -> Generator[Session]:
    """产出一个绑定应用引擎的数据库会话。"""
    with Session(engine) as session:
        yield session
