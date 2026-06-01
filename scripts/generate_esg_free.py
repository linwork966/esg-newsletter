"""
ESG Weekly Newsletter - 完全免費版（雙欄儀表板版）
左欄：新聞 / 市場 / 法規
右欄：摘要儀表板 / 全球暖化 / 台灣半導體排放 / GWP / 淨熱值 / 碳費趨勢
"""

import feedparser, requests, html as html_lib, os, re
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

TW_TZ    = timezone(timedelta(hours=8))
NOW      = datetime.now(TW_TZ)
DATE_STR = NOW.strftime("%Y年%m月%d日")
WEEK_STR = NOW.strftime("第%W週")
FILENAME = NOW.strftime("%Y-%m-%d")

BLOCKED_DOMAINS = ['esgtoday.com','ft.com','wsj.com','bloomberg.com','barrons.com']

HEADERS = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

# ── RSS 來源 ──────────────────────────────────────────────────────────────────
NEWS_FEEDS = [
    {"name":"Google News - ESG綜合","url":"https://news.google.com/rss/search?q=ESG+sustainability&hl=en&gl=US&ceid=US:en","category":"ESG綜合","region":"全球"},
    {"name":"Google News - 氣候變遷","url":"https://news.google.com/rss/search?q=climate+change+carbon+emissions&hl=en&gl=US&ceid=US:en","category":"氣候","region":"全球"},
    {"name":"Google News - ESG投資","url":"https://news.google.com/rss/search?q=ESG+investing+sustainable+finance&hl=en&gl=US&ceid=US:en","category":"投資","region":"全球"},
    {"name":"Google News - 再生能源","url":"https://news.google.com/rss/search?q=renewable+energy+solar+wind+power&hl=en&gl=US&ceid=US:en","category":"能源","region":"全球"},
    {"name":"Google News - 企業永續","url":"https://news.google.com/rss/search?q=corporate+sustainability+ESG+report&hl=en&gl=US&ceid=US:en","category":"ESG綜合","region":"全球"},
    {"name":"Google News - 亞洲ESG","url":"https://news.google.com/rss/search?q=ESG+Asia+Pacific+sustainability&hl=en&gl=US&ceid=US:en","category":"ESG綜合","region":"亞洲"},
    {"name":"Google News - 台灣ESG","url":"https://news.google.com/rss/search?q=台灣+ESG+永續&hl=zh-TW&gl=TW&ceid=TW:zh-Hant","category":"ESG綜合","region":"台灣"},
    {"name":"Google News - 台灣碳費","url":"https://news.google.com/rss/search?q=台灣+碳費+碳排放&hl=zh-TW&gl=TW&ceid=TW:zh-Hant","category":"氣候","region":"台灣"},
    {"name":"Google News - 台灣永續報告","url":"https://news.google.com/rss/search?q=永續報告書+ESG揭露+金管會&hl=zh-TW&gl=TW&ceid=TW:zh-Hant","category":"ESG綜合","region":"台灣"},
]
MARKET_FEEDS = [
    {"name":"Google News - 綠色債券","url":"https://news.google.com/rss/search?q=green+bond+sustainable+finance&hl=en&gl=US&ceid=US:en","category":"債券","region":"全球"},
    {"name":"Google News - ESG基金","url":"https://news.google.com/rss/search?q=ESG+fund+sustainable+investment&hl=en&gl=US&ceid=US:en","category":"基金","region":"全球"},
    {"name":"Google News - 碳市場","url":"https://news.google.com/rss/search?q=carbon+credit+carbon+market+price&hl=en&gl=US&ceid=US:en","category":"碳市場","region":"全球"},
    {"name":"Google News - ESG評級","url":"https://news.google.com/rss/search?q=ESG+rating+MSCI+Sustainalytics&hl=en&gl=US&ceid=US:en","category":"評級","region":"全球"},
    {"name":"Google News - 台灣綠色金融","url":"https://news.google.com/rss/search?q=台灣+綠色金融+ESG投資&hl=zh-TW&gl=TW&ceid=TW:zh-Hant","category":"投資","region":"台灣"},
]
REGULATION_FEEDS = [
    {"name":"Google News - CSRD/SFDR","url":"https://news.google.com/rss/search?q=CSRD+SFDR+ESG+regulation+Europe&hl=en&gl=US&ceid=US:en","category":"法規","region":"歐洲"},
    {"name":"Google News - SEC氣候","url":"https://news.google.com/rss/search?q=SEC+climate+disclosure+rule&hl=en&gl=US&ceid=US:en","category":"法規","region":"美洲"},
    {"name":"Google News - ISSB準則","url":"https://news.google.com/rss/search?q=ISSB+IFRS+sustainability+standard&hl=en&gl=US&ceid=US:en","category":"標準","region":"全球"},
    {"name":"Google News - 碳定價","url":"https://news.google.com/rss/search?q=carbon+tax+carbon+pricing+policy&hl=en&gl=US&ceid=US:en","category":"碳政策","region":"全球"},
    {"name":"Google News - 台灣碳費法規","url":"https://news.google.com/rss/search?q=台灣+碳費+氣候法+環境部&hl=zh-TW&gl=TW&ceid=TW:zh-Hant","category":"法規","region":"台灣"},
]

# ── 靜態儀表板資料 ────────────────────────────────────────────────────────────

# 台灣半導體業溫室氣體排放（依企業永續報告書公開資料，2022年度，總量排放最少前5名）
# 資料來源：各公司永續報告書 / TWSE 永續資訊平台
TW_SEMI_EMISSIONS = [
    {"rank":1,"company":"聯詠科技","co2":7821,"ch4":0,"n2o":15,"hfcs":0,"pfcs":0,"sf6":0,"nf3":0,"total":7836,"note":"Fabless","year":"2022"},
    {"rank":2,"company":"瑞昱半導體","co2":52300,"ch4":3,"n2o":28,"hfcs":0,"pfcs":0,"sf6":0,"nf3":0,"total":52331,"note":"Fabless","year":"2022"},
    {"rank":3,"company":"聯發科技","co2":98400,"ch4":12,"n2o":45,"hfcs":0,"pfcs":120,"sf6":0,"nf3":0,"total":98577,"note":"Fabless","year":"2022"},
    {"rank":4,"company":"力積電","co2":412000,"ch4":820,"n2o":380,"hfcs":150,"pfcs":2100,"sf6":480,"nf3":3200,"total":419130,"note":"Foundry","year":"2022"},
    {"rank":5,"company":"世界先進","co2":385000,"ch4":650,"n2o":290,"hfcs":210,"pfcs":1850,"sf6":320,"nf3":2680,"total":390000,"note":"Foundry","year":"2022"},
]

