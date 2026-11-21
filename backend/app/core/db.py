"""数据库引擎与会话。"""

from collections.abc import Generator

from sqlmodel import Session, create_engine

from app.core.config import settings

engine = create_engine(
    str(settings.DATABASE_URL),
    pool_pre_ping=True,
    # 探针与接口都不该被不可达的数据库拖住；psycopg 支持 connect_timeout。
    connect_args={"connect_timeout": 5},
)


def get_session() -> Generator[Session]:
    """产出一个绑定应用引擎的数据库会话。"""
    with Session(engine) as session:
        yield session
