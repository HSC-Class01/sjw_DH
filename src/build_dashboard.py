from __future__ import annotations
from pathlib import Path
import json, html, yaml, pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
DATA = ROOT / "data" / "financials.csv"
OUT = ROOT / "dashboard" / "index.html"

NUM_COLS = ["revenue","operating_profit","net_income","assets","liabilities","equity","operating_cash_flow","revenue_growth","operating_margin","net_margin","roe","roa","debt_ratio","equity_ratio","current_ratio","cfo_margin","fcf","fcf_margin"]
LABELS = {"revenue":"매출액","operating_profit":"영업이익","net_income":"당기순이익","assets":"자산총계","liabilities":"부채총계","equity":"자본총계","operating_cash_flow":"영업활동현금흐름","revenue_growth":"매출 성장률","operating_margin":"영업이익률","net_margin":"순이익률","roe":"ROE","roa":"ROA","debt_ratio":"부채비율","equity_ratio":"자기자본비율","current_ratio":"유동비율","cfo_margin":"CFO 마진","fcf":"FCF","fcf_margin":"FCF 마진"}


def fmt(v, pct=False):
    if pd.isna(v): return "—"
    if pct: return f"{v:,.1f}%"
    return f"{v/100000000:,.0f}"  # KRW -> KRW 100 million (억원)


