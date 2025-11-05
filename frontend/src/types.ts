export interface DayMetrics {
  date: string
  total_sales_qty: number
  ad_sales_qty: number
  natural_sales_qty: number
  avg_price: number
  goods_cost: number
  sales_cost: number
  ad_spend: number
  sales_amount: number
  payout: number
  profit: number
  inventory: number
  ad_ratio: number
}

export interface Summary12D {
  sales_qty: number
  sales_amount: number
  ad_sales_qty: number
  ad_spend: number
  ad_ratio: number
  ad_sales_ratio: number
}

export interface ReportRow {
  category?: string
  name_cn?: string
  sku?: string
  ozon_id?: string
  platform?: string
  account?: string
  summary_12d: Summary12D
  days: DayMetrics[]
}

export interface ReportResponse {
  start: string
  end: string
  days_count: number
  page: number
  page_size: number
  total: number
  rows: ReportRow[]
}

