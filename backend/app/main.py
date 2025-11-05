from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, Query
import re
from fastapi.middleware.cors import CORSMiddleware

from .db import get_collection
from .models import DayMetrics, ReportResponse, ReportRow, Summary12D
from .utils import date_range, month_start, parse_any_date, build_weeks, build_months


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
    # 组合为 AND，内部有 OR 子条件
    and_filters: List[Dict[str, Any]] = []
    # 日期字段兼容：同时支持 Date 类型范围过滤与字符串精确匹配
    def _fmt_v(d: date) -> List[str]:
        y = d.year
        m = d.month
        dd = d.day
        return [
            f"{y}/{m}/{dd}",
            f"{y}/{m:02d}/{dd:02d}",
            f"{y}-{m:02d}-{dd:02d}",
            f"{y}-{m}-{dd}",
        ]

    str_dates: List[str] = []
    cur = start_d
    while cur <= end_d:
        str_dates.extend(_fmt_v(cur))
        cur = cur + timedelta(days=1)
    str_dates = list(sorted(set(str_dates)))

    # Date 类型范围：包含 end_d 当天，采用 [start, end+1) 的半开区间更稳妥
    start_dt = datetime.combine(start_d, datetime.min.time())
    end_dt_next = datetime.combine(end_d, datetime.min.time()) + timedelta(days=1)

    date_fields = ["日期", "date", "Date"]
    date_or: List[Dict[str, Any]] = []
    for f in date_fields:
        date_or.append({f: {"$gte": start_dt, "$lt": end_dt_next}})
        date_or.append({f: {"$in": str_dates}})
    if date_or:
        and_filters.append({"$or": date_or})

    if platform:
        plat_regex = re.compile(rf"^\s*{re.escape(platform)}\s*$", re.IGNORECASE)
        and_filters.append({"$or": [{"平台": plat_regex}, {"platform": plat_regex}]})
    if account:
        acc_regex = re.compile(rf"^\s*{re.escape(account)}\s*$", re.IGNORECASE)
        and_filters.append({"$or": [{"账号": acc_regex}, {"account": acc_regex}]})

    final_filter: Dict[str, Any] = {"$and": and_filters} if and_filters else {}
    cursor = coll.find(final_filter)
    return [doc async for doc in cursor]


def _doc_date(doc: Dict[str, Any]) -> Optional[date]:
    d = doc.get("日期")
    if not d:
        return None
    try:
        if isinstance(d, datetime):
            return d.date()
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


@app.get("/api/debug-report")
async def debug_report(
    date_str: str,
    platform: Optional[str] = None,
    account: Optional[str] = None,
    days: Optional[int] = None,
    mode: str = "day",
    weeks: Optional[int] = None,
    months: Optional[int] = None,
):
    end_d = parse_any_date(date_str)
    if mode == "week":
        n_weeks = int(weeks or 12)
        wk = build_weeks(end_d, n_weeks)
        start_d = wk[0][0]
        end_d = wk[-1][1]
    elif mode == "month":
        n_months = int(months or 12)
        mr = build_months(end_d, n_months)
        start_d = mr[0][0]
        end_d = mr[-1][1]
    else:
        if days is not None:
            days = max(1, min(62, int(days)))
            start_d = end_d - timedelta(days=days - 1)
        else:
            start_d = month_start(end_d)

    # 构造与 _fetch_docs 相同的过滤器，附加计数
    coll = get_collection()
    # 日期部分
    def _fmt_v(d: date) -> List[str]:
        y, m, dd = d.year, d.month, d.day
        return [f"{y}/{m}/{dd}", f"{y}/{m:02d}/{dd:02d}", f"{y}-{m:02d}-{dd:02d}", f"{y}-{m}-{dd}"]
    str_dates: List[str] = []
    cur = start_d
    while cur <= end_d:
        str_dates.extend(_fmt_v(cur))
        cur = cur + timedelta(days=1)
    str_dates = list(sorted(set(str_dates)))
    start_dt = datetime.combine(start_d, datetime.min.time())
    end_dt_next = datetime.combine(end_d, datetime.min.time()) + timedelta(days=1)
    date_fields = ["日期", "date", "Date"]
    date_or: List[Dict[str, Any]] = []
    for f in date_fields:
        date_or.append({f: {"$gte": start_dt, "$lt": end_dt_next}})
        date_or.append({f: {"$in": str_dates}})
    filter_parts: List[Dict[str, Any]] = []
    if date_or:
        filter_parts.append({"$or": date_or})
    if platform:
        plat_regex = re.compile(rf"^\s*{re.escape(platform)}\s*$", re.IGNORECASE)
        filter_parts.append({"$or": [{"平台": plat_regex}, {"platform": plat_regex}]})
    if account:
        acc_regex = re.compile(rf"^\s*{re.escape(account)}\s*$", re.IGNORECASE)
        filter_parts.append({"$or": [{"账号": acc_regex}, {"account": acc_regex}]})
    final_filter: Dict[str, Any] = {"$and": filter_parts} if filter_parts else {}

    total = await coll.count_documents(final_filter)
    sample = await coll.find_one(final_filter)
    return {
        "start": str(start_d),
        "end": str(end_d),
        "mode": mode,
        "filter": str(final_filter),
        "str_dates": str_dates[:5],
        "total_match": int(total),
        "sample_keys": list(sample.keys()) if sample else [],
    }


