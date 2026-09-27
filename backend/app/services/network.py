"""管网画面业务规则：按服务管网把提升泵站聚合到同一张画面上。

画面上的每个泵站状态都读取提升泵站台账的「泵站状态」——与台账、液位记录
同源，不单独存一份，因此任何一处编辑后管网画面看到的结论始终一致。
"""
from __future__ import annotations

from typing import Any

from app.store import store

LIFT_MODULE = "lift"


class NetworkService:
    def overview(self, *, keyword: str | None = None) -> dict[str, Any]:
        stations = store.rows(LIFT_MODULE)
        networks: dict[str, dict[str, Any]] = {}

        for station in stations:
            net_name = str(station.get("服务管网") or "").strip() or "未分配管网"
            bucket = networks.setdefault(
                net_name,
                {"服务管网": net_name, "泵站数量": 0, "泵站": []},
            )
            bucket["泵站数量"] += 1
            bucket["泵站"].append(
                {
                    "泵站编号": station.get("泵站编号"),
                    "泵站名称": station.get("泵站名称"),
                    "服务管网": net_name,
                    "集水池容积": station.get("集水池容积"),
                    "液位高度": station.get("液位高度"),
                    "格栅状态": station.get("格栅状态"),
                    "泵站状态": station.get("泵站状态"),
                }
            )

        items = list(networks.values())
        if keyword:
            items = [item for item in items if keyword in item["服务管网"]]
            # 同步过滤每个管网下命中的泵站。
            for item in items:
                item["泵站"] = [
                    station
                    for station in item["泵站"]
                    if keyword in str(station.get("服务管网") or "")
                    or keyword in str(station.get("泵站编号") or "")
                ]

        status_count = {"正常运行": 0, "高液位": 0, "格栅堵塞": 0, "停机": 0}
        for station in stations:
            state = str(station.get("泵站状态") or "").strip()
            if state in status_count:
                status_count[state] += 1

        return {
            "networks": sorted(items, key=lambda item: item["服务管网"]),
            "total": len(stations),
            "status_count": status_count,
        }