# GWP 數值（IPCC AR6，100年期）
GWP_DATA = [
    {"gas":"CO₂","formula":"CO2","gwp":1,"lifetime":"永久","category":"基準氣體"},
    {"gas":"甲烷","formula":"CH₄","gwp":27.9,"lifetime":"11.8年","category":"短效氣體"},
    {"gas":"氧化亞氮","formula":"N₂O","gwp":273,"lifetime":"109年","category":"長效氣體"},
    {"gas":"HFC-134a","formula":"CH₂FCF₃","gwp":1526,"lifetime":"14年","category":"HFCs"},
    {"gas":"HFC-125","formula":"CHF₂CF₃","gwp":3740,"lifetime":"30年","category":"HFCs"},
    {"gas":"HFC-23","formula":"CHF₃","gwp":14600,"lifetime":"228年","category":"HFCs"},
    {"gas":"CF₄（PFC）","formula":"CF₄","gwp":7380,"lifetime":"50000年","category":"PFCs"},
    {"gas":"C₂F₆（PFC）","formula":"C₂F₆","gwp":12400,"lifetime":"10000年","category":"PFCs"},
    {"gas":"六氟化硫","formula":"SF₆","gwp":25200,"lifetime":"3200年","category":"SF₆"},
    {"gas":"三氟化氮","formula":"NF₃","gwp":17400,"lifetime":"569年","category":"NF₃"},
]

# 淨熱值（低位發熱值，來源：IPCC 2006/2019, EPA, IEA）
NCV_SOLIDS = [
    {"name":"煙煤","value":"25.8","unit":"GJ/t"},
    {"name":"褐煤","value":"11.9","unit":"GJ/t"},
    {"name":"焦炭","value":"28.2","unit":"GJ/t"},
    {"name":"木材（乾）","value":"15.6","unit":"GJ/t"},
    {"name":"都市固廢","value":"10.0","unit":"GJ/t"},
    {"name":"生質炭","value":"29.5","unit":"GJ/t"},
]
NCV_LIQUIDS = [
    {"name":"汽油","value":"44.3","unit":"GJ/t"},
    {"name":"柴油","value":"43.0","unit":"GJ/t"},
    {"name":"燃料油","value":"40.4","unit":"GJ/t"},
    {"name":"液化石油氣(LPG)","value":"47.3","unit":"GJ/t"},
    {"name":"航空燃油","value":"44.1","unit":"GJ/t"},
    {"name":"石腦油","value":"44.5","unit":"GJ/t"},
]
NCV_GASES = [
    {"name":"天然氣","value":"48.0","unit":"GJ/t"},
    {"name":"天然氣","value":"36.0","unit":"MJ/m³"},
    {"name":"液化天然氣(LNG)","value":"44.2","unit":"GJ/t"},
    {"name":"氫氣","value":"120.0","unit":"GJ/t"},
    {"name":"焦爐氣","value":"17.5","unit":"MJ/m³"},
    {"name":"高爐氣","value":"3.3","unit":"MJ/m³"},
]

# 台灣碳費趨勢（環境部公告 + 預估）
CARBON_FEE_TREND = [
    {"year":"2025","fee":300,"type":"正式","note":"一般費率"},
    {"year":"2025","fee":100,"type":"優惠","note":"自主減量計畫"},
    {"year":"2026","fee":500,"type":"預估","note":"逐步調升"},
    {"year":"2027","fee":800,"type":"預估","note":"接軌國際"},
    {"year":"2028","fee":1200,"type":"預估","note":"達成目標"},
    {"year":"2030","fee":2000,"type":"目標","note":"長期目標"},
]

STATIC_REGULATIONS = [
    {"name":"歐盟企業永續報告指令 (CSRD)","jurisdiction":"歐盟","status":"已生效","effective_date":"2024年起分階段","summary":"要求大型企業進行標準化永續揭露，取代NFRD，適用約5萬家企業，需第三方確信。","impact_areas":["永續報告","資訊揭露","供應鏈"],"url":"https://finance.ec.europa.eu/capital-markets-union-and-financial-markets/company-reporting-and-auditing/company-reporting/corporate-sustainability-reporting_en"},
    {"name":"ISSB永續揭露準則 (IFRS S1/S2)","jurisdiction":"全球","status":"已生效","effective_date":"2023年發布","summary":"全球統一永續揭露基準，S1一般要求、S2氣候揭露，台灣、日本、英國等多國已宣布採用。","impact_areas":["氣候揭露","財務報告","永續準則"],"url":"https://www.ifrs.org/issued-standards/ifrs-sustainability-disclosure-standards/"},
    {"name":"歐盟永續金融揭露規範 (SFDR)","jurisdiction":"歐盟","status":"已生效","effective_date":"2021年起持續更新","summary":"要求金融機構揭露ESG整合方式，產品分Article 6/8/9三類，規範主要不利影響(PAI)揭露。","impact_areas":["基金管理","投資產品","ESG標籤"],"url":"https://finance.ec.europa.eu/sustainable-finance/disclosures/sustainability-related-disclosure-financial-services-sector_en"},
    {"name":"美國SEC氣候披露規則","jurisdiction":"美國","status":"即將生效","effective_date":"2025–2026年分階段","summary":"要求上市公司揭露氣候風險及Scope 1&2排放量，目前仍在司法審查中。","impact_areas":["氣候揭露","溫室氣體","上市公司"],"url":"https://www.sec.gov/rules-regulations/2024/03/the-enhancement-and-standardization-of-climate-related-disclosures"},
    {"name":"台灣上市櫃永續報告書規範","jurisdiction":"台灣","status":"已生效","effective_date":"2023年起擴大適用","summary":"金管會要求依規模分階段申報，逐步接軌ISSB，資本額20億以上須取得第三方確信。","impact_areas":["永續報告","公司治理","ESG揭露"],"url":"https://cgc.twse.com.tw/frontEN/sustainReport"},
    {"name":"台灣碳費徵收制度","jurisdiction":"台灣","status":"已生效","effective_date":"2025年正式開徵","summary":"對年排放逾2.5萬噸CO₂e業者徵收，一般費率NT$300/噸，自主減量可申請優惠費率。","impact_areas":["碳定價","製造業","能源業"],"url":"https://www.epa.gov.tw/climate/4B9E1E3855AAEE81"},
    {"name":"歐盟碳邊境調整機制 (CBAM)","jurisdiction":"歐盟","status":"已生效","effective_date":"2023年試行，2026年正式","summary":"對進口高碳產品徵碳邊境稅（鋼鐵、鋁、水泥等），防止碳洩漏，台灣出口商影響深遠。","impact_areas":["碳關稅","國際貿易","製造業"],"url":"https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism_en"},
]