@app.get("/api/report", response_model=ReportResponse)
async def report(
    date_str: str = Query(..., alias="date", description="选择的日期，YYYY-MM-DD"),
    platform: Optional[str] = Query(None),
    account: Optional[str] = Query(None),
    mode: str = Query("day", pattern="^(day|week|month)$"),
    days: Optional[int] = Query(None, ge=1, le=62, description="展示的天数（可选，默认当月起）"),
    weeks: Optional[int] = Query(None, ge=1, le=52, description="周模式下展示的周数"),
    months: Optional[int] = Query(None, ge=1, le=36, description="月模式下展示的月数"),
    page: int = 1,
    page_size: int = Query(50, ge=1, le=500),
):
    end_d = parse_any_date(date_str)
    period_labels: List[str] = []

    if mode == "day":
        if days is not None:
            days = max(1, min(62, int(days)))
            start_d = end_d - timedelta(days=days - 1)
        else:
            start_d = month_start(end_d)
        periods = list(date_range(start_d, end_d))

        # 取记录
        docs = await _fetch_docs(start_d, end_d, platform, account)
        groups: Dict[tuple, List[dict]] = defaultdict(list)
        for doc in docs:
            groups[_row_key(doc)].append(doc)
        keys = list(groups.keys())
        total = len(keys)
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total)
        page_keys = keys[start_idx:end_idx]
        rows: List[ReportRow] = [_build_row(periods, groups[k]) for k in page_keys]
        return ReportResponse(
            start=start_d,
            end=end_d,
            days_count=len(periods),
            page=page,
            page_size=page_size,
            total=total,
            rows=rows,
            mode="day",
            period_labels=[],
        )

    if mode == "week":
        n_weeks = int(weeks or 12)
        week_ranges = build_weeks(end_d, n_weeks)  # oldest -> latest
        start_d = week_ranges[0][0]
        last_end = week_ranges[-1][1]
        period_labels = [f"{a} ~ {b}" for (a, b) in week_ranges]

        docs = await _fetch_docs(start_d, last_end, platform, account)
        groups: Dict[tuple, List[dict]] = defaultdict(list)
        for doc in docs:
            groups[_row_key(doc)].append(doc)

        def week_index(d: date) -> Optional[int]:
            for idx, (s, e) in enumerate(week_ranges):
                if s <= d <= e:
                    return idx
            return None

        def build_week_row(docs: List[Dict[str, Any]]) -> ReportRow:
            weeks_metrics: List[DayMetrics] = []
            for s, e in week_ranges:
                label = f"{s} ~ {e}"
                weeks_metrics.append(_empty_day(s))
                weeks_metrics[-1].date = label

            for doc in docs:
                d = _doc_date(doc)
                if d is None:
                    continue
                idx = week_index(d)
                if idx is None:
                    continue
                dm = weeks_metrics[idx]
                total_sales_qty = _safe_int(doc.get("总销量") or doc.get("销量") or doc.get("销售量"))
                tpl_qty = _safe_int(doc.get("模板销量"))
                search_qty = _safe_int(doc.get("搜索销量"))
                natural_qty = _safe_int(doc.get("自然销量")) if doc.get("自然销量") is not None else max(total_sales_qty - tpl_qty - search_qty, 0)

                sales_amount = _safe_float(doc.get("总销售额") or doc.get("销售额"))
                goods_cost = _safe_float(doc.get("总货物成本") or doc.get("货物成本") or doc.get("成本|卢布") or doc.get("成本"))
                sales_cost = _safe_float(doc.get("总销售成本") or doc.get("销售成本"))
                tpl_spend = _safe_float(doc.get("总模板花费") or doc.get("模板花费"))
                search_spend = _safe_float(doc.get("总搜索花费") or doc.get("搜索花费"))
                ad_spend = tpl_spend + search_spend
                payout = _safe_float(doc.get("总回款") or doc.get("回款"))
                inventory = _safe_int(doc.get("库存数量") or 0)

                dm.total_sales_qty += total_sales_qty
                dm.ad_sales_qty += (tpl_qty + search_qty)
                dm.natural_sales_qty += natural_qty
                dm.sales_amount += sales_amount
                dm.goods_cost += goods_cost
                dm.sales_cost += sales_cost
                dm.ad_spend += ad_spend
                dm.payout += payout
                dm.inventory = inventory

            for dm in weeks_metrics:
                dm.avg_price = round((dm.sales_amount / dm.total_sales_qty) if dm.total_sales_qty > 0 else 0.0, 2)
                dm.profit = _calc_profit(dm.sales_amount, dm.goods_cost, dm.sales_cost, dm.ad_spend)
                dm.ad_ratio = round((dm.ad_spend / dm.sales_amount) if dm.sales_amount > 0 else 0.0, 4)

            first = docs[0] if docs else {}
            ozon_id, name_cn, category, sku, platform_v, account_v = _row_key(first)

            sales_qty_n = sum(x.total_sales_qty for x in weeks_metrics)
            sales_amt_n = sum(x.sales_amount for x in weeks_metrics)
            ad_qty_n = sum(x.ad_sales_qty for x in weeks_metrics)
            ad_spend_n = sum(x.ad_spend for x in weeks_metrics)
            summary_12d = Summary12D(
                sales_qty=sales_qty_n,
                sales_amount=round(sales_amt_n, 2),
                ad_sales_qty=ad_qty_n,
                ad_spend=round(ad_spend_n, 2),
                ad_ratio=round((ad_spend_n / sales_amt_n) if sales_amt_n > 0 else 0.0, 4),
                ad_sales_ratio=round((ad_qty_n / sales_qty_n) if sales_qty_n > 0 else 0.0, 4),
            )

            return ReportRow(
                category=category or None,
                name_cn=name_cn or None,
                sku=sku or None,
                ozon_id=ozon_id or None,
                platform=platform_v or None,
                account=account_v or None,
                summary_12d=summary_12d,
                days=weeks_metrics,
            )

        keys = list(groups.keys())
        total = len(keys)
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total)
        page_keys = keys[start_idx:end_idx]
        rows = [build_week_row(groups[k]) for k in page_keys]

        return ReportResponse(
            start=start_d,
            end=last_end,
            days_count=len(week_ranges),
            page=page,
            page_size=page_size,
            total=total,
            rows=rows,
            mode="week",
            period_labels=period_labels,
        )

    # month mode
    if mode == "month":
        n_months = int(months or 12)
        month_ranges = build_months(end_d, n_months)  # [(s, e, ym)]
        start_d = month_ranges[0][0]
        last_end = month_ranges[-1][1]
        period_labels = [f"{ym}（{s} ~ {e}）" for (s, e, ym) in month_ranges]

        docs = await _fetch_docs(start_d, last_end, platform, account)
        groups: Dict[tuple, List[dict]] = defaultdict(list)
        for doc in docs:
            groups[_row_key(doc)].append(doc)

        def month_index(d: date) -> Optional[int]:
            for idx, (s, e, _ym) in enumerate(month_ranges):
                if s <= d <= e:
                    return idx
            return None

        def build_month_row(docs: List[Dict[str, Any]]) -> ReportRow:
            months_metrics: List[DayMetrics] = []
            for s, e, ym in month_ranges:
                label = f"{ym}\n{s} ~ {e}"
                months_metrics.append(_empty_day(s))
                months_metrics[-1].date = label

            for doc in docs:
                d = _doc_date(doc)
                if d is None:
                    continue
                idx = month_index(d)
                if idx is None:
                    continue
                dm = months_metrics[idx]
                total_sales_qty = _safe_int(doc.get("总销量") or doc.get("销量") or doc.get("销售量"))
                tpl_qty = _safe_int(doc.get("模板销量"))
                search_qty = _safe_int(doc.get("搜索销量"))
                natural_qty = _safe_int(doc.get("自然销量")) if doc.get("自然销量") is not None else max(total_sales_qty - tpl_qty - search_qty, 0)

                sales_amount = _safe_float(doc.get("总销售额") or doc.get("销售额"))
                goods_cost = _safe_float(doc.get("总货物成本") or doc.get("货物成本") or doc.get("成本|卢布") or doc.get("成本"))
                sales_cost = _safe_float(doc.get("总销售成本") or doc.get("销售成本"))
                tpl_spend = _safe_float(doc.get("总模板花费") or doc.get("模板花费"))
                search_spend = _safe_float(doc.get("总搜索花费") or doc.get("搜索花费"))
                ad_spend = tpl_spend + search_spend
                payout = _safe_float(doc.get("总回款") or doc.get("回款"))
                inventory = _safe_int(doc.get("库存数量") or 0)

                dm.total_sales_qty += total_sales_qty
                dm.ad_sales_qty += (tpl_qty + search_qty)
                dm.natural_sales_qty += natural_qty
                dm.sales_amount += sales_amount
                dm.goods_cost += goods_cost
                dm.sales_cost += sales_cost
                dm.ad_spend += ad_spend
                dm.payout += payout
                dm.inventory = inventory

            for dm in months_metrics:
                dm.avg_price = round((dm.sales_amount / dm.total_sales_qty) if dm.total_sales_qty > 0 else 0.0, 2)
                dm.profit = _calc_profit(dm.sales_amount, dm.goods_cost, dm.sales_cost, dm.ad_spend)
                dm.ad_ratio = round((dm.ad_spend / dm.sales_amount) if dm.sales_amount > 0 else 0.0, 4)

            first = docs[0] if docs else {}
            ozon_id, name_cn, category, sku, platform_v, account_v = _row_key(first)

            sales_qty_n = sum(x.total_sales_qty for x in months_metrics)
            sales_amt_n = sum(x.sales_amount for x in months_metrics)
            ad_qty_n = sum(x.ad_sales_qty for x in months_metrics)
            ad_spend_n = sum(x.ad_spend for x in months_metrics)
            summary_12d = Summary12D(
                sales_qty=sales_qty_n,
                sales_amount=round(sales_amt_n, 2),
                ad_sales_qty=ad_qty_n,
                ad_spend=round(ad_spend_n, 2),
                ad_ratio=round((ad_spend_n / sales_amt_n) if sales_amt_n > 0 else 0.0, 4),
                ad_sales_ratio=round((ad_qty_n / sales_qty_n) if sales_qty_n > 0 else 0.0, 4),
            )

            return ReportRow(
                category=category or None,
                name_cn=name_cn or None,
                sku=sku or None,
                ozon_id=ozon_id or None,
                platform=platform_v or None,
                account=account_v or None,
                summary_12d=summary_12d,
                days=months_metrics,
            )

        keys = list(groups.keys())
        total = len(keys)
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total)
        page_keys = keys[start_idx:end_idx]
        rows = [build_month_row(groups[k]) for k in page_keys]

        return ReportResponse(
            start=start_d,
            end=last_end,
            days_count=len(month_ranges),
            page=page,
            page_size=page_size,
            total=total,
            rows=rows,
            mode="month",
            period_labels=period_labels,
        )

    # unreachable
