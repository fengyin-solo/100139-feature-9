"""提升泵站业务规则：台账维护、液位/格栅编辑、状态推导与筛选口径都收在这里。

口径约定：
- 「泵站状态」是唯一对外状态，内部 ``status`` 永远与其保持一致，
  台账、液位记录、管网画面三处都读这一份，不再出现两个入口结论不一致。
- 液位高度、格栅状态只属于某一个「泵站编号」，编辑直接更新该泵站台账，
  历史液位记录由 lift_level 模块按记录追加保存，不覆盖旧记录。
"""
from __future__ import annotations

from typing import Any

from app.store import store

MODULE = "lift"
REQUIRED_FIELDS = ["泵站编号", "泵站名称", "集水池容积"]
# 台账上允许编辑的业务字段；泵站编号是关联键，单独处理。
EDITABLE_FIELDS = ["泵站名称", "集水池容积", "扬程", "服务管网", "格栅状态", "液位高度", "泵站状态"]

STATUS_ORDER = ["正常运行", "高液位", "格栅堵塞", "停机"]
# 动作直接给出的目标状态；格栅/液位联动在 _apply_status 里统一兜底。
ACTION_RULES = {"启动清渣": "正常运行", "排水处置": "正常运行", "停机": "停机"}
NEGATIVE_ACTIONS = []

# 液位高度达到该值（米）判为高液位。
HIGH_LEVEL = 5.0
GRID_BLOCKED = "堵塞"
GRID_OK = "通畅"


def _to_float(value: Any) -> float | None:
    """尽量把液位高度解析成数值；空值或非数值返回 None，不当成 0 参与判断。"""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def derive_status(level: Any, grid: Any, stopped: bool = False) -> str:
    """按格栅状态优先、其次液位的口径推导泵站状态。

    格栅堵塞在现场需要优先清渣，所以优先级高于高液位；停机由动作显式指定。
    """
    if stopped:
        return "停机"
    if str(grid or "").strip() == GRID_BLOCKED:
        return "格栅堵塞"
    height = _to_float(level)
    if height is not None and height >= HIGH_LEVEL:
        return "高液位"
    return "正常运行"


class LiftService:
    # ---------- 查询 ----------
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("泵站编号", ""))]
        if status:
            # 状态分组只认真正的「泵站状态」，内部 status 字段与其始终同源。
            rows = [row for row in rows if str(row.get("泵站状态") or "").strip() == status]
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)

    def get_by_code(self, station_code: str) -> dict[str, Any] | None:
        """按泵站编号取台账，液位记录登记时用它带出集水池容积等台账信息。"""
        code = str(station_code or "").strip()
        if not code:
            return None
        for row in store.rows(MODULE):
            if str(row.get("泵站编号") or "").strip() == code:
                return row
        return None

    # ---------- 写入 ----------
    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        code = str(values["泵站编号"]).strip()
        if self.get_by_code(code) is not None:
            return None, [f"泵站编号「{code}」已存在，请勿重复登记"]
        entry: dict[str, Any] = {"id": store.next_id(MODULE)}
        entry["泵站编号"] = code
        for field in EDITABLE_FIELDS:
            entry[field] = values.get(field)
        # 新台账补齐格栅/液位缺省，再按现场数据推导状态。
        entry.setdefault("格栅状态", GRID_OK)
        entry.setdefault("液位高度", "")
        self._apply_status(entry, stopped=False)
        store.save()
        return entry, []

    def update_entry(
        self, entry_id: int, values: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, str]:
        """编辑泵站台账（含液位高度、格栅状态），保存后立即落盘。

        改过的记录再次打开仍是改过的那一份：这里直接更新同一行并持久化。
        """
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"提升泵站 {entry_id} 不存在或已归档"

        new_code = values.get("泵站编号")
        if new_code is not None and str(new_code).strip() and str(new_code).strip() != str(
            entry.get("泵站编号") or ""
        ):
            other = self.get_by_code(str(new_code).strip())
            if other is not None and int(other.get("id", 0)) != entry_id:
                return None, f"泵站编号「{str(new_code).strip()}」已被其他泵站占用"
            entry["泵站编号"] = str(new_code).strip()

        for field in EDITABLE_FIELDS:
            if field in values:
                entry[field] = values[field]

        stopped = str(entry.get("泵站状态") or "").strip() == "停机"
        self._apply_status(entry, stopped=stopped)
        store.save()
        return entry, "提升泵站已保存"

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"提升泵站 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于提升泵站可执行范围"
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        if target == "停机":
            self._apply_status(entry, stopped=True)
        else:
            # 启动清渣 / 排水处置意味着恢复运行：格栅清通、按当前液位重新判状态。
            if action == "启动清渣":
                entry["格栅状态"] = GRID_OK
            self._apply_status(entry, stopped=False)
        store.save()
        return entry, f"提升泵站已{action}"

    # ---------- 内部口径 ----------
    def _apply_status(self, entry: dict[str, Any], *, stopped: bool) -> None:
        """把泵站状态、内部 status、看板用的 pending/abnormal 一次同步到位。"""
        status = derive_status(entry.get("液位高度"), entry.get("格栅状态"), stopped=stopped)
        entry["泵站状态"] = status
        entry["status"] = status
        entry["pending"] = status != "停机"
        entry["abnormal"] = status in ("高液位", "格栅堵塞")
