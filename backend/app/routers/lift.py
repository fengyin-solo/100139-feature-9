"""提升泵站接口：泵站台账、历史液位记录与管网画面状态共用一套数据。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.lift import STATUS_ORDER, LiftService

router = APIRouter(prefix="/api/lift", tags=["提升泵站"])

service = LiftService()

# 台账与液位记录的展示列；液位高度、格栅状态只存在于液位记录上。
LIST_FIELDS = ["泵站编号", "泵站名称", "集水池容积", "扬程", "服务管网", "格栅状态", "液位高度", "泵站状态"]
RECORD_FIELDS = ["泵站编号", "泵站名称", "记录时间", "液位高度", "格栅状态", "泵站状态"]


# ---------- 泵站台账 ----------

@router.get("", response_model=PageResult[dict])
def list_entries(
    keyword: str | None = Query(default=None, description="按泵站编号检索"),
    status: str | None = Query(default=None, description="正常运行、高液位、格栅堵塞、停机"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按泵站编号与状态过滤提升泵站列表；没有数据时返回空页，不报错。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = service.list_entries(keyword=keyword, status=status, page=page, size=size)
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/stations/options")
def station_options() -> list[dict[str, Any]]:
    """填报液位时的泵站编号选项，同时带出集水池容积。"""
    return service.station_options()


@router.get("/status-summary")
def status_summary() -> list[dict[str, Any]]:
    """泵站状态分组统计：台账、液位记录、管网画面三处共用。"""
    return service.status_summary()


@router.get("/network")
def network_view() -> dict[str, Any]:
    """管网画面：按服务管网分组查看各泵站的实时状态。"""
    groups = service.network_view()
    return {"groups": groups, "total": sum(group["泵站数量"] for group in groups)}


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条提升泵站台账，缺字段或编号重复时说明原因而不是静默丢弃。"""
    entry, problem = service.create_entry(payload.values)
    if entry is None:
        if isinstance(problem, list):
            return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(problem)}")
        return ActionResult(ok=False, message=problem)
    return ActionResult(ok=True, message="提升泵站已登记", entry=entry)


# ---------- 历史液位记录 ----------

@router.get("/records", response_model=PageResult[dict])
def list_records(
    station: str | None = Query(default=None, description="按泵站编号过滤历史记录"),
    status: str | None = Query(default=None, description="按泵站当前状态过滤"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """历史液位记录：只追加不改写，按记录时间倒序返回。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = service.list_records(station_code=station, status=status, page=page, size=size)
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/records/{record_id}", response_model=dict)
def get_record(record_id: int) -> dict:
    """再次打开一条历史记录时读取它自己的内容，不会返回成别的记录。"""
    record = service.get_record(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"液位记录 {record_id} 不存在或已归档")
    return record


@router.post("/records", response_model=ActionResult)
def create_record(payload: EntryPayload) -> ActionResult:
    """填报一条液位记录：校验泵站编号后追加，新记录不覆盖任何历史记录。"""
    entry, message = service.create_record(payload.values)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message="液位记录已保存", entry=entry)


@router.put("/records/{record_id}", response_model=ActionResult)
def update_record(record_id: int, payload: EntryPayload) -> ActionResult:
    """编辑已保存的液位记录：只改这一条，保存后再次打开仍是改过的内容。"""
    entry, message = service.update_record(record_id, payload.values)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message="液位记录已更新", entry=entry)


# ---------- 单条台账（通配路径放最后，避免吃掉 /records、/network 等） ----------

@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条提升泵站明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"提升泵站 {entry_id} 不存在或已归档")
    return entry


@router.put("/{entry_id}", response_model=ActionResult)
def update_entry(entry_id: int, payload: EntryPayload) -> ActionResult:
    """编辑泵站台账（集水池容积等基础资料），按记录 id 更新并落盘。"""
    entry, message = service.update_entry(entry_id, payload.values)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message="提升泵站台账已更新", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """对单条提升泵站执行启动清渣、排水处置、停机；不允许的动作会被拦下。"""
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)


@router.get("/export/all")
def export_entries() -> dict[str, Any]:
    """导出提升泵站全量数据：台账与历史液位记录一起导出。"""
    stations, station_total = service.list_entries(page=1, size=10000)
    records, record_total = service.list_records(page=1, size=10000)
    return {
        "module": "lift",
        "total": station_total,
        "items": stations,
        "records_total": record_total,
        "records": records,
    }
