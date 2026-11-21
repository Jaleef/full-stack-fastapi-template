"""检查外部依赖是否可用。

用法（在 backend 目录下）：

    uv run python scripts/check_deps.py

退出码：全部依赖可用为 0，否则为 1。
"""

from __future__ import annotations

import logging
import sys

from sqlmodel import Session

from app.core.db import engine
from app.core.dependencies import dependency_report

# Windows 控制台默认不是 UTF-8，显式切一下，避免中文详情乱码。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-5s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("check_deps")


def main() -> int:
    """探测数据库、pgvector、对话模型与向量化接口。"""
    with Session(engine) as session:
        statuses = dependency_report(session)

    all_ok = True
    for status in statuses:
        label = "OK" if status.ok else "FAIL"
        logger.info("%-11s %-4s %s", status.name, label, status.detail)
        all_ok = all_ok and status.ok

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
