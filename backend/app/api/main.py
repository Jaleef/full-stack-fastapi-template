"""API v1 router assembly."""

from fastapi import APIRouter

from app.api.routes import analyses, findings, mappings, utils

api_router = APIRouter()
api_router.include_router(analyses.router)
api_router.include_router(findings.router)
api_router.include_router(mappings.router)
api_router.include_router(utils.router)