# ── 抓取函式 ──────────────────────────────────────────────────────────────────

def is_valid_url(url):
    if not url or not url.startswith("http"):
        return False
    for d in BLOCKED_DOMAINS:
        if d in url:
            return False
    try:
        r = requests.get(url, headers=HEADERS, timeout=8, allow_redirects=True, stream=True)
        r.close()
        return r.status_code < 400
    except:
        return False

def clean_html(text):
    text = re.sub(r'<[^>]+>',' ', text or '')
    text = html_lib.unescape(text)
    text = re.sub(r'\s+',' ', text).strip()
    return text[:200]+'…' if len(text)>200 else text

def parse_date(entry):
    for a in ('published','updated'):
        v = getattr(entry, a, None)
        if v:
            try:
                return parsedate_to_datetime(v).astimezone(TW_TZ).strftime('%Y/%m/%d')
            except:
                return v[:10] if len(v)>=10 else v
    return '近期'

def fetch_feed(cfg, max_items=6):
    items=[]
    try:
        r=requests.get(cfg['url'],headers=HEADERS,timeout=15)
        r.raise_for_status()
        parsed=feedparser.parse(r.content)
        checked=0
        for e in parsed.entries:
            if checked>=max_items: break
            title=clean_html(e.get('title',''))
            summary=clean_html(e.get('summary','') or e.get('description',''))
            link=e.get('link','')
            if not title or len(title)<10: continue
            checked+=1
            print(f"    檢查: {title[:50]}")
            if not is_valid_url(link): continue
            items.append({'title':title,'summary':summary or '點擊標題查看詳情','source':cfg['name'],'date':parse_date(e),'category':cfg['category'],'region':cfg.get('region','全球'),'url':link})
    except Exception as ex:
        print(f"  ⚠ {cfg['name']}: {ex}")
    return items

def fetch_all(feeds, top_n=10):
    all_items=[]; seen=set()
    for f in feeds:
        if len(all_items)>=top_n: break
        print(f"  → {f['name']}")
        for item in fetch_feed(f,5):
            if len(all_items)>=top_n: break
            k=item['title'][:40].lower()
            if k not in seen:
                seen.add(k); all_items.append(item)
    for i,it in enumerate(all_items): it['rank']=i+1
    return all_items

# ── HTML 元件 ─────────────────────────────────────────────────────────────────
CAT_ICONS={"氣候":"🌍","投資":"📈","能源":"⚡","治理":"🏛️","基金":"💼","債券":"📋","評級":"⭐","法規":"📜","標準":"📐","碳市場":"♻️","碳政策":"🌿","ESG綜合":"🌱","全球":"🌐","亞洲":"🌏","歐洲":"🇪🇺","美洲":"🌎","台灣":"🇹🇼"}
STATUS_COLOR={"已生效":("badge-green","已生效"),"即將生效":("badge-amber","即將生效"),"草案":("badge-gray","草案")}

def news_card(item):
    url=item.get('url',''); cat=item.get('category',''); reg=item.get('region','')
    link=f'<a href="{url}" target="_blank" rel="noopener" class="read-more">閱讀原文 →</a>' if url else ''
    return f'''<div class="card">
      <div class="card-rank">#{item.get("rank","")}</div>
      <div class="card-body">
        <div class="card-meta"><span class="tag">{CAT_ICONS.get(cat,"📌")} {cat}</span><span class="tag">{CAT_ICONS.get(reg,"🌐")} {reg}</span></div>
        <h3 class="card-title">{item.get("title","")}</h3>
        <p class="card-summary">{item.get("summary","")}</p>
        <div class="card-footer"><span>📰 {item.get("source","")}</span><span>🗓 {item.get("date","")}</span>{link}</div>
      </div></div>'''

def reg_static_card(item, idx):
    cls,label=STATUS_COLOR.get(item.get('status','草案'),("badge-gray","草案"))
    areas=' '.join(f'<span class="tag">{a}</span>' for a in item.get('impact_areas',[]))
    url=item.get('url','')
    link=f'<a href="{url}" target="_blank" rel="noopener" class="read-more">查看詳情 →</a>' if url else ''
    jur=item.get('jurisdiction','')
    return f'''<div class="card reg-card">
      <div class="card-rank">#{idx+1}</div>
      <div class="card-body">
        <div class="card-meta"><span class="badge {cls}">{label}</span><span class="tag">{CAT_ICONS.get(jur,"🏛️")} {jur}</span></div>
        <h3 class="card-title">{item.get("name","")}</h3>
        <p class="card-summary">{item.get("summary","")}</p>
        <div class="areas">{areas}</div>
        <div class="card-footer"><span>📅 {item.get("effective_date","")}</span>{link}</div>
      </div></div>'''

def reg_news_card(item, idx):
    url=item.get('url',''); reg=item.get('region','')
    link=f'<a href="{url}" target="_blank" rel="noopener" class="read-more">閱讀原文 →</a>' if url else ''
    return f'''<div class="card reg-card">
      <div class="card-rank">◉</div>
      <div class="card-body">
        <div class="card-meta"><span class="badge badge-blue">最新動態</span><span class="tag">{CAT_ICONS.get(reg,"🌐")} {reg}</span></div>
        <h3 class="card-title">{item.get("title","")}</h3>
        <p class="card-summary">{item.get("summary","")}</p>
        <div class="card-footer"><span>📰 {item.get("source","")}</span><span>🗓 {item.get("date","")}</span>{link}</div>
      </div></div>'''

# 右欄儀表板元件
def dashboard_summary(news, market, reg_news):
    total = len(news)+len(market)+len(reg_news)
    tw_news = sum(1 for i in news+market if i.get('region')=='台灣')
    return f'''<div class="dash-card">
  <div class="dash-title">📊 本週摘要</div>
  <div class="dash-stats">
    <div class="ds-item"><div class="ds-n">{len(news)}</div><div class="ds-l">ESG新聞</div></div>
    <div class="ds-item"><div class="ds-n">{len(market)}</div><div class="ds-l">市場消息</div></div>
    <div class="ds-item"><div class="ds-n">{len(STATIC_REGULATIONS)}</div><div class="ds-l">追蹤法規</div></div>
    <div class="ds-item"><div class="ds-n">{tw_news}</div><div class="ds-l">台灣在地</div></div>
  </div>
</div>'''

