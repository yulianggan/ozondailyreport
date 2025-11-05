# Ozon Operation Report（FastAPI + React）

## 目录结构

- `backend/` FastAPI 后端，连接 MongoDB（数据库 `ozondatas`，集合 `operation_report`）
- `frontend/` React + Vite 前端（动态按日列渲染表格）

## 环境变量

- `MONGODB_URI`：MongoDB 连接串，例如：`mongodb://localhost:27017`

## 启动后端

```
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export MONGODB_URI="mongodb://localhost:27017"  # 修改为你的连接
uvicorn app.main:app --reload --port 8000
```

接口：
- `GET /api/report?date=YYYY-MM-DD&platform=ozon&account=个人舒适&page=1&page_size=50`

语义：
- `date` 为选择日期；报表日列从该月 1 号到选择日期（含）。
- 计算以选择日期为结束的 12 日滚动汇总（销量、销售额、广告费用、广告占比）。
- 数据按商品（Ozon ID + 名称 + 类别 + SKU + 平台 + 账号）分组。

## 启动前端

```
cd frontend
npm i
npm run dev
```

默认通过 Vite 代理访问后端 `http://localhost:8000`。

## 显示与计算说明

- 日列（第1天~第N天）覆盖从该月首日到选择的日期（含）
- 12日汇总：以选择日向前 12 天（含）进行滚动聚合。
- 广告相关：
  - 广告销量 = 模板销量 + 搜索销量
  - 广告花费 = 模板花费 + 搜索花费
  - 广告占比（展示）= 广告花费 / 销售额
  - 另提供广告销量占比 = 广告销量 / 总销量（在行展开详情中展示）
- 利润（若无 `每日盈亏` 字段）= 销售额 - 货物成本 - 销售成本 - 广告花费

## 注意

- 数据库日期字段支持 `YYYY-MM-DD` 或 `YYYY/M/D` 字符串；如有差异可在 `backend/app/main.py` 的 `_fetch_docs` 与 `_doc_date` 中调整。
- 若部分字段缺失，后端使用 0 或推导（如自然销量=总销量-模板-搜索）以保证稳定渲染。

## 使用 Docker Compose 部署

前置：安装 Docker Desktop（或 Docker Engine + Compose）。

1) 构建并启动

```
./compose-up.sh
# 或者（手动执行）
docker compose up -d --build
```

2) 访问

- 前端：`http://localhost:3051`（Docker 内采用零依赖静态服务器，无需 npm install）
- 后端：`http://localhost:8009/api/health`

说明：
- 默认连接宿主机 MongoDB（无鉴权）。如需变更：
  - `MONGODB_URI="mongodb://<你的地址>:27017" docker compose up -d`
  - `MONGODB_DB`（默认 `ozondatas`），`MONGODB_COLL`（默认 `operation_report`）
