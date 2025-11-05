import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import dayjs from 'dayjs'
import type { ReportResponse, ReportRow } from './types'
import ReportTable from './components/ReportTable'

function todayIso() {
  return dayjs().format('YYYY-MM-DD')
}

export default function App() {
  const [date, setDate] = useState<string>(todayIso())
  const [platform, setPlatform] = useState<string>('ozon')
  const [account, setAccount] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [days, setDays] = useState<number>(12)
  const [data, setData] = useState<ReportResponse | null>(null)
  const [page, setPage] = useState(1)
  const pageSize = 20

  const fetchData = async () => {
    setLoading(true)
    try {
      const resp = await axios.get<ReportResponse>('/api/report', {
        params: { date, platform: platform || undefined, account: account || undefined, days, page, page_size: pageSize }
      })
      setData(resp.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [date, platform, account, page, days])

  const rows = useMemo<ReportRow[]>(() => data?.rows ?? [], [data])

  return (
    <div className="container">
      <h2>Ozon 运营报表（按商品、按日透视）</h2>
      <div className="toolbar">
        <label>选择日期：<input type="date" value={date} onChange={(e) => setDate(e.target.value)} /></label>
        <label>平台：
          <select value={platform} onChange={(e) => setPlatform(e.target.value)}>
            <option value="">全部</option>
            <option value="ozon">ozon</option>
          </select>
        </label>
        <label>账号：<input value={account} onChange={(e) => setAccount(e.target.value)} placeholder="可选" /></label>
        <label>展示天数：<input type="number" min={1} max={62} value={days} style={{ width: 80 }} onChange={(e)=> setDays(Number(e.target.value||'12'))} /></label>
        <button disabled={loading} onClick={fetchData}>{loading ? '加载中...' : '刷新'}</button>
        {data && (
          <span className="meta">时间范围：{data.start} ~ {data.end}（{data.days_count}天） | 共 {data.total} 个商品</span>
        )}
      </div>
      <ReportTable rows={rows} />
      {data && (
        <div className="toolbar" style={{ justifyContent: 'flex-end' }}>
          <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1 || loading}>上一页</button>
          <span className="meta">第 {page} / {Math.max(1, Math.ceil((data.total || 0) / pageSize))} 页</span>
          <button onClick={() => setPage((p) => p + 1)} disabled={loading || page >= Math.ceil((data.total || 0) / pageSize)}>下一页</button>
        </div>
      )}
    </div>
  )
}
