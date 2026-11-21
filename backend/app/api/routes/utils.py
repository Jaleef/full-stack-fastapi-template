"""工具接口：健康检查与依赖诊断。"""

from fastapi import APIRouter

from app.api.deps import SessionDep
from app.core.dependencies import DepStatus, dependency_report

router = APIRouter(prefix="/utils", tags=["utils"])


@router.get("/health-check/")
async def health_check() -> bool:
    """返回服务健康状态。"""
    return True


@router.get("/dependencies/", response_model=list[DepStatus])
def dependencies(session: SessionDep) -> list[DepStatus]:
    """返回外部依赖的连通性与版本状态。"""
    return dependency_report(session)
