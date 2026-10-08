import html
import json

def render(result, path):
    points = result['equity']
    values = [p['equity'] for p in points]
    lo,hi = min(values),max(values)
    coords = ' '.join('%.2f,%.2f'%(30+i*940/max(1,len(values)-1),240-(v-lo)*200/max(1,hi-lo)) for i,v in enumerate(values))
    summary = ''.join('<tr><td>%s</td><td>%s</td></tr>'%(html.escape(k),html.escape(str(v))) for k,v in result['summary'].items())
    trades = ''.join('<tr>'+''.join('<td>%s</td>'%html.escape(str(f[k])) for k in ('ts','side','qty','price'))+'</tr>' for f in result['fills'])
    content = '''<!doctype html><html lang="zh"><meta charset="utf-8"><title>USQuant MVP</title>
<style>body{font:16px system-ui;background:#111827;color:#e5e7eb;max-width:1000px;margin:40px auto;padding:20px}td,th{padding:9px;text-align:left;border-bottom:1px solid #374151}svg{background:#1f2937;width:100%%}small{color:#9ca3af}</style>
<h1>美股量化 · MVP</h1><p>%s | %s | 实盘下单已禁用</p><p>合成数据用于验证软件流程，不代表历史收益。</p>
<svg viewBox="0 0 1000 280" role="img" aria-label="账户权益"><polyline fill="none" stroke="#34d399" stroke-width="3" points="%s"/></svg>
<small>权益范围 %.2f – %.2f USD · 期末仓位按收盘价估值，未强制平仓</small>
<h2>运行结果</h2><table>%s</table><h2>成交记录</h2><table><tr><th>UTC 时间</th><th>方向</th><th>股数</th><th>价格</th></tr>%s</table></html>'''%(html.escape(result['mode']),html.escape(result['source']),coords,lo,hi,summary,trades)
    path.write_text(content,encoding='utf-8')
