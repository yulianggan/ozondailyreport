from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class DayMetrics(BaseModel):
    date: date
    total_sales_qty: int = 0
    ad_sales_qty: int = 0
    natural_sales_qty: int = 0
    avg_price: float = 0.0
    goods_cost: float = 0.0  # 总货物成本
    sales_cost: float = 0.0  # 总销售成本/配送/佣金等
    ad_spend: float = 0.0  # 模板+搜索
    sales_amount: float = 0.0  # 总销售额
    payout: float = 0.0  # 回款
    profit: float = 0.0  # 计算字段
    inventory: int = 0  # 库存数量
    ad_ratio: float = 0.0  # 广告花费/销售额


class Summary12D(BaseModel):
    sales_qty: int = 0
    sales_amount: float = 0.0
    ad_sales_qty: int = 0
    ad_spend: float = 0.0
    ad_ratio: float = 0.0  # ad_spend / sales_amount
    ad_sales_ratio: float = 0.0  # ad_sales_qty / sales_qty


class ReportRow(BaseModel):
    category: Optional[str] = Field(None, description="类别")
    name_cn: Optional[str] = Field(None, description="中文名称")
    sku: Optional[str] = None
    ozon_id: Optional[str] = Field(None, description="Ozon ID")
    platform: Optional[str] = None
    account: Optional[str] = None
    summary_12d: Summary12D
    days: List[DayMetrics]


class ReportResponse(BaseModel):
    start: date
    end: date
    days_count: int
    page: int
    page_size: int
    total: int
    rows: List[ReportRow]

