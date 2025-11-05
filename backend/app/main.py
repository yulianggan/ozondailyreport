from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .db import get_collection
from .models import DayMetrics, ReportResponse, ReportRow, Summary12D
from .utils import date_range, month_start, parse_any_date


app = FastAPI(title="Ozon Operation Report API")

# 允许本地前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _safe_float(v: Any) -> float:
    try:
        if v is None:
            return 0.0
        if isinstance(v, (int, float)):
            return float(v)
        return float(str(v).replace(",", ""))
    except Exception:  # noqa: BLE001
        return 0.0


def _safe_int(v: Any) -> int:
    try:
        if v is None:
            return 0
        if isinstance(v, (int,)):
            return int(v)
        return int(float(str(v).replace(",", "")))
    except Exception:  # noqa: BLE001
        return 0


def _calc_profit(sales_amount: float, goods_cost: float, sales_cost: float, ad_spend: float) -> float:
    return round(sales_amount - goods_cost - sales_cost - ad_spend, 2)


async def _fetch_docs(
    start_d: date,
    end_d: date,
    platform: Optional[str],
    account: Optional[str],
) -> List[Dict[str, Any]]:
    coll = get_collection()
    filters: Dict[str, Any] = {}
    # 日期字段兼容：字符串，生成该范围内所有可能格式
    def _fmt_v(d: date) -> List[str]:
        y = d.year
        m = d.month
        dd = d.day
        return [
            f"{y}/{m}/{dd}",
            f"{y}/{m:02d}/{dd:02d}",
            f"{y}-{m:02d}-{dd:02d}",
        ]
    dates: List[str] = []
    cur = start_d
    while cur <= end_d:
        dates.extend(_fmt_v(cur))
        cur = cur + timedelta(days=1)
    filters["日期"] = {"$in": list(sorted(set(dates)))}
    if platform:
        filters["平台"] = platform
    if account:
        filters["账号"] = account
    cursor = coll.find(filters)
    return [doc async for doc in cursor]


def _doc_date(doc: Dict[str, Any]) -> Optional[date]:
    d = doc.get("日期")
    if not d:
        return None
    try:
        return parse_any_date(str(d))
    except Exception:  # noqa: BLE001
        return None


def _row_key(doc: Dict[str, Any]) -> Tuple[str, str, str, str, str, str]:
    return (
        str(doc.get("Ozon ID", "")),
        str(doc.get("中文名称", "")),
        str(doc.get("类别", "")),
        str(doc.get("SKU", "")),
        str(doc.get("平台", "")),
        str(doc.get("账号", "")),
    )


def _empty_day(d: date) -> DayMetrics:
    return DayMetrics(
        date=d,
        total_sales_qty=0,
        ad_sales_qty=0,
        natural_sales_qty=0,
        avg_price=0.0,
        goods_cost=0.0,
        sales_cost=0.0,
        ad_spend=0.0,
        sales_amount=0.0,
        payout=0.0,
        profit=0.0,
        inventory=0,
        ad_ratio=0.0,
    )


