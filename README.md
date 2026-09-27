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
│   └── app/store.py          JSON 文件持久化数据仓库（backend/data/store.json）
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
| 提升泵站 | `lift` | 提升泵站 | 泵站编号、泵站名称、集水池容积、液位高度、格栅状态、泵站状态 |
| 液位记录 | `lift_level` | 提升泵站历史液位记录 | 泵站编号、监测时间、液位高度、格栅状态（只追加不覆盖） |
| 管网画面 | `network` | 服务管网与泵站聚合画面 | 服务管网、泵站编号、泵站状态（读台账同源数据） |
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

数据保存在后端 `backend/data/store.json`（可用环境变量 `LIFT_PLATFORM_DATA_FILE`
覆盖路径），采用临时文件 + 原子替换写入，服务重启后编辑结果仍然保留；
首次启动没有数据文件时用示例数据初始化。

提升泵站相关口径：

- 「泵站状态」是唯一状态：台账、液位记录、管网画面三处同源，
  按「格栅堵塞 > 液位 ≥ 5.0m 高液位 > 正常运行」自动推导，停机由动作显式设置。
- 液位高度与格栅状态只挂在「泵站编号」上；液位记录每次登记都追加一条历史，
  新记录不会覆盖旧记录，集水池容积等台账信息在登记时按泵站编号带出并固化。
- `PUT /api/lift/{id}` 保存台账编辑，`PUT /api/lift-level/{id}` 只修正对应历史记录
  （历史记录不允许改挂到别的泵站编号）。
