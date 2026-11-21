"""问题状态接口。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.api.deps import SessionDep
from app.models import Finding

router = APIRouter(prefix="/findings", tags=["findings"])


@router.patch("/{finding_id}", response_model=Finding)
def update_finding(
    session: SessionDep,
    finding_id: uuid.UUID,
    status: str,
    note: str | None = None,
) -> Finding:
    """更新问题的处理状态或复核备注。"""
    ...
