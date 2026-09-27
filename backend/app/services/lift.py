"""提升泵站业务规则。

数据分两张表：
- lift：泵站台账，以「泵站编号」为业务主键，集水池容积等基础资料挂在这里；
- lift_records：历史液位记录，每条记录只通过「泵站编号」挂到对应泵站，
  填报一律追加、不改写旧记录；同一条记录可以再打开编辑，改的是它自己。

泵站状态不在任何页面单独保存，统一由 derive_status 根据停机标志和最新一条
液位记录推导，台账列表、液位记录列表、管网画面共用这一个口径，保证同步。
"""
from __future__ import annotations

from typing import Any

from app.store import store

MODULE = "lift"
RECORDS_MODULE = "lift_records"

# 台账基础字段（液位高度、格栅状态不在台账里，它们属于液位记录）。
STATION_FIELDS = ["泵站编号", "泵站名称", "集水池容积", "扬程", "服务管网"]
REQUIRED_FIELDS = ["泵站编号", "泵站名称", "集水池容积"]
RECORD_FIELDS = ["泵站编号", "记录时间", "液位高度", "格栅状态"]

STATUS_NORMAL = "正常运行"
STATUS_HIGH = "高液位"
STATUS_BLOCKED = "格栅堵塞"
STATUS_STOPPED = "停机"
STATUS_ORDER = [STATUS_NORMAL, STATUS_HIGH, STATUS_BLOCKED, STATUS_STOPPED]

GRID_NORMAL = "正常"
GRID_BLOCKED = "堵塞"
GRID_STATES = [GRID_NORMAL, GRID_BLOCKED]

# 液位达到高液位阈值（米）即判为高液位。
HIGH_LEVEL_THRESHOLD = 6.0

ACTION_RULES = {"启动清渣": STATUS_NORMAL, "排水处置": STATUS_NORMAL, "停机": STATUS_STOPPED}