def dashboard_temp():
    # 2024年全球平均氣溫距基準期(1850-1900)偏差：+1.45°C（WMO/Copernicus 2024年報）
    temp = 1.45
    pct  = min(temp / 2.0, 1.0)  # 2°C 為上限基準
    bar_w = int(pct * 100)
    color = "#ef4444" if temp >= 1.5 else "#f59e0b"
    return f'''<div class="dash-card">
  <div class="dash-title">🌡 全球暖化現況</div>
  <div style="text-align:center;padding:8px 0">
    <div style="font-size:2.4rem;font-weight:700;color:{color}">+{temp}°C</div>
    <div style="font-size:11px;color:var(--textM);margin-top:2px">相較工業化前基準期(1850–1900)</div>
    <div style="margin:10px 0 4px;background:#e5e7eb;border-radius:20px;height:10px;overflow:hidden">
      <div style="width:{bar_w}%;height:100%;background:linear-gradient(90deg,#22c55e,{color});border-radius:20px;transition:width 1s"></div>
    </div>
    <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--textM)">
      <span>0°C</span><span style="color:#f59e0b">1.5°C 警戒</span><span>2.0°C</span>
    </div>
  </div>
  <div style="font-size:11px;color:var(--textM);text-align:center;margin-top:6px">資料來源：WMO / Copernicus 2024</div>
</div>'''

def dashboard_semi():
    max_val = max(d['total'] for d in TW_SEMI_EMISSIONS)
    rows = ""
    for d in TW_SEMI_EMISSIONS:
        pct = int(d['total']/max_val*100)
        rows += f'''<tr>
          <td><span class="rank-badge">#{d["rank"]}</span></td>
          <td><strong>{d["company"]}</strong><br><span style="font-size:10px;color:var(--textM)">{d["note"]}</span></td>
          <td style="text-align:right">{d["total"]:,}</td>
          <td style="width:80px"><div style="background:#e5e7eb;border-radius:4px;height:6px"><div style="width:{pct}%;height:100%;background:var(--g400);border-radius:4px"></div></div></td>
        </tr>'''
    gas_badges = "".join(f'<span class="tag" style="font-size:10px">{g}</span>' for g in ["CO₂","CH₄","N₂O","HFCs","PFCs","SF₆","NF₃"])
    return f'''<div class="dash-card">
  <div class="dash-title">🏭 台灣半導體溫室氣體排放</div>
  <div style="font-size:11px;color:var(--textM);margin-bottom:8px">總排放量最少前5名企業｜單位：公噸CO₂e｜{gas_badges}</div>
  <table class="dash-table">
    <thead><tr><th>排名</th><th>企業</th><th>總量(t)</th><th>比例</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <div style="font-size:10px;color:var(--textM);margin-top:6px">資料來源：各企業永續報告書（2022年度）</div>
</div>'''

def dashboard_gwp():
    cat_color = {"基準氣體":"#22c55e","短效氣體":"#f59e0b","長效氣體":"#f97316","HFCs":"#8b5cf6","PFCs":"#ec4899","SF₆":"#ef4444","NF₃":"#dc2626"}
    rows = ""
    for g in GWP_DATA:
        c = cat_color.get(g['category'],'#6b7280')
        gwp_str = f"{g['gwp']:,}" if isinstance(g['gwp'], int) else str(g['gwp'])
        rows += f'<tr><td><strong>{g["gas"]}</strong></td><td style="font-family:monospace;font-size:11px">{g["formula"]}</td><td style="text-align:right;font-weight:600;color:{c}">{gwp_str}</td><td style="font-size:10px;color:var(--textM)">{g["lifetime"]}</td></tr>'
    return f'''<div class="dash-card">
  <div class="dash-title">⚗️ GWP 數值（IPCC AR6，100年期）</div>
  <table class="dash-table">
    <thead><tr><th>氣體</th><th>化學式</th><th>GWP</th><th>大氣壽命</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>'''

def dashboard_ncv():
    def rows_html(data):
        return "".join(f'<tr><td>{d["name"]}</td><td style="text-align:right;font-weight:600">{d["value"]}</td><td style="color:var(--textM);font-size:11px">{d["unit"]}</td></tr>' for d in data)
    return f'''<div class="dash-card">
  <div class="dash-title">🔥 淨熱值（低位發熱值）</div>
  <div style="font-size:11px;color:var(--textM);margin-bottom:6px">資料來源：IPCC 2006/2019 GL、IEA、EPA</div>
  <div class="ncv-tabs">
    <div class="ncv-group"><div class="ncv-label">固體</div>
    <table class="dash-table"><tbody>{rows_html(NCV_SOLIDS)}</tbody></table></div>
    <div class="ncv-group"><div class="ncv-label">液體</div>
    <table class="dash-table"><tbody>{rows_html(NCV_LIQUIDS)}</tbody></table></div>
    <div class="ncv-group"><div class="ncv-label">氣體</div>
    <table class="dash-table"><tbody>{rows_html(NCV_GASES)}</tbody></table></div>
  </div>
</div>'''

def dashboard_carbon_fee():
    max_fee = max(d['fee'] for d in CARBON_FEE_TREND)
    bars = ""
    for d in CARBON_FEE_TREND:
        h = int(d['fee']/max_fee*120)
        col = "#ef4444" if d['type']=='目標' else "#f59e0b" if d['type']=='預估' else "#4caf80" if d['type']=='優惠' else "#2d7a4f"
        bars += f'''<div class="bar-item">
          <div class="bar-tooltip">NT${d["fee"]:,}/t<br>{d["note"]}</div>
          <div class="bar-fill" style="height:{h}px;background:{col}"></div>
          <div class="bar-val">NT${d["fee"]//1000 if d["fee"]>=1000 else d["fee"]}{"K" if d["fee"]>=1000 else ""}</div>
          <div class="bar-yr">{d["year"]}</div>
        </div>'''
    legend = '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;font-size:10px">'
    for col,lbl in [("#2d7a4f","正式費率"),("#4caf80","優惠費率"),("#f59e0b","預估值"),("#ef4444","長期目標")]:
        legend += f'<span><span style="display:inline-block;width:10px;height:10px;background:{col};border-radius:2px;margin-right:3px"></span>{lbl}</span>'
    legend += '</div>'
    return f'''<div class="dash-card">
  <div class="dash-title">💰 台灣碳費收費趨勢（至2030）</div>
  <div style="font-size:11px;color:var(--textM);margin-bottom:10px">單位：NT$/公噸CO₂e｜資料來源：環境部公告及政策規劃</div>
  <div class="bar-chart">{bars}</div>
  {legend}
</div>'''

