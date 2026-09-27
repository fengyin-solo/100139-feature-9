"""文件持久化数据仓库：给每个业务模块准备一份可筛选、可流转的数据。

数据落盘在后端运行目录下的 ``data/store.json``（可用环境变量
``LIFT_PLATFORM_DATA_FILE`` 覆盖路径），服务重启后仍然读回改过的内容；
首次启动没有数据文件时，用 ``app.seed`` 里的示例数据初始化并立刻落盘。

写文件采用「写临时文件再原子替换」，避免写到一半进程退出把数据截坏。
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

from app.seed import SEED_ROWS

# 数据文件默认放在后端根目录（本文件向上两级）的 data/ 下，可用环境变量覆盖。
_DEFAULT_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "store.json"


class Store:
    def __init__(self, data_file: str | os.PathLike[str] | None = None) -> None:
        path = os.environ.get("LIFT_PLATFORM_DATA_FILE") or data_file
        self._data_file = Path(path) if path else _DEFAULT_DATA_FILE
        self._lock = threading.RLock()
        self._tables: dict[str, list[dict[str, Any]]] = self._load()

    # ---------- 持久化 ----------
    def _load(self) -> dict[str, list[dict[str, Any]]]:
        if self._data_file.exists():
            try:
                with self._data_file.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if isinstance(data, dict):
                    return {
                        name: [dict(row) for row in rows]
                        for name, rows in data.items()
                        if isinstance(rows, list)
                    }
            except (json.JSONDecodeError, OSError):
                # 数据文件损坏时退回示例数据，至少保证服务能起得来。
                pass
        tables = {name: [dict(row) for row in rows] for name, rows in SEED_ROWS.items()}
        self._persist(tables)
        return tables

    def _persist(self, tables: dict[str, list[dict[str, Any]]] | None = None) -> None:
        payload = tables if tables is not None else self._tables
        self._data_file.parent.mkdir(parents=True, exist_ok=True)
        # 同目录临时文件 + os.replace，保证落盘是原子的。
        fd, tmp_name = tempfile.mkstemp(
            prefix=self._data_file.name, suffix=".tmp", dir=self._data_file.parent
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
            os.replace(tmp_name, self._data_file)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    def save(self) -> None:
        """业务层改完数据后调用，把当前全量数据刷到磁盘。"""
        with self._lock:
            self._persist()

    # ---------- 读写 ----------
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
        modules: list[dict[str, object]] = []
        for name in self.module_names():
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