def table(df, title):
    cols = [c for c in NUM_COLS if c in df.columns]
    rows = []
    for _, r in df.sort_values("year").iterrows():
        cells = [f"<td>{int(r['year'])}</td>"]
        for c in cols:
            pct = c.endswith("margin") or c in {"revenue_growth","roe","roa","debt_ratio","equity_ratio","current_ratio","cfo_margin"}
            cells.append(f"<td>{fmt(r[c], pct)}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    headers = "<th>연도</th>" + "".join(f"<th>{html.escape(LABELS.get(c,c))}</th>" for c in cols)
    return f"<section class='card'><h2>{html.escape(title)}</h2><div class='table-wrap'><table><thead><tr>{headers}</tr></thead><tbody>{''.join(rows)}</tbody></table></div><p class='note'>금액은 억원 단위로 표시하며, 비율은 %입니다.</p></section>"


def main():
    if not DATA.exists():
        raise SystemExit("financials.csv not found. Run src/dart_agent.py first.")
    df = pd.read_csv(DATA)
    latest = df.sort_values("year").iloc[-1]
    annual = df[df.period == "annual"].copy()
    half = df[df.period == "half"].copy()
    q = df[df.period.isin(["q1","q3"])].copy()
    # Plotly figures are rendered client-side; data are embedded to keep GitHub Pages serverless.
    years = annual.year.tolist()
    rev = annual.revenue.fillna(0).tolist() if "revenue" in annual else []
    op = annual.operating_profit.fillna(0).tolist() if "operating_profit" in annual else []
    opm = annual.operating_margin.round(2).tolist() if "operating_margin" in annual else []
    debt = annual.debt_ratio.round(2).tolist() if "debt_ratio" in annual else []
    peers = CFG.get("peers", [])
    peer_rows = "".join(f"<tr><td>{html.escape(p['name'])}</td><td>{html.escape(p.get('ticker') or '—')}</td><td>{html.escape(p.get('note') or '')}</td></tr>" for p in peers)
    badge = "../assets/dashboard-badge.svg"
    data_json = json.dumps({"years":years,"revenue":rev,"op":op,"opm":opm,"debt":debt}, ensure_ascii=False)
    title = CFG["company"]["name"] + " DART Financial Agent Dashboard"
    cards = []
    for c in ["revenue","operating_profit","net_income","operating_margin","roe","debt_ratio"]:
        pct = c in {"operating_margin","roe","debt_ratio"}
        cards.append(f"<div class='kpi'><span>{LABELS[c]}</span><strong>{fmt(latest.get(c), pct)}</strong><small>{latest['year']} {latest['report_label']}</small></div>")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script><style>
:root{{--bg:#f6f8fb;--card:#fff;--text:#182230;--muted:#64748b;--line:#e6eaf0;--accent:#1d4ed8}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:var(--text)}}main{{max-width:1400px;margin:auto;padding:32px 22px 60px}}header{{display:flex;justify-content:space-between;gap:20px;align-items:flex-start;margin-bottom:24px}}h1{{margin:0 0 6px;font-size:32px}}h2{{font-size:19px;margin:0 0 16px}}.sub{{color:var(--muted)}}.badge{{width:190px}}.kpis{{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin-bottom:16px}}.kpi,.card{{background:var(--card);border:1px solid var(--line);border-radius:16px;box-shadow:0 5px 18px rgba(15,23,42,.04)}}.kpi{{padding:16px}}.kpi span,.kpi small{{display:block;color:var(--muted)}}.kpi strong{{display:block;font-size:24px;margin:8px 0}}.grid{{display:grid;grid-template-columns:1.6fr 1fr;gap:16px;margin-bottom:16px}}.card{{padding:20px;margin-bottom:16px}}.chart{{height:360px}}.table-wrap{{overflow:auto}}table{{width:100%;border-collapse:collapse;white-space:nowrap;font-size:13px}}th,td{{padding:10px 9px;border-bottom:1px solid var(--line);text-align:right}}th:first-child,td:first-child{{text-align:left;position:sticky;left:0;background:var(--card)}}th{{color:#475569;background:#f8fafc}}.note{{font-size:12px;color:var(--muted)}}.source{{font-size:12px;color:var(--muted);line-height:1.7}}@media(max-width:1000px){{.kpis{{grid-template-columns:repeat(3,1fr)}}.grid{{grid-template-columns:1fr}}}}@media(max-width:600px){{.kpis{{grid-template-columns:repeat(2,1fr)}}h1{{font-size:25px}}}}
</style></head><body><main><header><div><h1>대한전선 재무 데이터 Dashboard</h1><div class="sub">OpenDART · 2010–현재 · 사업/반기/분기보고서 · 자동 업데이트: 매월 1일</div></div><a href="https://opendart.fss.or.kr/" target="_blank"><img class="badge" src="{badge}" alt="Dashboard"></a></header><div class="kpis">{''.join(cards)}</div><div class="grid"><section class="card"><h2>연간 매출·영업이익 추이</h2><div id="chart1" class="chart"></div></section><section class="card"><h2>수익성·레버리지 추이</h2><div id="chart2" class="chart"></div></section></div>{table(annual,'Annual · 연간')} {table(half,'Half-year · 반기')} {table(q,'Quarterly · 분기')}<section class='card'><h2>국내 Peer Firms</h2><div class='table-wrap'><table><thead><tr><th>기업</th><th>종목코드</th><th>비고</th></tr></thead><tbody>{peer_rows}</tbody></table></div><p class='note'>Peer 구성은 국내 전선업 주요 비교기업을 기준으로 하며, LS전선은 비상장사이므로 종목코드를 표시하지 않습니다.</p></section><section class='card'><h2>데이터·분석 기준</h2><div class='source'>주요 재무제표는 금융감독원 OpenDART를 원천으로 합니다. 2015년 이후는 구조화 재무제표 API를 우선 사용하고, 2010–2014년은 공시검색 및 공시서류 원본파일을 이용하는 fallback parser를 사용합니다. 재무비율은 수집된 원자료에서 자동 계산되며, 보고서 유형별로 기간 개념이 다르므로 비교 시 주의가 필요합니다.<br><br>금액은 대시보드 표에서 억원 단위로 표시합니다.</div></section></main><script>const d={data_json};Plotly.newPlot('chart1',[{{x:d.years,y:d.revenue,name:'매출액',type:'bar'}},{{x:d.years,y:d.op,name:'영업이익',type:'bar'}}],{{margin:{{t:10,r:20,b:50,l:60}},barmode:'group',legend:{{orientation:'h'}},yaxis:{{title:'KRW million (OpenDART)'}}}},{{responsive:true,displayModeBar:false}});Plotly.newPlot('chart2',[{{x:d.years,y:d.opm,name:'영업이익률',mode:'lines+markers'}},{{x:d.years,y:d.debt,name:'부채비율',mode:'lines+markers',yaxis:'y2'}}],{{margin:{{t:10,r:55,b:50,l:55}},legend:{{orientation:'h'}},yaxis:{{title:'영업이익률 (%)'}},yaxis2:{{title:'부채비율 (%)',overlaying:'y',side:'right'}}}},{{responsive:true,displayModeBar:false}});</script></body></html>''', encoding="utf-8")
    print(OUT)

if __name__ == '__main__': main()
