# 污水处理厂工艺管理平台

面向污水处理厂进水调度、工艺运行、加药优化、污泥脱水、出水监控与药剂耗材的工艺管理后台。

这是一个前后端分离的管理平台：前端 Vue 3 + Vite + TypeScript，后端 FastAPI（Python）。
两边各自独立启动，前端 dev server 已关掉自动打开页面，启动后按终端打印的地址手工打开。

## 目录结构

```text
.
├── frontend/                 Vue 3 + Vite + TypeScript 前端
│   ├── src/views/            每个业务模块一个页面
│   ├── src/api/              统一请求封装
│   ├── src/stores/           会话与筛选状态
│   └── vite.config.ts        dev server 配置（open: false）
├── backend/                  FastAPI（Python） 后端
│   ├── app/routers/          每个业务模块一组接口
│   ├── app/services/         业务规则与状态流转
│   └── app/store.py          内存数据仓库与示例数据
├── .gitignore
└── docker-compose.yml
```

## 启动

### 后端

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
./run.sh
```

健康检查：`curl http://127.0.0.1:8000/api/health`

### 前端

```bash
cd frontend
npm install
npm run dev
```

前端默认监听 `http://127.0.0.1:5173/`，dev server 不会自动打开浏览器，
需要自己访问。`/api` 由 vite 代理到后端 `http://127.0.0.1:8000`。

## 业务模块

| 模块 | 目录 | 业务对象 | 主要字段 |
| --- | --- | --- | --- |
| 厂站信息 | `plank` | 污水处理厂 | 厂站编号、厂站名称、设计规模 |
| 进水监控 | `inflow` | 进水记录 | 记录编号、所属厂站、监测时间 |
| 曝气控制 | `aeration` | 曝气区段 | 区段编号、所属厂站、溶解氧目标 |
| 加药管理 | `chemical` | 加药方案 | 方案编号、药剂名称、加药点位 |
| 沉淀池管理 | `sediment` | 沉淀池 | 池编号、所属厂站、池容 |
| 污泥脱水 | `sludge` | 脱水机组 | 机组编号、所属厂站、机组类型 |
| 出水监测 | `effluent` | 出水记录 | 记录编号、所属厂站、监测时间 |
| 化验分析 | `labtest` | 化验报告 | 报告编号、取样点位、化验项目 |
| 化验药剂 | `reagent` | 化验药剂 | 药剂编号、药剂名称、规格等级 |
| 设备维保 | `equip` | 维保记录 | 记录编号、设备名称、维保类型 |
| 泵站运行 | `pump` | 水泵机组 | 机组编号、所属厂站、水泵型号 |
| 能耗管理 | `power` | 能耗记录 | 记录编号、所属厂站、统计周期 |
| 管网巡查 | `pipe` | 管网巡查 | 巡查编号、巡查路段、巡查人员 |
| 提升泵站 | `lift` | 提升泵站 + 历史液位记录 | 泵站编号、泵站名称、集水池容积、液位高度、格栅状态 |
| 仪表校准 | `meter` | 仪表 | 仪表编号、仪表名称、安装位置 |
| 水量调度 | `dispatch2` | 调度指令 | 调度编号、调度类型、来源厂站 |
| 雨污调控 | `storm` | 雨水调控 | 调控编号、所属厂站、降雨强度 |
| 污染源溯源 | `pollutant` | 溯源记录 | 溯源编号、异常厂站、异常指标 |
| 药剂耗材 | `material` | 耗材 | 耗材编号、耗材名称、规格型号 |
| 排污许可 | `license` | 排污许可证 | 证照编号、持证单位、许可排放量 |

## 约定

- 每个模块的前端页面在 `frontend/src/views/<模块>/index.vue`，后端接口在
  `backend/app/routers/<模块>.py`，业务规则在 `backend/app/services/<模块>.py`。
- 列表接口统一返回 `{ items, total, page, size }`，动作接口统一返回 `{ ok, message }`。
- 状态流转只允许在 `app/services` 里改，路由层不做业务判断。

## 数据持久化

数据保存在后端的 `backend/data/store.json`（可用环境变量 `LIFT_OPS_DATA_PATH` 改位置）：
首次启动用示例数据初始化，之后所有新增、编辑、动作都会立即原子落盘，进程重启后
读到的仍是上次保存的内容。`backend/data/` 已加入 `.gitignore`，删除该目录即可恢复示例数据。

### 提升泵站模块的数据口径

- **泵站台账**（`lift` 表）以「泵站编号」为业务主键，集水池容积、扬程、服务管网等
  基础资料挂在台账上；液位高度、格栅状态不属于台账。
- **历史液位记录**（`lift_records` 表）每条只通过「泵站编号」挂到对应泵站，填报一律
  追加、不改写旧记录；同一条记录可再次打开编辑（`PUT /api/lift/records/{id}`），改的是它自己。
- **泵站状态**不保存在任何页面，统一由最新一条液位记录按
  `停机 > 格栅堵塞 > 高液位(≥6米) > 正常运行` 推导；泵站台账、历史液位记录、管网画面
  （`GET /api/lift/network`，管网巡查页底部展示）三处共用同一口径。
