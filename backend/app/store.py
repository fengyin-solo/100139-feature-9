"""数据仓库：启动时从本地数据文件加载，写入后立即落盘。

数据按业务模块分表存放在一份 JSON 文件里：首次启动没有文件时用示例数据
(SEED_ROWS) 初始化，之后所有增改都追加写入文件，进程重启（比如第二天再打开）
读到的仍是上次保存的内容，不会被示例数据覆盖。
真实项目里这里会换成数据库访问层；当前实现只依赖标准库，保证克隆下来就能起。
"""
from __future__ import annotations

import json
import os
import tempfile
from typing import Any

from app.seed import SEED_ROWS

# 持久化数据文件：允许通过环境变量换位置，默认放在后端 data 目录下。
DATA_PATH = os.environ.get(
    "LIFT_OPS_DATA_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "store.json"),
)


class Store:
    def __init__(self) -> None:
        self._tables: dict[str, list[dict[str, Any]]] = self._load()

    def _load(self) -> dict[str, list[dict[str, Any]]]:
        """优先读持久化文件；文件不存在时用示例数据初始化并立刻落盘。"""
        if os.path.exists(DATA_PATH):
            try:
                with open(DATA_PATH, encoding="utf-8") as handle:
                    data = json.load(handle)
                if isinstance(data, dict):
                    # 种子数据后续新增了模块时，已存在的数据文件也要把新表补齐。
                    tables = {name: [dict(row) for row in rows] for name, rows in data.items() if isinstance(rows, list)}
                    for name, rows in SEED_ROWS.items():
                        tables.setdefault(name, [dict(row) for row in rows])
                    return tables
            except (json.JSONDecodeError, OSError):
                # 数据文件损坏时回退到示例数据，避免服务整体起不来。
                pass
        tables = {name: [dict(row) for row in rows] for name, rows in SEED_ROWS.items()}
        self._tables = tables
        self.flush()
        return tables

    def flush(self) -> None:
        """把当前全量数据原子写入文件：先写临时文件再替换，避免写一半损坏。"""
        directory = os.path.dirname(DATA_PATH)
        os.makedirs(directory, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(prefix=".store-", suffix=".json", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(self._tables, handle, ensure_ascii=False, indent=2)
            os.replace(temp_path, DATA_PATH)
        except OSError:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

    def module_names(self) -> list[str]:
        return sorted(self._tables)

    def rows(self, module: str) -> list[dict[str, Any]]:
        return self._tables.setdefault(module, [])

    def find(self, module: str, entry_id: int) -> dict[str, Any] | None:
        for row in self.rows(module):
            if int(row.get("id", 0)) == entry_id:
                return row
        return None

    def next_id(self, module: str) -> int:
        return max((int(row.get("id", 0)) for row in self.rows(module)), default=0) + 1

    def overview(self) -> dict[str, object]:
        # 液位历史是提升泵站的附属表，不作为独立业务模块计入运营概览。
        hidden = {"lift_records"}
        modules: list[dict[str, object]] = []
        for name in self.module_names():
            if name in hidden:
                continue
            rows = self.rows(name)
            modules.append({
                "name": name,
                "created": len(rows),
                "pending": sum(1 for row in rows if row.get("pending")),
                "abnormal": sum(1 for row in rows if row.get("abnormal")),
            })
        cards = [
            {"label": "业务模块", "value": len(modules)},
            {"label": "今日新增", "value": sum(int(item["created"]) for item in modules)},
            {"label": "待处理", "value": sum(int(item["pending"]) for item in modules)},
            {"label": "异常量", "value": sum(int(item["abnormal"]) for item in modules)},
        ]
        return {"cards": cards, "modules": modules}


store = Store()
