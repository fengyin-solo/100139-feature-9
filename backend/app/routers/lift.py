"""提升泵站接口：维护提升泵站台账，覆盖登记、编辑保存与启动清渣、排水处置、停机等动作。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.lift import LiftService

router = APIRouter(prefix="/api/lift", tags=["提升泵站"])

service = LiftService()

LIST_FIELDS = ["泵站编号", "泵站名称", "集水池容积", "扬程", "服务管网", "格栅状态", "液位高度", "泵站状态"]
STATUSES = ["正常运行", "高液位", "格栅堵塞", "停机"]


@router.get("", response_model=PageResult[dict])
def list_entries(
    keyword: str | None = Query(default=None, description="按泵站编号检索"),
    status: str | None = Query(default=None, description="正常运行、高液位、格栅堵塞、停机"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按泵站编号与泵站状态过滤提升泵站列表；没有数据时返回空页，不报错。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = service.list_entries(keyword=keyword, status=status, page=page, size=size)
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/export")
def export_entries() -> dict[str, Any]:
    """导出提升泵站清单：返回当前过滤条件下的全量数据。"""
    items, total = service.list_entries(page=1, size=10000)
    return {"module": "lift", "total": total, "items": items}


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条提升泵站明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"提升泵站 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条提升泵站，缺字段时说明原因而不是静默丢弃。"""
    entry, missing = service.create_entry(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段或校验未通过：{'、'.join(missing)}")
    return ActionResult(ok=True, message="提升泵站已登记", entry=entry)


@router.put("/{entry_id}", response_model=ActionResult)
def update_entry(entry_id: int, payload: EntryPayload) -> ActionResult:
    """保存提升泵站编辑结果（液位高度、格栅状态等直接挂在泵站编号上）。

    每次保存都是更新同一条台账并落盘，重新打开读到的仍是改过的内容。
    """
    entry, message = service.update_entry(entry_id, payload.values)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """对单条提升泵站执行启动清渣、排水处置、停机；不允许的动作会被拦下并说明原因。"""
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)