def _to_level(value: Any) -> float | None:
    """把液位高度解析成数字；空值或无法解析时返回 None，不抛异常。"""
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class LiftService:
    # ---------- 内部工具 ----------

    def _find_station_by_code(self, code: str) -> dict[str, Any] | None:
        code = str(code or "").strip()
        for row in store.rows(MODULE):
            if str(row.get("泵站编号", "")).strip() == code:
                return row
        return None

    def _records_of(self, code: str) -> list[dict[str, Any]]:
        code = str(code or "").strip()
        return [row for row in store.rows(RECORDS_MODULE) if str(row.get("泵站编号", "")).strip() == code]

    def _latest_record(self, code: str) -> dict[str, Any] | None:
        records = self._records_of(code)
        if not records:
            return None
        # 记录时间相同时退回用 id，保证“最新一条”口径稳定。
        return max(records, key=lambda row: (str(row.get("记录时间", "")), int(row.get("id", 0))))

    def derive_status(self, station: dict[str, Any]) -> str:
        """泵站状态唯一推导口径：停机优先，其次格栅堵塞，再看液位高度。"""
        if station.get("stopped"):
            return STATUS_STOPPED
        latest = self._latest_record(station.get("泵站编号", ""))
        if latest is not None and str(latest.get("格栅状态", "")).strip() == GRID_BLOCKED:
            return STATUS_BLOCKED
        level = _to_level(latest.get("液位高度")) if latest is not None else None
        if level is not None and level >= HIGH_LEVEL_THRESHOLD:
            return STATUS_HIGH
        return STATUS_NORMAL

    def _recalc(self, station: dict[str, Any]) -> dict[str, Any]:
        """按统一口径回写台账上的状态快照（筛选与运营概览都读这份）。"""
        status = self.derive_status(station)
        station["status"] = status
        station["pending"] = status != STATUS_STOPPED
        station["abnormal"] = status in (STATUS_HIGH, STATUS_BLOCKED)
        return station

    def recalc_all(self) -> None:
        for station in store.rows(MODULE):
            self._recalc(station)

    def _station_view(self, station: dict[str, Any]) -> dict[str, Any]:
        """台账视图：带出最新液位/格栅，泵站状态用统一口径。"""
        view = {field: station.get(field) for field in STATION_FIELDS}
        view["id"] = station["id"]
        latest = self._latest_record(station.get("泵站编号", ""))
        view["液位高度"] = latest.get("液位高度") if latest else None
        view["格栅状态"] = latest.get("格栅状态") if latest else None
        view["记录时间"] = latest.get("记录时间") if latest else None
        view["泵站状态"] = self.derive_status(station)
        return view

    def _record_view(self, record: dict[str, Any]) -> dict[str, Any]:
        """液位记录视图：状态不落在记录上，实时取所属泵站的统一状态。"""
        view = {field: record.get(field) for field in RECORD_FIELDS}
        view["id"] = record["id"]
        station = self._find_station_by_code(str(record.get("泵站编号", "")))
        view["泵站名称"] = station.get("泵站名称") if station else None
        view["集水池容积"] = station.get("集水池容积") if station else None
        view["泵站状态"] = self.derive_status(station) if station else None
        return view

    # ---------- 查询 ----------

    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        views = [self._station_view(station) for station in store.rows(MODULE)]
        if keyword:
            views = [row for row in views if keyword in str(row.get("泵站编号", ""))]
        if status:
            views = [row for row in views if row.get("泵站状态") == status]
        total = len(views)
        start = max(page - 1, 0) * size
        return views[start:start + size], total

    def list_records(
        self,
        *,
        station_code: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        # 历史记录按时间倒序：新填报追加在后面，查看时最新的在最前。
        records = sorted(
            store.rows(RECORDS_MODULE),
            key=lambda row: (str(row.get("记录时间", "")), int(row.get("id", 0))),
            reverse=True,
        )
        if station_code:
            code = station_code.strip()
            records = [row for row in records if code in str(row.get("泵站编号", ""))]
        views = [self._record_view(record) for record in records]
        if status:
            views = [row for row in views if row.get("泵站状态") == status]
        total = len(views)
        start = max(page - 1, 0) * size
        return views[start:start + size], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        station = store.find(MODULE, entry_id)
        return self._station_view(station) if station else None

    def get_record(self, record_id: int) -> dict[str, Any] | None:
        record = store.find(RECORDS_MODULE, record_id)
        return self._record_view(record) if record else None

    def station_options(self) -> list[dict[str, Any]]:
        """填报下拉：给出泵站编号、名称与集水池容积，供前端按编号带出容积。"""
        return [
            {"泵站编号": row.get("泵站编号"), "泵站名称": row.get("泵站名称"), "集水池容积": row.get("集水池容积")}
            for row in store.rows(MODULE)
        ]

    def status_summary(self) -> list[dict[str, Any]]:
        """各状态泵站数量，台账/记录/管网三个入口共用同一份统计。"""
        counts = {name: 0 for name in STATUS_ORDER}
        for station in store.rows(MODULE):
            counts[self.derive_status(station)] += 1
        return [{"label": name, "value": counts[name]} for name in STATUS_ORDER]

    def network_view(self) -> list[dict[str, Any]]:
        """管网画面：按服务管网分组，展示挂在该管网上的泵站实时状态。"""
        groups: dict[str, list[dict[str, Any]]] = {}
        for station in store.rows(MODULE):
            view = self._station_view(station)
            network = str(station.get("服务管网") or "未分配管网").strip() or "未分配管网"
            groups.setdefault(network, []).append(view)
        return [
            {"服务管网": network, "泵站数量": len(stations), "泵站": stations}
            for network, stations in sorted(groups.items())
        ]

    # ---------- 台账登记 / 编辑 ----------

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str] | str]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        code = str(values.get("泵站编号")).strip()
        if self._find_station_by_code(code):
            return None, f"泵站编号 {code} 已存在，请直接编辑该泵站"
        station: dict[str, Any] = {"id": store.next_id(MODULE), "stopped": False}
        for field in STATION_FIELDS:
            station[field] = str(values.get(field)).strip() if values.get(field) is not None else None
        store.rows(MODULE).append(station)
        self._recalc(station)
        store.flush()
        return self._station_view(station), []

    def update_entry(self, entry_id: int, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        station = store.find(MODULE, entry_id)
        if station is None:
            return None, f"提升泵站 {entry_id} 不存在或已归档"
        new_code = values.get("泵站编号")
        if new_code is not None and str(new_code).strip() != str(station.get("泵站编号", "")):
            other = self._find_station_by_code(str(new_code).strip())
            if other is not None and int(other.get("id", 0)) != entry_id:
                return None, f"泵站编号 {new_code} 已被其他台账占用"
        for field in STATION_FIELDS:
            if values.get(field) is not None:
                station[field] = str(values.get(field)).strip()
        self._recalc(station)
        store.flush()
        return self._station_view(station), ""

    # ---------- 液位记录填报 / 编辑 ----------

    def _validate_record(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        code = str(values.get("泵站编号") or "").strip()
        if not code:
            return None, "请先选择泵站编号"
        if self._find_station_by_code(code) is None:
            return None, f"泵站编号 {code} 不在泵站台账中，请先登记泵站"
        level = _to_level(values.get("液位高度"))
        if level is None:
            return None, "液位高度需填写为数字"
        if level < 0:
            return None, "液位高度不能为负数"
        grid = str(values.get("格栅状态") or "").strip()
        if grid not in GRID_STATES:
            return None, f"格栅状态只能是：{'、'.join(GRID_STATES)}"
        record_time = str(values.get("记录时间") or "").strip()
        if not record_time:
            return None, "请填写记录时间"
        return {
            "泵站编号": code,
            "记录时间": record_time,
            "液位高度": round(level, 2),
            "格栅状态": grid,
        }, ""

    def create_record(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        data, message = self._validate_record(values)
        if data is None:
            return None, message
        # 始终追加新记录，绝不动旧记录，历史液位不会被覆盖。
        data = {"id": store.next_id(RECORDS_MODULE), **data}
        store.rows(RECORDS_MODULE).append(data)
        station = self._find_station_by_code(data["泵站编号"])
        if station is not None:
            self._recalc(station)
        store.flush()
        return self._record_view(data), ""

    def update_record(self, record_id: int, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        record = store.find(RECORDS_MODULE, record_id)
        if record is None:
            return None, f"液位记录 {record_id} 不存在或已归档"
        # 编辑的是这一条记录本身；泵站编号保持挂在原泵站上，不允许借编辑改挂。
        merged = {
            "泵站编号": record.get("泵站编号"),
            "记录时间": values.get("记录时间", record.get("记录时间")),
            "液位高度": values.get("液位高度", record.get("液位高度")),
            "格栅状态": values.get("格栅状态", record.get("格栅状态")),
        }
        data, message = self._validate_record(merged)
        if data is None:
            return None, message
        record.update(data)
        station = self._find_station_by_code(record["泵站编号"])
        if station is not None:
            self._recalc(station)
        store.flush()
        return self._record_view(record), ""

    # ---------- 动作 ----------

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        station = store.find(MODULE, entry_id)
        if station is None:
            return None, f"提升泵站 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于提升泵站可执行范围"
        target = ACTION_RULES[action]
        station["stopped"] = target == STATUS_STOPPED
        self._recalc(station)
        store.flush()
        return self._station_view(station), f"提升泵站已{action}"


# 启动时把种子数据的状态按统一口径校准一遍（含历史液位推导出的高液位/堵塞）。
LiftService().recalc_all()
store.flush()