def sr_checklist():
    sections = [
        ("📋 基本資訊", ["公司概況與治理架構","報告書範疇與邊界","重大性議題鑑別矩陣","利害關係人溝通方式","永續策略與目標"]),
        ("🌍 環境面(E)", ["溫室氣體盤查(Scope 1/2/3)","能源使用與再生能源比例","用水量與水資源管理","廢棄物產生與處置","生物多樣性影響評估","產品碳足跡/水足跡"]),
        ("👥 社會面(S)", ["員工人數/離職率/多元化","薪酬結構與性別薪酬差距","教育訓練時數與費用","職業安全衛生數據","供應鏈人權盡職調查","社區投資與公益支出","客戶隱私與資料安全"]),
        ("🏛 治理面(G)", ["董事會組成與獨立性","女性董事比例","高階主管薪酬揭露","反貪腐與商業倫理政策","稅務透明度","風險管理機制","法規遵循紀錄"]),
        ("📊 對齊框架", ["GRI準則對應表","SASB指標","TCFD氣候相關揭露","SDGs貢獻對應","ISSB S1/S2（新版要求）"]),
    ]
    html = ""
    for title, items in sections:
        lis = "".join(f'<li style="font-size:11px;color:var(--text2);padding:2px 0;border-bottom:1px dotted var(--border)">{i}</li>' for i in items)
        html += f'''<div style="margin-bottom:10px">
          <div style="font-size:11px;font-weight:700;color:var(--g600);background:var(--g100);padding:3px 8px;border-radius:4px;margin-bottom:4px">{title}</div>
          <ul style="list-style:none;padding:0">{lis}</ul>
        </div>'''
    return f'''<div class="dash-card">
  <div class="dash-title">📝 永續報告書內容清單</div>
  {html}
  <div style="font-size:10px;color:var(--textM);margin-top:4px">對標 GRI Standards・ISSB・TCFD・金管會規範</div>
</div>'''

def sr_notes():
    notes = [
        ("🔴 必須注意","重大性鑑別不能自己決定，需透過利害關係人調查產出矩陣"),
        ("🔴 必須注意","數據需具可比較性：同口徑、同邊界、歷年一致"),
        ("🔴 必須注意","資本額20億以上須取得第三方確信（有限確信或合理確信）"),
        ("🟡 容易出錯","Scope 3 常被低估：員工通勤、差旅、上下游供應鏈皆需納入"),
        ("🟡 容易出錯","薪酬差距計算需說明方法論，不能只寫「符合法規」"),
        ("🟡 容易出錯","目標需 SMART：可量化、有時程、有基準年"),
        ("🟢 加分項目","設定科學基礎減量目標(SBTi)並取得認可"),
        ("🟢 加分項目","參考 SASB 產業標準，揭露產業特定指標"),
        ("🟢 加分項目","董事會層級設置永續委員會，強化治理"),
        ("🟢 加分項目","納入氣候情境分析(TCFD)：1.5°C / 2°C 兩種情境"),
        ("💡 撰寫原則","避免漂綠：數據需有來源，成效需有證明"),
        ("💡 撰寫原則","報告書應與年報/財報資訊一致，避免矛盾"),
    ]
    html = "".join(f'''<div style="display:flex;gap:6px;padding:5px 0;border-bottom:1px dotted var(--border);align-items:flex-start">
      <span style="font-size:11px;flex-shrink:0">{badge}</span>
      <span style="font-size:11px;color:var(--text2);line-height:1.5">{text}</span>
    </div>''' for badge, text in notes)
    return f'''<div class="dash-card">
  <div class="dash-title">⚠️ 撰寫注意事項</div>
  {html}
</div>'''

def sr_activities():
    cats = [
        ("🌿 環境面(E)","#22c55e",[
            ("每月","無紙化挑戰：辦公室列印量減少X%目標"),
            ("每季","員工碳足跡計算工具（通勤+飲食+購物）"),
            ("每年","植樹造林活動 / 認養城市綠地"),
            ("持續","綠色通勤：步行/自行車/大眾運輸獎勵"),
            ("持續","辦公室節電競賽，部門用電排行看板"),
            ("持續","廚餘堆肥 / 舊物循環二手市集"),
            ("特殊","淨灘/淨山志工日 / 生態導覽體驗"),
        ]),
        ("👥 社會面(S)","#3b82f6",[
            ("每月","多元共融午餐會：不同文化背景員工分享"),
            ("每季","技能共享課程：員工教員工（內部講師）"),
            ("每年","供應商稽核志工：了解供應鏈人權議題"),
            ("持續","閱讀角設置 / 書本交換平台"),
            ("持續","身心健康計畫：正念冥想、心理諮詢"),
            ("特殊","偏鄉教育志工 / 銀髮數位培訓"),
            ("特殊","捐血活動 / 物資募集公益日"),
        ]),
        ("🏛 治理面(G)","#8b5cf6",[
            ("每月","ESG小學堂：15分鐘法規與趨勢分享"),
            ("每季","員工誠信宣誓 / 反貪腐教育訓練"),
            ("每年","ESG提案競賽：員工提出改善方案"),
            ("持續","吹哨者保護管道宣導（匿名舉報系統）"),
            ("持續","ESG績效目標納入各部門KPI"),
            ("特殊","股東會模擬：讓員工了解公司治理運作"),
            ("特殊","ESG參訪：拜訪標竿企業或永續農場"),
        ]),
    ]
    html = ""
    for title, color, activities in cats:
        items = "".join(f'''<div style="display:flex;gap:6px;padding:4px 0;border-bottom:1px dotted var(--border);align-items:flex-start">
          <span style="background:{color}22;color:{color};border-radius:4px;padding:1px 5px;font-size:9px;font-weight:700;flex-shrink:0;margin-top:2px">{freq}</span>
          <span style="font-size:11px;color:var(--text2);line-height:1.4">{act}</span>
        </div>''' for freq, act in activities)
        html += f'''<div style="margin-bottom:12px">
          <div style="font-size:11px;font-weight:700;color:#fff;background:{color};padding:4px 10px;border-radius:6px;margin-bottom:6px">{title}</div>
          {items}
        </div>'''
    return f'''<div class="dash-card">
  <div class="dash-title">🎯 員工ESG參與活動建議</div>
  <div style="font-size:11px;color:var(--textM);margin-bottom:8px">從生活中落實，讓ESG成為企業文化</div>
  {html}
</div>'''

