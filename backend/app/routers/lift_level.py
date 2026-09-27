"""液位记录接口：按泵站编号追加历史液位/格栅记录，不覆盖旧记录。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.lift_level import LiftLevelService

router = APIRouter(prefix="/api/lift-level", tags=["液位记录"])

service = LiftLevelService()

LIST_FIELDS = ["泵站编号", "泵站名称", "集水池容积", "监测时间", "格栅状态", "液位高度", "泵站状态"]
STATUSES = ["正常运行", "高液位", "格栅堵塞", "停机"]


@router.get("", response_model=PageResult[dict])
def list_records(
    station_code: str | None = Query(default=None, description="按泵站编号检索"),
    status: str | None = Query(default=None, description="正常运行、高液位、格栅堵塞、停机"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按泵站编号与泵站状态过滤历史液位记录；记录只追加，列表按时间倒序。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = service.list_records(
        station_code=station_code, status=status, page=page, size=size
    )
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/stations/{station_code:path}", response_model=dict)
def get_station(station_code: str) -> dict:
    """按泵站编号带出台账信息（集水池容积、服务管网等），供登记液位记录时回填。"""
    station = service.lifts.get_by_code(station_code)
    if station is None:
        raise HTTPException(status_code=404, detail=f"泵站编号「{station_code}」在台账中不存在")
    return station


@router.get("/export")
def export_records() -> dict[str, Any]:
    """导出全部历史液位记录。"""
    items, total = service.list_records(page=1, size=10000)
    return {"module": "lift_level", "total": total, "items": items}


@router.get("/{record_id}", response_model=dict)
def get_record(record_id: int) -> dict:
    """读取单条历史液位记录；不存在时给出可读的错误说明。"""
    record = service.get_record(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"液位记录 {record_id} 不存在或已归档")
    return record


@router.post("", response_model=ActionResult)
def create_record(payload: EntryPayload) -> ActionResult:
    """登记一条液位记录：历史追加一条，并把最新值同步到泵站台账。"""
    record, missing = service.create_record(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段或校验未通过：{'、'.join(missing)}")
    return ActionResult(ok=True, message="液位记录已保存", entry=record)


@router.put("/{record_id}", response_model=ActionResult)
def update_record(record_id: int, payload: EntryPayload) -> ActionResult:
    """修正某条历史液位记录本身；其它历史记录保持原样，不被覆盖。"""
    record, message = service.update_record(record_id, payload.values)
    if record is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=record)
