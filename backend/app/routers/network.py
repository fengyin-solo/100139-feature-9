"""管网画面接口：按服务管网聚合提升泵站，状态与泵站台账实时同源。"""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.services.network import NetworkService

router = APIRouter(prefix="/api/network", tags=["管网画面"])

service = NetworkService()


@router.get("")
def overview(
    keyword: str | None = Query(default=None, description="按服务管网或泵站编号检索"),
) -> dict:
    """管网画面：按管网分组展示各泵站的液位、格栅与泵站状态。"""
    return service.overview(keyword=keyword)
