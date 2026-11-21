"""映射复核接口。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.api.deps import SessionDep
from app.models import AtomMapping

router = APIRouter(prefix="/mappings", tags=["mappings"])


@router.patch("/{mapping_id}", response_model=AtomMapping)
def review_mapping(
    session: SessionDep,
    mapping_id: uuid.UUID,
    review_status: str,
    review_note: str | None = None,
) -> AtomMapping:
    """接受、推翻或备注一条映射。"""
    ...
