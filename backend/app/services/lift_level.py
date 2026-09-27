"""液位记录业务规则：每条记录只追加、不覆盖，液位高度与格栅状态挂在泵站编号上。

保存一条液位记录时：
1. 按「泵站编号」找到提升泵站台账，带出集水池容积等台账信息；
2. 记录本身存一份当次快照（含历史液位高度），后续新记录不会改它；
3. 台账上的当前液位高度/格栅状态同步为本次值，泵站状态随之推导，
   保证台账、液位记录、管网画面三处口径一致。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.services.lift import LiftService, derive_status
from app.store import store

MODULE = "lift_level"
REQUIRED_FIELDS = ["泵站编号", "格栅状态", "液位高度"]

# 历史记录允许回看修正的字段；泵站编号是关联键，不允许改挂到别的泵站。
EDITABLE_FIELDS = ["监测时间", "格栅状态", "液位高度", "备注"]


class LiftLevelService:
    def __init__(self) -> None:
        self.lifts = LiftService()

    # ---------- 查询 ----------
    def list_records(
        self,
        *,
        station_code: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = list(store.rows(MODULE))
        # 历史记录按时间倒序：最新登记的排前面，旧记录始终保留在后面。
        rows.sort(key=lambda row: str(row.get("监测时间") or ""), reverse=True)
        if station_code:
            rows = [row for row in rows if station_code in str(row.get("泵站编号", ""))]
        if status:
            rows = [row for row in rows if str(row.get("泵站状态") or "").strip() == status]
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def get_record(self, record_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, record_id)

    # ---------- 写入 ----------
    def create_record(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        code = str(values.get("泵站编号") or "").strip()
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing

        station = self.lifts.get_by_code(code)
        if station is None:
            return None, [f"泵站编号「{code}」在泵站台账中不存在，请先登记泵站"]

        level = str(values["液位高度"]).strip()
        grid = str(values["格栅状态"]).strip()
        observed_at = str(values.get("监测时间") or "").strip() or datetime.now().strftime("%Y-%m-%d %H:%M")
        status = derive_status(level, grid)

        # 历史快照：台账信息（含集水池容积）按泵站编号带出来，固定在这条记录上。
        record: dict[str, Any] = {
            "id": store.next_id(MODULE),
            "泵站编号": code,
            "泵站名称": station.get("泵站名称"),
            "集水池容积": station.get("集水池容积"),
            "服务管网": station.get("服务管网"),
            "监测时间": observed_at,
            "格栅状态": grid,
            "液位高度": level,
            "泵站状态": status,
            "备注": str(values.get("备注") or "").strip(),
        }
        store.rows(MODULE).append(record)

        # 台账同步成最新一次记录的现场值，状态由 service 统一推导。
        self.lifts.update_entry(
            int(station["id"]),
            {"格栅状态": grid, "液位高度": level, "泵站状态": status},
        )
        return record, []

    def update_record(
        self, record_id: int, values: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, str]:
        """只修正某一条历史记录自身；不删除、不改写其它历史记录。

        泵站编号不能改，保证液位高度与格栅状态始终挂在原来的泵站上。
        若该记录是泵站最新一条，台账当前值随之同步；否则台账保持最新记录的值。
        """
        record = store.find(MODULE, record_id)
        if record is None:
            return None, f"液位记录 {record_id} 不存在或已归档"
        if "泵站编号" in values and str(values["泵站编号"]).strip() != str(
            record.get("泵站编号") or ""
        ):
            return None, "历史液位记录不能改挂到其他泵站编号"

        for field in EDITABLE_FIELDS:
            if field in values:
                record[field] = values[field]
        record["泵站状态"] = derive_status(record.get("液位高度"), record.get("格栅状态"))

        station = self.lifts.get_by_code(str(record["泵站编号"]))
        latest = self._latest_record(str(record["泵站编号"]))
        if station is not None and latest is not None and int(latest["id"]) == record_id:
            self.lifts.update_entry(
                int(station["id"]),
                {
                    "格栅状态": record["格栅状态"],
                    "液位高度": record["液位高度"],
                    "泵站状态": record["泵站状态"],
                },
            )
        else:
            store.save()
        return record, "液位记录已保存，历史记录未被覆盖"

    def _latest_record(self, station_code: str) -> dict[str, Any] | None:
        records = [
            row
            for row in store.rows(MODULE)
            if str(row.get("泵站编号") or "").strip() == station_code
        ]
        if not records:
            return None
        return max(records, key=lambda row: str(row.get("监测时间") or ""))