def _build_row(days_order: List[date], docs: List[Dict[str, Any]]) -> ReportRow:
    # 基础信息取第一条
    first = docs[0] if docs else {}
    ozon_id, name_cn, category, sku, platform, account = _row_key(first)

    # 建立每天映射
    day_map: Dict[date, DayMetrics] = {d: _empty_day(d) for d in days_order}

    for doc in docs:
        d = _doc_date(doc)
        if d is None or d not in day_map:
            continue
        dm = day_map[d]
        total_sales_qty = _safe_int(doc.get("总销量") or doc.get("销量") or doc.get("销售量"))
        tpl_qty = _safe_int(doc.get("模板销量"))
        search_qty = _safe_int(doc.get("搜索销量"))
        nat_qty_field = doc.get("自然销量")
        natural_qty = _safe_int(nat_qty_field) if nat_qty_field is not None else max(total_sales_qty - tpl_qty - search_qty, 0)

        avg_price = _safe_float(doc.get("均价") or doc.get("售价"))
        sales_amount = _safe_float(doc.get("总销售额") or doc.get("销售额"))
        goods_cost = _safe_float(doc.get("总货物成本") or doc.get("货物成本") or doc.get("成本|卢布") or doc.get("成本"))
        sales_cost = _safe_float(doc.get("总销售成本") or doc.get("销售成本"))
        tpl_spend = _safe_float(doc.get("总模板花费") or doc.get("模板花费"))
        search_spend = _safe_float(doc.get("总搜索花费") or doc.get("搜索花费"))
        ad_spend = tpl_spend + search_spend
        payout = _safe_float(doc.get("总回款") or doc.get("回款"))
        inventory = _safe_int(doc.get("库存数量") or 0)

        dm.total_sales_qty = total_sales_qty
        dm.ad_sales_qty = tpl_qty + search_qty
        dm.natural_sales_qty = natural_qty
        dm.avg_price = avg_price
        dm.sales_amount = sales_amount
        dm.goods_cost = goods_cost
        dm.sales_cost = sales_cost
        dm.ad_spend = ad_spend
        dm.payout = payout
        dm.inventory = inventory
        dm.profit = _calc_profit(sales_amount, goods_cost, sales_cost, ad_spend)
        dm.ad_ratio = round((ad_spend / sales_amount) if sales_amount > 0 else 0.0, 4)

    # 12日汇总按最后一天向前滚12天
    end_d = days_order[-1]
    start_12d = end_d - timedelta(days=11)
    days_12 = [d for d in days_order if start_12d <= d <= end_d]
    sales_qty_12 = sum(day_map[d].total_sales_qty for d in days_12)
    sales_amt_12 = sum(day_map[d].sales_amount for d in days_12)
    ad_qty_12 = sum(day_map[d].ad_sales_qty for d in days_12)
    ad_spend_12 = sum(day_map[d].ad_spend for d in days_12)
    summary_12d = Summary12D(
        sales_qty=sales_qty_12,
        sales_amount=round(sales_amt_12, 2),
        ad_sales_qty=ad_qty_12,
        ad_spend=round(ad_spend_12, 2),
        ad_ratio=round((ad_spend_12 / sales_amt_12) if sales_amt_12 > 0 else 0.0, 4),
        ad_sales_ratio=round((ad_qty_12 / sales_qty_12) if sales_qty_12 > 0 else 0.0, 4),
    )

    return ReportRow(
        category=category or None,
        name_cn=name_cn or None,
        sku=sku or None,
        ozon_id=ozon_id or None,
        platform=platform or None,
        account=account or None,
        summary_12d=summary_12d,
        days=[day_map[d] for d in days_order],
    )


@app.get("/api/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/api/report", response_model=ReportResponse)
async def report(
    date_str: str = Query(..., alias="date", description="选择的日期，YYYY-MM-DD"),
    platform: Optional[str] = Query(None),
    account: Optional[str] = Query(None),
    days: Optional[int] = Query(None, ge=1, le=62, description="展示的天数（可选，默认当月起）"),
    page: int = 1,
    page_size: int = Query(50, ge=1, le=500),
):
    end_d = parse_any_date(date_str)
    if days is not None:
        # 指定展示天数，从 end_d 向前回溯（含 end_d）
        days = max(1, min(62, int(days)))
        start_d = end_d - timedelta(days=days - 1)
    else:
        # 默认：当月第一天
        start_d = month_start(end_d)
    days_order = list(date_range(start_d, end_d))

    # 取整月起至选择日的所有记录
    docs = await _fetch_docs(start_d, end_d, platform, account)

    # 以 Ozon ID + 名称 + 类别 + SKU + 平台 + 账号 分组
    groups: Dict[tuple, List[dict]] = defaultdict(list)
    for doc in docs:
        groups[_row_key(doc)].append(doc)

    # 分页
    keys = list(groups.keys())
    total = len(keys)
    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, total)
    page_keys = keys[start_idx:end_idx]

    rows: List[ReportRow] = [_build_row(days_order, groups[k]) for k in page_keys]

    return ReportResponse(
        start=start_d,
        end=end_d,
        days_count=len(days_order),
        page=page,
        page_size=page_size,
        total=total,
        rows=rows,
    )