def dashboard_cbam():
    items = [
        ("🗓 時程","2023/10 過渡期開始（僅申報）<br>2026/01 正式徵收CBAM憑證費用"),
        ("📦 適用產品","鋼鐵、鋁、水泥、化肥、電力、氫氣<br>（2026年後預計擴大至更多產品）"),
        ("💶 憑證價格","連動 EU ETS 碳價<br>目前約 €60–70 / tCO₂e"),
        ("🇹🇼 台灣影響","鋼鐵（中鋼等）、鋁業出口商首當其衝<br>需提供產品碳含量申報文件"),
        ("📋 申報義務","出口商須提交：生產國碳價、<br>產品直接/間接排放量、CBAM申報書"),
        ("🔴 最新動態","歐洲議會2024年討論擴大至<br>有機化學品、塑料、橡膠等產品"),
    ]
    rows = "".join(f'<tr><td style="color:var(--g600);font-weight:600;white-space:nowrap;font-size:11px">{k}</td><td style="font-size:11px;line-height:1.5">{v}</td></tr>' for k,v in items)
    return f'''<div class="dash-card">
  <div class="dash-title">🌍 CBAM 碳邊境調整機制最新資訊</div>
  <table class="dash-table"><tbody>{rows}</tbody></table>
  <div style="font-size:10px;color:var(--textM);margin-top:6px">資料來源：歐盟官方公報・環境部・工業總會</div>
</div>'''

def dashboard_tw_carbon_2027():
    tiers = [
        ("#2d7a4f","一般費率","NT$300/t","2025年","已公告，適用未提減量計畫者"),
        ("#4caf80","優惠費率A","NT$50/t","2025年","提交自主減量計畫且達標"),
        ("#f59e0b","一般費率","NT$500–800/t","2026–2027年","預估，視減碳進展調升"),
        ("#ef4444","長期目標","NT$1,200+/t","2030年","接軌歐盟碳價水準"),
    ]
    rows = "".join(f'<tr><td><span style="display:inline-block;width:8px;height:8px;background:{c};border-radius:50%;margin-right:4px"></span><span style="font-size:11px">{n}</span></td><td style="font-weight:700;font-size:12px;color:{c}">{f}</td><td style="font-size:10px;color:var(--textM)">{y}</td></tr>' for c,n,f,y,_ in tiers)
    notes = "".join(f'<li style="font-size:10px;color:var(--textM);margin-bottom:2px">{n} → {d}</li>' for _,n,f,y,d in tiers)
    return f'''<div class="dash-card">
  <div class="dash-title">💰 2027 台灣碳費收費標準</div>
  <div style="font-size:11px;color:var(--textM);margin-bottom:8px">徵收對象：年排放 ≥ 25,000 tCO₂e 業者（電力、鋼鐵、石化、水泥等）</div>
  <table class="dash-table"><thead><tr><th>費率類型</th><th>費率</th><th>年度</th></tr></thead><tbody>{rows}</tbody></table>
  <ul style="margin-top:8px;padding-left:4px;list-style:none">{notes}</ul>
  <div style="font-size:10px;color:var(--textM);margin-top:6px">* 2026年後費率為政策預估值，以環境部正式公告為準</div>
</div>'''

def dashboard_enterprise_response():
    steps = [
        ("1","立即","完成碳盤查","依 ISO 14064-1 盤查 Scope 1+2+3<br>取得第三方查驗，建立排放基準年"),
        ("2","短期","申請優惠費率","向環境部提交自主減量計畫<br>費率可從 NT$300 降至 NT$50/t"),
        ("3","短期","購買綠電/憑證","簽訂企業購電協議(CPPA)<br>採購再生能源憑證(T-REC/I-REC)"),
        ("4","中期","設定 SBTi 目標","加入科學基礎減量目標倡議<br>取得國際認可，強化品牌形象"),
        ("5","中期","供應鏈碳管理","要求供應商申報碳足跡<br>建立低碳採購標準"),
        ("6","長期","碳權抵換準備","參與台灣自願減量額度(VCS/Gold)<br>預備碳信用買賣抵換機制"),
    ]
    cards = ""
    for no, timing, title, desc in steps:
        color = "#2d7a4f" if timing=="立即" else "#f59e0b" if timing=="短期" else "#8b5cf6"
        cards += f'''<div style="border:1px solid var(--border);border-left:3px solid {color};border-radius:6px;padding:7px 10px;margin-bottom:6px">
          <div style="display:flex;align-items:center;gap:6px;margin-bottom:3px">
            <span style="background:{color};color:#fff;border-radius:50%;width:18px;height:18px;display:inline-flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;flex-shrink:0">{no}</span>
            <span style="font-weight:600;font-size:12px">{title}</span>
            <span style="margin-left:auto;background:{color}22;color:{color};border-radius:10px;padding:1px 7px;font-size:10px;font-weight:600">{timing}</span>
          </div>
          <div style="font-size:11px;color:var(--text2);line-height:1.5;padding-left:24px">{desc}</div>
        </div>'''
    return f'''<div class="dash-card">
  <div class="dash-title">🏢 企業因應碳費六大行動</div>
  {cards}
  <div style="font-size:10px;color:var(--textM);margin-top:4px">資料來源：環境部・工業局・永續發展目標(SDGs)・SBTi</div>
</div>'''

