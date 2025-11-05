import { useMemo, useState } from 'react'
import type { ReportRow } from '../types'

function pct(v: number) { return isFinite(v) ? `${(v * 100).toFixed(2)}%` : '-' }
function money(v: number) { return isFinite(v) ? v.toFixed(2) : '-' }

interface Props { rows: ReportRow[] }

export default function ReportTable({ rows }: Props) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const toggle = (key: string) => setExpanded((s) => ({ ...s, [key]: !s[key] }))

  const dayHeaders = useMemo(() => {
    const first = rows[0]?.days ?? []
    return first.map((d) => d.date)
  }, [rows])

  // 列宽（可拖动）
  const [colW, setColW] = useState({
    cat: 110,
    nameCn: 140,
    sku: 160,
    sumQty: 110,
    sumAmt: 120,
    sumAd: 110,
    ozid: 120,
    day: 120,
  })
  const stickyLeft = useMemo(() => {
    const arr: number[] = []
    arr[0] = 0
    arr[1] = arr[0] + colW.cat
    arr[2] = arr[1] + colW.nameCn
    arr[3] = arr[2] + colW.sku
    arr[4] = arr[3] + colW.sumQty
    arr[5] = arr[4] + colW.sumAmt
    arr[6] = arr[5] + colW.sumAd
    arr[7] = arr[6] + colW.ozid
    return arr
  }, [colW])

  const startResize = (key: string, e: React.MouseEvent) => {
    e.preventDefault()
    const startX = e.clientX
    const startW = (colW as any)[key] ?? colW.day
    function onMove(ev: MouseEvent) {
      const dx = ev.clientX - startX
      const next = Math.max(80, startW + dx)
      setColW((w) => ({ ...w, [key]: next }))
    }
    function onUp() {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }

  return (
    <div className="table-wrap"><table>
      <thead>
        <tr>
          <th className="sticky-col" style={{ left: 0, width: colW.cat, minWidth: colW.cat }}><div className="th-inner">大类目<span className="col-resizer" onMouseDown={(e) => startResize('cat', e)} /></div></th>
          <th className="sticky-col" style={{ left: stickyLeft[1], width: colW.nameCn, minWidth: colW.nameCn }}><div className="th-inner">中文类目<span className="col-resizer" onMouseDown={(e) => startResize('nameCn', e)} /></div></th>
          <th className="sticky-col" style={{ left: stickyLeft[2], width: colW.sku, minWidth: colW.sku }}><div className="th-inner">类目名称<span className="col-resizer" onMouseDown={(e) => startResize('sku', e)} /></div></th>
          <th className="sticky-col" style={{ left: stickyLeft[3], width: colW.sumQty, minWidth: colW.sumQty }}><div className="th-inner">12日销量<span className="col-resizer" onMouseDown={(e) => startResize('sumQty', e)} /></div></th>
          <th className="sticky-col" style={{ left: stickyLeft[4], width: colW.sumAmt, minWidth: colW.sumAmt }}><div className="th-inner">12日销售额<span className="col-resizer" onMouseDown={(e) => startResize('sumAmt', e)} /></div></th>
          <th className="sticky-col" style={{ left: stickyLeft[5], width: colW.sumAd, minWidth: colW.sumAd }}><div className="th-inner">12日广告占比<span className="col-resizer" onMouseDown={(e) => startResize('sumAd', e)} /></div></th>
          <th className="sticky-col" style={{ left: stickyLeft[6], width: colW.ozid, minWidth: colW.ozid }}><div className="th-inner">Ozon ID<span className="col-resizer" onMouseDown={(e) => startResize('ozid', e)} /></div></th>
          {dayHeaders.map((d, i) => (
            <th key={d} className="day-col" style={{ width: colW.day, minWidth: colW.day }}><div className="th-inner">第{i + 1}天<br/><span className="meta">{d}</span><span className="col-resizer" onMouseDown={(e) => startResize('day', e)} /></div></th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => {
          const key = `${r.platform}-${r.account}-${r.ozon_id}`
          const isOpen = !!expanded[key]
          return (
            <>
              <tr key={key}>
                <td className="sticky-col" style={{ left: 0, width: colW.cat, minWidth: colW.cat }}>{r.category}</td>
                <td className="sticky-col meta" style={{ left: stickyLeft[1], width: colW.nameCn, minWidth: colW.nameCn }}>{r.name_cn}</td>
                <td className="sticky-col" style={{ left: stickyLeft[2], width: colW.sku, minWidth: colW.sku }}>{r.sku}</td>
                <td className="sticky-col" style={{ left: stickyLeft[3], width: colW.sumQty, minWidth: colW.sumQty }}>{r.summary_12d.sales_qty}</td>
                <td className="sticky-col" style={{ left: stickyLeft[4], width: colW.sumAmt, minWidth: colW.sumAmt }}>{money(r.summary_12d.sales_amount)}</td>
                <td className="sticky-col" style={{ left: stickyLeft[5], width: colW.sumAd, minWidth: colW.sumAd }}>{pct(r.summary_12d.ad_ratio)}</td>
                <td className="sticky-col nowrap" style={{ left: stickyLeft[6], width: colW.ozid, minWidth: colW.ozid }}>{r.ozon_id} <span className="expand" onClick={() => toggle(key)}>{isOpen ? '收起' : '展开'}</span></td>
                {r.days.map((d) => (
                  <td key={d.date} className="day-col" style={{ width: colW.day, minWidth: colW.day }}>
                    <div className="cell-grid">
                      <div><span className="meta">销量</span><span>{d.total_sales_qty}</span></div>
                      <div><span className="meta">广告</span><span>{d.ad_sales_qty}</span></div>
                      <div><span className="meta">自然</span><span>{d.natural_sales_qty}</span></div>
                      <div><span className="meta">销售额</span><span>{money(d.sales_amount)}</span></div>
                      <div><span className="meta">售价</span><span>{money(d.avg_price)}</span></div>
                      <div><span className="meta">成本</span><span>{money(d.goods_cost)}</span></div>
                      <div><span className="meta">销售成本</span><span>{money(d.sales_cost)}</span></div>
                      <div><span className="meta">广告费</span><span>{money(d.ad_spend)}</span></div>
                      <div><span className="meta">回款</span><span>{money(d.payout)}</span></div>
                      <div><span className="meta">利润</span><span>{money(d.profit)}</span></div>
                      <div><span className="meta">库存</span><span>{d.inventory}</span></div>
                      <div><span className="meta">广告占比</span><span>{pct(d.ad_ratio)}</span></div>
                    </div>
                  </td>
                ))}
              </tr>
              {isOpen && (
                <tr>
                  <td colSpan={7 + dayHeaders.length}>
                    <div>
                      <strong>详细</strong>：
                      <span className="meta" style={{ marginLeft: 8 }}>12日广告销量占比：{pct(r.summary_12d.ad_sales_ratio)}</span>
                    </div>
                    <div className="meta">平台：{r.platform}，账号：{r.account}</div>
                  </td>
                </tr>
              )}
            </>
          )
        })}
      </tbody>
    </table></div>
  )
}