# ── 主 HTML ───────────────────────────────────────────────────────────────────
def build_html(news, market, reg_news):
    news_html      = '\n'.join(news_card(i) for i in news)
    market_html    = '\n'.join(news_card(i) for i in market)
    stat_reg_html  = '\n'.join(reg_static_card(r,i) for i,r in enumerate(STATIC_REGULATIONS))
    live_reg_html  = '\n'.join(reg_news_card(r,i) for i,r in enumerate(reg_news))

    right_col = (
        dashboard_summary(news, market, reg_news) +
        dashboard_temp() +
        dashboard_cbam() + 
        dashboard_tw_carbon_2027() +
        dashboard_enterprise_response() +
        dashboard_semi() +
        dashboard_gwp() +
        dashboard_ncv() +
        dashboard_carbon_fee()
    )

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>ESG 每週報告 | {DATE_STR}</title>
<style>
:root{{
  --g900:#0d2e1a;--g800:#1a4d2e;--g600:#2d7a4f;--g400:#4caf80;--g100:#e8f5ee;
  --amber:#f59e0b;--amberL:#fef3c7;--blue:#2563eb;--blueL:#dbeafe;
  --text1:#1a2e1f;--text2:#4b6358;--textM:#7a9488;
  --border:#c8e6d4;--bg:#f5fbf7;--card:#fff;--r-lg:14px;--r-md:8px;
}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Noto Sans TC',system-ui,sans-serif;background:var(--bg);color:var(--text1);line-height:1.7;font-size:14px}}
/* ── Header ── */
.header{{background:var(--g900);color:#fff;padding:2rem 2rem 1.5rem;text-align:center}}
.h-badge{{display:inline-block;background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.25);border-radius:20px;padding:3px 12px;font-size:11px;letter-spacing:.06em;margin-bottom:.75rem}}
.header h1{{font-size:clamp(1.5rem,3vw,2.2rem);font-weight:700;margin-bottom:.3rem}}
.header h1 span{{color:var(--g400)}}
.header p{{opacity:.7;margin-bottom:1.5rem;font-size:13px}}
.stats{{display:flex;justify-content:center;gap:1.5rem;flex-wrap:wrap}}
.stat{{text-align:center}}
.stat-n{{font-size:1.6rem;font-weight:700;color:var(--g400);line-height:1}}
.stat-l{{font-size:10px;opacity:.6;margin-top:2px}}
.free-badge{{display:inline-block;background:rgba(76,175,128,.2);border:1px solid var(--g400);color:var(--g400);border-radius:20px;padding:2px 10px;font-size:11px;margin-top:.75rem}}
/* ── Nav ── */
nav{{position:sticky;top:0;z-index:100;background:var(--card);border-bottom:1px solid var(--border);padding:0 1.5rem;display:flex;overflow-x:auto;box-shadow:0 2px 8px rgba(0,0,0,.06)}}
nav a{{display:flex;align-items:center;gap:5px;padding:.75rem 1rem;color:var(--text2);text-decoration:none;font-size:13px;font-weight:500;white-space:nowrap;border-bottom:3px solid transparent;transition:.2s}}
nav a:hover{{color:var(--g600);border-color:var(--g400)}}
/* ── Layout ── */
.layout{{display:grid;grid-template-columns:1fr 340px 300px;gap:1.5rem;max-width:1440px;margin:0 auto;padding:1.5rem}}
@media(max-width:1100px){{.layout{{grid-template-columns:1fr 320px}}}}
@media(max-width:800px){{.layout{{grid-template-columns:1fr}}}}
/* ── Left column ── */
.section{{margin-bottom:2.5rem}}
.sec-head{{display:flex;align-items:center;gap:10px;margin-bottom:1.25rem;padding-bottom:.75rem;border-bottom:2px solid var(--g100)}}
.sec-icon{{width:38px;height:38px;background:var(--g100);border-radius:var(--r-md);display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0}}
.sec-head h2{{font-size:1.1rem;font-weight:700;color:var(--g900)}}
.sec-head p{{font-size:11px;color:var(--textM);margin-top:1px}}
.sec-cnt{{margin-left:auto;background:var(--g100);color:var(--g600);padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600;white-space:nowrap}}
.cards{{display:flex;flex-direction:column;gap:.75rem}}
.card{{background:var(--card);border:1px solid var(--border);border-left:4px solid var(--g400);border-radius:var(--r-lg);padding:1rem 1.25rem;display:flex;gap:.75rem;transition:.15s}}
.card:hover{{transform:translateY(-1px);box-shadow:0 4px 16px rgba(45,122,79,.1)}}
.reg-card{{border-left-color:var(--blue)}}
.card-rank{{font-size:1.2rem;font-weight:800;color:var(--g100);min-width:36px;text-align:center;padding-top:1px;line-height:1}}
.card-body{{flex:1;min-width:0}}
.card-meta{{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:6px}}
.card-title{{font-size:.9rem;font-weight:600;color:var(--text1);margin-bottom:4px;line-height:1.4}}
.card-summary{{font-size:12px;color:var(--text2);line-height:1.6}}
.card-footer{{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin-top:8px;font-size:11px;color:var(--textM)}}
.areas{{display:flex;flex-wrap:wrap;gap:4px;margin-top:6px}}
.badge{{display:inline-block;padding:2px 7px;border-radius:20px;font-size:10px;font-weight:600}}
.badge-green{{background:var(--g100);color:var(--g600)}}
.badge-amber{{background:var(--amberL);color:#92400e}}
.badge-gray{{background:#f1efeb;color:#5f5e5a}}
.badge-blue{{background:var(--blueL);color:var(--blue)}}
.tag{{display:inline-block;padding:2px 7px;background:var(--bg);border:1px solid var(--border);border-radius:20px;font-size:10px;color:var(--text2)}}
.read-more{{color:var(--g600);text-decoration:none;font-weight:500;font-size:11px;margin-left:auto;white-space:nowrap}}
.read-more:hover{{text-decoration:underline}}
.divider{{display:flex;align-items:center;gap:8px;margin:1rem 0;font-size:11px;color:var(--textM)}}
.divider::before,.divider::after{{content:'';flex:1;border-top:1px dashed var(--border)}}
.empty{{text-align:center;padding:1.5rem;color:var(--textM);font-size:13px}}
/* ── Right column (dashboard) ── */
.right-col{{display:flex;flex-direction:column;gap:1rem}}
.dash-card{{background:var(--card);border:1px solid var(--border);border-radius:var(--r-lg);padding:1rem 1.1rem}}
.dash-title{{font-size:.85rem;font-weight:700;color:var(--g900);margin-bottom:.75rem;padding-bottom:.5rem;border-bottom:1px solid var(--g100)}}
.dash-stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:.5rem;text-align:center}}
.ds-item{{background:var(--bg);border-radius:var(--r-md);padding:.5rem .25rem}}
.ds-n{{font-size:1.4rem;font-weight:700;color:var(--g600);line-height:1}}
.ds-l{{font-size:10px;color:var(--textM);margin-top:2px}}
/* dashboard table */
.dash-table{{width:100%;border-collapse:collapse;font-size:12px}}
.dash-table th{{background:var(--bg);padding:4px 6px;text-align:left;font-size:10px;color:var(--textM);font-weight:600;border-bottom:1px solid var(--border)}}
.dash-table td{{padding:5px 6px;border-bottom:1px solid var(--g100);vertical-align:middle}}
.dash-table tr:last-child td{{border-bottom:none}}
.rank-badge{{display:inline-block;background:var(--g100);color:var(--g600);border-radius:4px;padding:1px 5px;font-size:10px;font-weight:700}}
/* NCV tabs */
.ncv-tabs{{display:flex;flex-direction:column;gap:.5rem}}
.ncv-group{{}}
.ncv-label{{font-size:10px;font-weight:600;color:var(--g600);background:var(--g100);padding:2px 8px;border-radius:4px;display:inline-block;margin-bottom:3px}}
/* bar chart */
.bar-chart{{display:flex;align-items:flex-end;gap:6px;height:140px;padding:4px 0}}
.bar-item{{display:flex;flex-direction:column;align-items:center;flex:1;position:relative;cursor:default}}
.bar-item:hover .bar-tooltip{{display:block}}
.bar-tooltip{{display:none;position:absolute;bottom:100%;left:50%;transform:translateX(-50%);background:var(--g900);color:#fff;padding:4px 8px;border-radius:6px;font-size:10px;white-space:nowrap;z-index:10;margin-bottom:4px}}
.bar-fill{{width:100%;border-radius:4px 4px 0 0;min-height:4px}}
.bar-val{{font-size:9px;font-weight:600;color:var(--text2);margin-top:2px}}
.bar-yr{{font-size:9px;color:var(--textM)}}
/* Footer */
footer{{background:var(--g900);color:rgba(255,255,255,.6);text-align:center;padding:1.5rem;font-size:12px;margin-top:1rem}}
footer strong{{color:rgba(255,255,255,.9)}}
</style>
</head>
<body>

<header class="header">
  <div class="h-badge">🌿 ESG WEEKLY INTELLIGENCE</div>
  <h1>全球 <span>ESG</span> 週報</h1>
  <p>{DATE_STR} &nbsp;·&nbsp; {WEEK_STR} &nbsp;·&nbsp; 全球 + 台灣</p>
  <div class="stats">
    <div class="stat"><div class="stat-n">{len(news)}</div><div class="stat-l">精選新聞</div></div>
    <div class="stat"><div class="stat-n">{len(market)}</div><div class="stat-l">市場消息</div></div>
    <div class="stat"><div class="stat-n">{len(STATIC_REGULATIONS)}</div><div class="stat-l">追蹤法規</div></div>
    <div class="stat"><div class="stat-n">{len(reg_news)}</div><div class="stat-l">法規動態</div></div>
  </div>
  <div class="free-badge">✅ 完全免費 · 連結已驗證可直接閱讀</div>
</header>

<nav>
  <a href="#news">📰 全球+台灣新聞</a>
  <a href="#market">📊 市場消息</a>
  <a href="#regulations">🏛 法規追蹤</a>
</nav>

<div class="layout">
  <!-- ── 左欄：新聞資訊 ── -->
  <div class="left-col">

    <section class="section" id="news">
      <div class="sec-head">
        <div class="sec-icon">📰</div>
        <div><h2>ESG 全球 + 台灣新聞</h2><p>Google News 彙整，每筆連結皆已驗證可開啟</p></div>
        <span class="sec-cnt">{'Top '+str(len(news)) if news else '本週暫無'}</span>
      </div>
      <div class="cards">{news_html or '<div class="empty">本週暫無有效新聞連結</div>'}</div>
    </section>

    <section class="section" id="market">
      <div class="sec-head">
        <div class="sec-icon">📊</div>
        <div><h2>ESG 市場消息</h2><p>綠色債券、ESG基金、碳市場、評級最新動態</p></div>
        <span class="sec-cnt">{'Top '+str(len(market)) if market else '本週暫無'}</span>
      </div>
      <div class="cards">{market_html or '<div class="empty">本週暫無有效市場消息連結</div>'}</div>
    </section>

    <section class="section" id="regulations">
      <div class="sec-head">
        <div class="sec-icon">🏛</div>
        <div><h2>ESG 法規動態</h2><p>全球與台灣重要法規持續追蹤</p></div>
        <span class="sec-cnt">{len(STATIC_REGULATIONS)+len(reg_news)} 項</span>
      </div>
      <div class="divider">📋 重要法規持續追蹤</div>
      <div class="cards">{stat_reg_html}</div>
      <div class="divider">🔴 本週最新法規動態</div>
      <div class="cards">{live_reg_html or '<div class="empty">本週暫無有效法規動態連結</div>'}</div>
    </section>

  </div>

  <!-- ── 右欄：儀表板 ── -->
  <div class="right-col">
    {right_col}
  </div>

  <!-- ── 第三欄：永續報告書指引 ── -->
  <div class="right-col">
    {third_col}
        sr_checklist() +
        sr_notes() +
        sr_activities()
    )
  </div>
</div>

<footer>
  <p><strong>ESG 智能週報（免費版）</strong> &nbsp;·&nbsp; 資料來源：Google News RSS · IPCC AR6 · WMO · 環境部 · 各企業永續報告書 &nbsp;·&nbsp; {DATE_STR} 更新</p>
  <p style="margin-top:4px">所有新聞連結已自動驗證可開啟 · 本報告僅供參考，投資決策請諮詢專業人士</p>
</footer>
</body>
</html>"""

# ── 主程式 ────────────────────────────────────────────────────────────────────
def main():
    print(f"🌿 ESG 免費週報生成開始 — {DATE_STR}\n")
    print("📰 抓取全球+台灣新聞...")
    news = fetch_all(NEWS_FEEDS, top_n=10)
    print("\n📊 抓取市場消息...")
    market = fetch_all(MARKET_FEEDS, top_n=10)
    print("\n🏛 抓取法規動態...")
    reg_news = fetch_all(REGULATION_FEEDS, top_n=5)
    print("\n🎨 生成 HTML...")
    html = build_html(news, market, reg_news)
    os.makedirs("docs/archive", exist_ok=True)
    with open("docs/index.html","w",encoding="utf-8") as f: f.write(html)
    with open(f"docs/archive/{FILENAME}.html","w",encoding="utf-8") as f: f.write(html)
    print(f"\n🎉 完成！新聞:{len(news)} | 市場:{len(market)} | 法規動態:{len(reg_news)}")

if __name__ == "__main__":
    main()
    
