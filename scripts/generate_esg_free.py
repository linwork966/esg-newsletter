"""
ESG Weekly Newsletter - 完全免費版（三欄版）
左欄：新聞 / 市場 / 法規
中欄：摘要儀表板 / 全球暖化 / CBAM / 碳費 / 企業因應 / 半導體排放 / GWP / 淨熱值 / 碳費趨勢
右欄：永續報告書內容清單 / 撰寫注意事項 / 員工ESG活動建議
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

# 過濾低價值新聞：得獎、排名、公司內部宣傳
NOISE_KEYWORDS = [
    'award','wins the','named as','honored','ranked','recognition award',
    'best company','top 100','most admired','index inclusion','joins the',
    '得獎','獲獎','榮獲','獲選','榜單','百大','最佳企業','列入指數',
    'earns prominent','earns award','receives award','wins award',
]
def is_noise(title):
    tl = title.lower()
    return any(k in tl for k in NOISE_KEYWORDS)
HEADERS = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

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

TW_SEMI_EMISSIONS = [
    # 資料來源：各企業 2023 年度永續報告書（2024年公告）
    {"rank":1,"company":"聯詠科技","co2":8102,"ch4":0,"n2o":17,"hfcs":0,"pfcs":0,"sf6":0,"nf3":0,"total":8119,"note":"Fabless","year":"2023"},
    {"rank":2,"company":"瑞昱半導體","co2":54800,"ch4":4,"n2o":31,"hfcs":0,"pfcs":0,"sf6":0,"nf3":0,"total":54835,"note":"Fabless","year":"2023"},
    {"rank":3,"company":"聯發科技","co2":108500,"ch4":15,"n2o":52,"hfcs":0,"pfcs":145,"sf6":0,"nf3":0,"total":108712,"note":"Fabless","year":"2023"},
    {"rank":4,"company":"世界先進","co2":368000,"ch4":590,"n2o":265,"hfcs":190,"pfcs":1720,"sf6":295,"nf3":2480,"total":373540,"note":"Foundry","year":"2023"},
    {"rank":5,"company":"力積電","co2":395000,"ch4":780,"n2o":350,"hfcs":140,"pfcs":1980,"sf6":450,"nf3":3050,"total":401750,"note":"Foundry","year":"2023"},
]
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
NCV_SOLIDS = [
    # 保留與半導體/光電業相關的固體燃料
    {"name":"焦炭（製程用）","value":"28.2","unit":"GJ/t"},
    {"name":"都市固廢（RDF）","value":"10.0","unit":"GJ/t"},
]
NCV_LIQUIDS = [
    {"name":"汽油","value":"44.3","unit":"GJ/t"},{"name":"柴油","value":"43.0","unit":"GJ/t"},
    {"name":"燃料油","value":"40.4","unit":"GJ/t"},{"name":"液化石油氣(LPG)","value":"47.3","unit":"GJ/t"},
    {"name":"航空燃油","value":"44.1","unit":"GJ/t"},{"name":"石腦油","value":"44.5","unit":"GJ/t"},
]
NCV_GASES = [
    {"name":"天然氣","value":"48.0","unit":"GJ/t"},{"name":"天然氣","value":"36.0","unit":"MJ/m³"},
    {"name":"液化天然氣(LNG)","value":"44.2","unit":"GJ/t"},{"name":"氫氣","value":"120.0","unit":"GJ/t"},
    {"name":"焦爐氣","value":"17.5","unit":"MJ/m³"},{"name":"高爐氣","value":"3.3","unit":"MJ/m³"},
]
CARBON_FEE_TREND = [
    {"year":"2025","fee":300,"type":"正式","note":"一般費率（已公告）"},
    {"year":"2025","fee":50,"type":"優惠","note":"自主減量優惠費率"},
    {"year":"2026","fee":450,"type":"預估","note":"環境部滾動檢討"},
    {"year":"2027","fee":750,"type":"預估","note":"接軌國際碳價"},
    {"year":"2028","fee":1100,"type":"預估","note":"持續調升"},
    {"year":"2030","fee":1800,"type":"目標","note":"長期政策目標"},
]
STATIC_REGULATIONS = [
    {
        "name":"歐盟企業永續報告指令 (CSRD)",
        "jurisdiction":"歐盟","status":"已生效",
        "effective_date":"2024–2025年分階段生效",
        "summary":"2024年大型上市公司首批適用。2025年2月歐盟提出Omnibus簡化提案，擬將強制適用範圍從5萬家縮減至約1千家，仍待歐洲議會及各國審議，預計2026年明朗化。",
        "impact_areas":["永續報告","資訊揭露","供應鏈管理"],"url":"https://finance.ec.europa.eu/capital-markets-union-and-financial-markets/company-reporting-and-auditing/company-reporting/corporate-sustainability-reporting_en"
    },
    {
        "name":"ISSB 永續揭露準則 (IFRS S1/S2)",
        "jurisdiction":"全球","status":"已生效",
        "effective_date":"2023年正式發布，各國接軌中",
        "summary":"2023年6月正式發布 S1（一般永續揭露）& S2（氣候相關揭露）。台灣金管會2024年宣布2027年起強制接軌，日本2025年試行，澳洲2025年強制，全球逾25國承諾採用。",
        "impact_areas":["氣候揭露","財務報告","永續準則"],"url":"https://www.ifrs.org/issued-standards/ifrs-sustainability-disclosure-standards/"
    },
    {
        "name":"歐盟永續金融揭露規範 (SFDR)",
        "jurisdiction":"歐盟","status":"已生效",
        "effective_date":"2021年起，2023年修訂審查中",
        "summary":"要求金融機構揭露ESG整合方式，產品分 Article 6/8/9 三類。2023年歐盟展開全面修訂（SFDR Review），評估改用「永續」與「轉型」兩類標籤取代現行分類，預計2025–2026年公布修訂版本。",
        "impact_areas":["基金管理","投資產品","ESG標籤"],"url":"https://finance.ec.europa.eu/sustainable-finance/disclosures/sustainability-related-disclosure-financial-services-sector_en"
    },
    {
        "name":"美國 SEC 氣候披露規則",
        "jurisdiction":"美國","status":"暫緩執行",
        "effective_date":"2024年通過，司法審查暫緩",
        "summary":"2024年3月通過，要求大型上市公司揭露氣候風險與 Scope 1&2 排放量。2024年4月聯邦法院裁定暫停執行，SEC自願暫緩，預計2025年進一步釐清法律效力。",
        "impact_areas":["氣候揭露","溫室氣體","上市公司"],"url":"https://www.sec.gov/rules-regulations/2024/03/the-enhancement-and-standardization-of-climate-related-disclosures"
    },
    {
        "name":"台灣永續報告書 ISSB 接軌路徑",
        "jurisdiction":"台灣","status":"已生效",
        "effective_date":"2023–2027年分階段",
        "summary":"金管會2023年公告接軌 ISSB 路徑：2024年上市櫃公司依 GRI 申報，2026年資本額100億以上試行 ISSB 格式，2027年全面強制，第三方確信範圍同步擴大。",
        "impact_areas":["永續報告","公司治理","ESG揭露"],"url":"https://cgc.twse.com.tw/frontEN/sustainReport"
    },
    {
        "name":"台灣碳費徵收制度",
        "jurisdiction":"台灣","status":"已生效",
        "effective_date":"2025年1月正式開徵",
        "summary":"2025年正式開徵，首批約500家年排放逾2.5萬噸 CO₂e 業者納管。一般費率 NT$300/t；提交自主減量計畫可申請優惠費率 NT$50/t（達標）或 NT$100/t（未達標但申請中）。",
        "impact_areas":["碳定價","製造業","能源業"],"url":"https://www.epa.gov.tw/climate/4B9E1E3855AAEE81"
    },
    {
        "name":"歐盟碳邊境調整機制 (CBAM)",
        "jurisdiction":"歐盟","status":"已生效",
        "effective_date":"2023年10月試行，2026年1月正式",
        "summary":"2023年10月至2025年12月為過渡期（僅申報義務）。2026年1月起正式對鋼鐵、鋁、水泥、化肥、電力、氫氣徵收憑證費用，連動 EU ETS 碳價（2024均價約 €55–65/t），台灣中鋼等出口商積極準備。",
        "impact_areas":["碳關稅","國際貿易","製造業"],"url":"https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism_en"
    },
    {
        "name":"科學基礎減量目標 (SBTi) 2024更新",
        "jurisdiction":"全球","status":"已生效",
        "effective_date":"2024年更新認證標準",
        "summary":"2024年 SBTi 發布更新版企業標準，強化 1.5°C 路徑要求，縮短 Scope 3 納入期限，並新增金融機構及高排放產業特定指引。全球超過7,000家企業已提交或承諾設定目標。",
        "impact_areas":["企業減碳","供應鏈","國際認可"],"url":"https://sciencebasedtargets.org/companies-taking-action"
    },
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
            if is_noise(title): continue  # 過濾得獎/排名類新聞
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

# ── HTML 卡片元件 ─────────────────────────────────────────────────────────────
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
    url=item.get('url',''); jur=item.get('jurisdiction','')
    link=f'<a href="{url}" target="_blank" rel="noopener" class="read-more">查看詳情 →</a>' if url else ''
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

# ── 中欄儀表板元件 ────────────────────────────────────────────────────────────
def dashboard_summary(news, market, reg_news):
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
    years_data = [
        ("2020","+1.24\u00b0C","#22c55e",55),
        ("2021","+1.17\u00b0C","#22c55e",52),
        ("2022","+1.26\u00b0C","#f59e0b",56),
        ("2023","+1.45\u00b0C","#f59e0b",65),
        ("2024","+1.60\u00b0C","#ef4444",72),
    ]
    bars = "".join(
        '<div style="text-align:center;flex:1">' +
        f'<div style="font-size:14px;font-weight:600;color:{c};margin-bottom:2px">{v}</div>' +
        f'<div style="height:{h}px;background:{c};border-radius:3px 3px 0 0;margin:0 3px"></div>' +
        f'<div style="font-size:14px;color:var(--textM);margin-top:2px">{y}</div></div>'
        for y,v,c,h in years_data
    )
    return (
        '<div class="dash-card">' +
        '<div class="dash-title">\U0001f321 全球暖化現況</div>' +
        '<div style="text-align:center;padding:6px 0 10px">' +
        '<div style="font-size:3.6rem;font-weight:700;color:#ef4444">+1.60\u00b0C</div>' +
        '<div style="font-size:16px;color:#ef4444;font-weight:600;margin-top:2px">\u26a0\ufe0f 首度突破 1.5\u00b0C 巴黎警戒線</div>' +
        '<div style="font-size:14px;color:var(--textM);margin-top:2px">2024年全年均值 \u00b7 相較工業化前(1850\u20131900)</div>' +
        '</div>' +
        f'<div style="display:flex;align-items:flex-end;height:100px;border-bottom:1px solid var(--border);margin-bottom:8px;padding:4px 0 0">{bars}</div>' +
        '<div style="display:flex;justify-content:space-between;font-size:14px;color:var(--textM)">' +
        '<span>\U0001f4c8 5年升溫加速趨勢</span><span style="color:#ef4444">巴黎目標：\u2264+1.5\u00b0C</span>' +
        '</div>' +
        '<div style="font-size:14px;color:var(--textM);margin-top:4px">資料來源：Copernicus CCS / WMO State of Global Climate 2025</div>' +
        '</div>'
    )

def dashboard_cbam():
    items=[
        ("🗓 時程","2023/10–2025/12 過渡期（僅申報義務）<br>2026/01 正式徵收 CBAM 憑證費用"),
        ("📦 適用產品","鋼鐵、鋁、水泥、化肥、電力、氫氣（第一批）<br>2026年後擴大：化學品、塑料、橡膠研議中"),
        ("💶 憑證價格","連動 EU ETS 碳價<br>2024年均價約 €55–65 / tCO₂e（較2023高點回落）"),
        ("🇹🇼 台灣影響","中鋼、東和鋼鐵、台鋁等出口商首當其衝<br>2025年已開始準備產品碳含量申報文件"),
        ("📋 申報義務","須提交：出口品碳含量、生產國已付碳價<br>差額由進口商購買 CBAM 憑證補足"),
        ("🔴 2025最新","歐盟 Omnibus 提案：擬鬆綁部分CSRD要求<br>但 CBAM 範圍維持不變，如期2026執行"),
    ]
    rows="".join(f'<tr><td style="color:var(--g600);font-weight:600;white-space:nowrap;font-size:16px">{k}</td><td style="font-size:16px;line-height:1.5">{v}</td></tr>' for k,v in items)
    return f'''<div class="dash-card">
  <div class="dash-title">🌍 CBAM 碳邊境調整機制最新資訊</div>
  <table class="dash-table"><tbody>{rows}</tbody></table>
  <div style="font-size:15px;color:var(--textM);margin-top:6px">資料來源：歐盟官方公報・環境部・工業總會</div>
</div>'''

def dashboard_tw_carbon_2027():
    tiers=[
        ("#2d7a4f","一般費率","NT$300/t","2025年","已公告，適用未提減量計畫者"),
        ("#4caf80","優惠費率A","NT$50/t","2025年","提交自主減量計畫且達標"),
        ("#f59e0b","一般費率","NT$500–800/t","2026–2027年","預估，視減碳進展調升"),
        ("#ef4444","長期目標","NT$1,200+/t","2030年","接軌歐盟碳價水準"),
    ]
    rows="".join(f'<tr><td><span style="display:inline-block;width:8px;height:8px;background:{c};border-radius:50%;margin-right:4px"></span><span style="font-size:16px">{n}</span></td><td style="font-weight:700;font-size:18px;color:{c}">{f}</td><td style="font-size:15px;color:var(--textM)">{y}</td></tr>' for c,n,f,y,_ in tiers)
    notes="".join(f'<li style="font-size:15px;color:var(--textM);margin-bottom:2px">{n} → {d}</li>' for _,n,f,y,d in tiers)
    return f'''<div class="dash-card">
  <div class="dash-title">💰 台灣碳費費率（2025–2030）</div>
  <div style="font-size:16px;color:var(--textM);margin-bottom:8px">徵收對象：年排放 ≥ 25,000 tCO₂e 業者</div>
  <table class="dash-table"><thead><tr><th>費率類型</th><th>費率</th><th>年度</th></tr></thead><tbody>{rows}</tbody></table>
  <ul style="margin-top:8px;padding-left:4px;list-style:none">{notes}</ul>
  <div style="font-size:15px;color:var(--textM);margin-top:6px">* 2026年後費率為政策預估值，以環境部正式公告為準</div>
</div>'''

def dashboard_enterprise_response():
    steps=[
        ("1","立即","完成碳盤查","依 ISO 14064-1 盤查 Scope 1+2+3<br>取得第三方查驗，建立排放基準年"),
        ("2","短期","申請優惠費率","向環境部提交自主減量計畫<br>費率可從 NT$300 降至 NT$50/t"),
        ("3","短期","購買綠電/憑證","簽訂企業購電協議(CPPA)<br>採購再生能源憑證(T-REC/I-REC)"),
        ("4","中期","設定 SBTi 目標","加入科學基礎減量目標倡議<br>取得國際認可，強化品牌形象"),
        ("5","中期","供應鏈碳管理","要求供應商申報碳足跡<br>建立低碳採購標準"),
        ("6","長期","碳權抵換準備","參與台灣自願減量額度(VCS/Gold)<br>預備碳信用買賣抵換機制"),
    ]
    cards=""
    for no,timing,title,desc in steps:
        color="#2d7a4f" if timing=="立即" else "#f59e0b" if timing=="短期" else "#8b5cf6"
        cards+=f'''<div style="border:1px solid var(--border);border-left:3px solid {color};border-radius:6px;padding:7px 10px;margin-bottom:6px">
          <div style="display:flex;align-items:center;gap:6px;margin-bottom:3px">
            <span style="background:{color};color:#fff;border-radius:50%;width:18px;height:18px;display:inline-flex;align-items:center;justify-content:center;font-size:15px;font-weight:700;flex-shrink:0">{no}</span>
            <span style="font-weight:600;font-size:18px">{title}</span>
            <span style="margin-left:auto;background:{color}22;color:{color};border-radius:10px;padding:1px 7px;font-size:15px;font-weight:600">{timing}</span>
          </div>
          <div style="font-size:16px;color:var(--text2);line-height:1.5;padding-left:24px">{desc}</div>
        </div>'''
    return f'''<div class="dash-card">
  <div class="dash-title">🏢 企業因應碳費六大行動</div>
  {cards}
  <div style="font-size:15px;color:var(--textM);margin-top:4px">資料來源：環境部・工業局・SBTi</div>
</div>'''

def dashboard_semi():
    max_val=max(d['total'] for d in TW_SEMI_EMISSIONS)
    rows=""
    for d in TW_SEMI_EMISSIONS:
        pct=int(d['total']/max_val*100)
        rows+=f'''<tr>
          <td><span class="rank-badge">#{d["rank"]}</span></td>
          <td><strong>{d["company"]}</strong><br><span style="font-size:15px;color:var(--textM)">{d["note"]}</span></td>
          <td style="text-align:right">{d["total"]:,}</td>
          <td style="width:80px"><div style="background:#e5e7eb;border-radius:4px;height:6px"><div style="width:{pct}%;height:100%;background:var(--g400);border-radius:4px"></div></div></td>
        </tr>'''
    gas_badges="".join(f'<span class="tag" style="font-size:15px">{g}</span>' for g in ["CO₂","CH₄","N₂O","HFCs","PFCs","SF₆","NF₃"])
    return f'''<div class="dash-card">
  <div class="dash-title">🏭 台灣半導體溫室氣體排放</div>
  <div style="font-size:16px;color:var(--textM);margin-bottom:8px">總排放量最少前5名｜單位：公噸CO₂e｜{gas_badges}</div>
  <table class="dash-table">
    <thead><tr><th>排名</th><th>企業</th><th>總量(t)</th><th>比例</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <div style="font-size:15px;color:var(--textM);margin-top:6px">資料來源：各企業永續報告書（2023年度，部分為估算值）</div>
</div>'''

def dashboard_gwp():  # IPCC AR6 (2021) 為目前最新官方GWP標準，預計AR7約2027年發布
    cat_color={"基準氣體":"#22c55e","短效氣體":"#f59e0b","長效氣體":"#f97316","HFCs":"#8b5cf6","PFCs":"#ec4899","SF₆":"#ef4444","NF₃":"#dc2626"}
    rows=""
    for g in GWP_DATA:
        c=cat_color.get(g['category'],'#6b7280')
        gwp_str=f"{g['gwp']:,}" if isinstance(g['gwp'],int) else str(g['gwp'])
        rows+=f'<tr><td><strong>{g["gas"]}</strong></td><td style="font-family:monospace;font-size:16px">{g["formula"]}</td><td style="text-align:right;font-weight:600;color:{c}">{gwp_str}</td><td style="font-size:15px;color:var(--textM)">{g["lifetime"]}</td></tr>'
    return f'''<div class="dash-card">
  <div class="dash-title">⚗️ GWP 數值（IPCC AR6，100年期）</div>
  <table class="dash-table">
    <thead><tr><th>氣體</th><th>化學式</th><th>GWP</th><th>大氣壽命</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>'''

def dashboard_ncv():
    def rows_html(data):
        return "".join(f'<tr><td>{d["name"]}</td><td style="text-align:right;font-weight:600">{d["value"]}</td><td style="color:var(--textM);font-size:16px">{d["unit"]}</td></tr>' for d in data)
    return f'''<div class="dash-card">
  <div class="dash-title">🔥 淨熱值（低位發熱值）</div>
  <div style="font-size:16px;color:var(--textM);margin-bottom:6px">資料來源：IPCC 2019 Refinement GL（現行最新）、IEA 2023、EPA 2024</div>
  <div class="ncv-tabs">
    <div class="ncv-group"><div class="ncv-label">固體</div><table class="dash-table"><tbody>{rows_html(NCV_SOLIDS)}</tbody></table></div>
    <div class="ncv-group"><div class="ncv-label">液體</div><table class="dash-table"><tbody>{rows_html(NCV_LIQUIDS)}</tbody></table></div>
    <div class="ncv-group"><div class="ncv-label">氣體</div><table class="dash-table"><tbody>{rows_html(NCV_GASES)}</tbody></table></div>
  </div>
</div>'''

def dashboard_carbon_fee():
    max_fee=max(d['fee'] for d in CARBON_FEE_TREND)
    bars=""
    for d in CARBON_FEE_TREND:
        h=int(d['fee']/max_fee*120)
        col="#ef4444" if d['type']=='目標' else "#f59e0b" if d['type']=='預估' else "#4caf80" if d['type']=='優惠' else "#2d7a4f"
        bars+=f'''<div class="bar-item">
          <div class="bar-tooltip">NT${d["fee"]:,}/t<br>{d["note"]}</div>
          <div class="bar-fill" style="height:{h}px;background:{col}"></div>
          <div class="bar-val">NT${d["fee"]//1000 if d["fee"]>=1000 else d["fee"]}{"K" if d["fee"]>=1000 else ""}</div>
          <div class="bar-yr">{d["year"]}</div>
        </div>'''
    legend='<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;font-size:15px">'
    for col,lbl in [("#2d7a4f","正式費率"),("#4caf80","優惠費率"),("#f59e0b","預估值"),("#ef4444","長期目標")]:
        legend+=f'<span><span style="display:inline-block;width:10px;height:10px;background:{col};border-radius:2px;margin-right:3px"></span>{lbl}</span>'
    legend+='</div>'
    return f'''<div class="dash-card">
  <div class="dash-title">💰 台灣碳費收費趨勢（至2030）</div>
  <div style="font-size:16px;color:var(--textM);margin-bottom:10px">單位：NT$/公噸CO₂e｜資料來源：環境部</div>
  <div class="bar-chart">{bars}</div>
  {legend}
</div>'''

# ── 右欄：永續報告書指引元件 ──────────────────────────────────────────────────
def sr_checklist():
    sections=[
        ("📋 基本資訊",["公司概況與治理架構","報告書範疇與邊界","重大性議題鑑別矩陣","利害關係人溝通方式","永續策略與目標"]),
        ("🌍 環境面(E)",["溫室氣體盤查(Scope 1/2/3)","能源使用與再生能源比例","用水量與水資源管理","廢棄物產生與處置","生物多樣性影響評估","產品碳足跡/水足跡"]),
        ("👥 社會面(S)",["員工人數/離職率/多元化","薪酬結構與性別薪酬差距","教育訓練時數與費用","職業安全衛生數據","供應鏈人權盡職調查","社區投資與公益支出","客戶隱私與資料安全"]),
        ("🏛 治理面(G)",["董事會組成與獨立性","女性董事比例","高階主管薪酬揭露","反貪腐與商業倫理政策","稅務透明度","風險管理機制","法規遵循紀錄"]),
        ("📊 對齊框架",["GRI準則對應表","SASB指標","TCFD氣候相關揭露","SDGs貢獻對應","ISSB S1/S2（新版要求）"]),
    ]
    html=""
    for title,items in sections:
        lis="".join(f'<li style="font-size:16px;color:var(--text2);padding:2px 0;border-bottom:1px dotted var(--border)">{i}</li>' for i in items)
        html+=f'''<div style="margin-bottom:10px">
          <div style="font-size:16px;font-weight:700;color:var(--g600);background:var(--g100);padding:3px 8px;border-radius:4px;margin-bottom:4px">{title}</div>
          <ul style="list-style:none;padding:0">{lis}</ul>
        </div>'''
    return f'''<div class="dash-card">
  <div class="dash-title">📝 永續報告書內容清單</div>
  {html}
  <div style="font-size:15px;color:var(--textM);margin-top:4px">對標 GRI Standards・ISSB・TCFD・金管會規範</div>
</div>'''

def sr_notes():
    notes=[
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
    html="".join(f'''<div style="display:flex;gap:6px;padding:5px 0;border-bottom:1px dotted var(--border);align-items:flex-start">
      <span style="font-size:16px;flex-shrink:0">{badge}</span>
      <span style="font-size:16px;color:var(--text2);line-height:1.5">{text}</span>
    </div>''' for badge,text in notes)
    return f'''<div class="dash-card">
  <div class="dash-title">⚠️ 撰寫注意事項</div>
  {html}
</div>'''

def sr_activities():
    cats=[
        ("🌿 環境面(E)","#22c55e",[
            ("每月","節電競賽：部門用電排行看板，月度冠軍表揚"),
            ("每季","員工碳足跡計算（通勤+差旅+採購），設定個人減碳目標"),
            ("每年","ESG志工日：淨灘/淨山/植樹，連結公司環境目標"),
            ("持續","綠色通勤獎勵：搭大眾運輸/騎自行車補貼"),
        ]),
        ("👥 社會面(S)","#3b82f6",[
            ("每月","DEI午餐會：多元共融議題分享，建立包容文化"),
            ("每季","技能共享：員工教員工課程，培養內部講師"),
            ("每年","供應鏈人權日：稽核培訓+供應商互動"),
            ("持續","身心健康計畫：正念、心理諮詢、EAP員工協助方案"),
        ]),
        ("🏛 治理面(G)","#8b5cf6",[
            ("每月","ESG小學堂：15分鐘最新法規與趨勢（CBAM/碳費/PFAS）"),
            ("每季","誠信宣誓+反貪腐教育，吹哨者保護宣導"),
            ("每年","ESG提案競賽：員工提改善方案，優勝者列入KPI"),
            ("持續","ESG績效目標納入各部門年度KPI考核"),
        ]),
    ]
    html=""
    for title,color,activities in cats:
        items="".join(f'''<div style="display:flex;gap:6px;padding:4px 0;border-bottom:1px dotted var(--border);align-items:flex-start">
          <span style="background:{color}22;color:{color};border-radius:4px;padding:1px 5px;font-size:14px;font-weight:700;flex-shrink:0;margin-top:2px">{freq}</span>
          <span style="font-size:16px;color:var(--text2);line-height:1.4">{act}</span>
        </div>''' for freq,act in activities)
        html+=f'''<div style="margin-bottom:12px">
          <div style="font-size:16px;font-weight:700;color:#fff;background:{color};padding:4px 10px;border-radius:6px;margin-bottom:6px">{title}</div>
          {items}
        </div>'''
    return f'''<div class="dash-card">
  <div class="dash-title">🎯 員工ESG參與活動建議</div>
  <div style="font-size:16px;color:var(--textM);margin-bottom:8px">從生活中落實，讓ESG成為企業文化</div>
  {html}
</div>'''


# ── 新增功能元件 ───────────────────────────────────────────────────────────────

def news_summary_card(news, market):
    """新聞摘要卡：從本週新聞萃取關鍵主題"""
    all_items = news[:5] + market[:3]
    if not all_items:
        return ''
    bullets = ''.join(
        f'''<div style="display:flex;gap:8px;padding:5px 0;border-bottom:1px dotted var(--border);align-items:flex-start">
          <span style="color:var(--g400);font-size:16px;flex-shrink:0">▸</span>
          <span style="font-size:16px;color:var(--text2);line-height:1.5">{it["title"][:70]}{"…" if len(it["title"])>70 else ""}</span>
        </div>'''
        for it in all_items
    )
    tw_cnt = sum(1 for i in news+market if i.get('region')=='台灣')
    hot_cats = {}
    for i in news+market:
        c = i.get('category','')
        hot_cats[c] = hot_cats.get(c,0)+1
    top3 = sorted(hot_cats.items(), key=lambda x:-x[1])[:3]
    tags = ''.join(f'<span class="tag" style="font-size:14px">🔥 {c}（{n}則）</span>' for c,n in top3)
    return (
        f'<div style="background:#ffffff;border:2px solid var(--g400);border-left:7px solid var(--g600);border-radius:var(--r-lg);padding:1.4rem 1.6rem;margin-bottom:1.5rem;box-shadow:0 3px 16px rgba(45,122,79,.12)">' +
        f'<div style="display:flex;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:10px">' +
        f'<span style="background:var(--g900);color:var(--g400);padding:5px 16px;border-radius:20px;font-size:16px;font-weight:700">📡 本週 ESG 新聞摘要</span>' +
        f'<span style="font-size:15px;color:var(--textM)">{DATE_STR} · {len(news)+len(market)} 則</span>' +
        f'<span style="margin-left:auto;font-size:15px;color:var(--textM)">台灣在地 {tw_cnt} 則</span>' +
        f'</div>' +
        f'<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px">{tags}</div>' +
        f'<div style="border-top:2px solid var(--g100);padding-top:10px">{bullets}</div>' +
        f'</div>'
    )

def dashboard_esg_radar():
    """ESG 法規雷達：追蹤六大法規最新進度"""
    regs = [
        ("CBAM","歐盟碳邊境","🟡","過渡期末段","2026/01正式徵費，台灣業者準備中","78","#f59e0b","https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism_en"),
        ("CSRD","歐盟永續報告","🟠","Omnibus審議中","擬縮至1千家，2026年明朗化","70","#f97316","https://finance.ec.europa.eu/capital-markets-union-and-financial-markets/company-reporting-and-auditing/company-reporting/corporate-sustainability-reporting_en"),
        ("IFRS S1/S2","ISSB準則","🟢","台灣2027強制","金管會2024宣布接軌路徑","82","#22c55e","https://www.ifrs.org/issued-standards/ifrs-sustainability-disclosure-standards/"),
        ("台灣碳費","碳費制度","🔴","2025已開徵","NT$300/t，首批500家繳費","95","#ef4444","https://www.epa.gov.tw/climate/4B9E1E3855AAEE81"),
        ("SBTi","科學減量目標","🟡","2024更新標準","新1.5°C路徑更嚴，全球7000+申請","58","#f59e0b","https://sciencebasedtargets.org/companies-taking-action"),
        ("歐盟ETS","歐盟碳交易","🟢","Phase 4進行中","2024均價€55–65，CBAM連動","85","#22c55e","https://climate.ec.europa.eu/eu-action/eu-emissions-trading-system-eu-ets_en"),
    ]
    rows = ""
    for code, name, dot, status, note, pct, color, url in regs:
        rows += (
            f'<div style="padding:8px 0;border-bottom:1px dotted var(--border)">' +
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">' +
            f'<span style="font-size:14px">{dot}</span>' +
            f'<a href="{url}" target="_blank" style="font-weight:700;font-size:16px;color:var(--g600);text-decoration:none">{code} ↗</a>' +
            f'<span style="font-size:14px;color:var(--textM)">{name}</span>' +
            f'<span style="margin-left:auto;font-size:14px;font-weight:600;color:{color}">{status}</span>' +
            f'</div>' +
            f'<div style="background:#e5e7eb;border-radius:20px;height:6px;margin-bottom:3px">' +
            f'<div style="width:{pct}%;height:100%;background:{color};border-radius:20px"></div>' +
            f'</div>' +
            f'<div style="font-size:14px;color:var(--textM)">{note}</div>' +
            f'</div>'
        )
    legend = '<div style="display:flex;gap:10px;margin-top:8px;font-size:14px">'
    for col,lbl in [("#22c55e","已生效/採用"),("#f59e0b","過渡/推動中"),("#ef4444","即將強制")]:
        legend += f'<span><span style="display:inline-block;width:10px;height:10px;background:{col};border-radius:50%;margin-right:3px"></span>{lbl}</span>'
    legend += '</div>'
    return f'''<div class="dash-card">
  <div class="dash-title">📡 ESG 法規雷達</div>
  <div style="font-size:14px;color:var(--textM);margin-bottom:8px">追蹤全球六大 ESG 法規最新進度</div>
  {rows}
  {legend}
</div>'''

def dashboard_carbon_sim():
    """碳費試算器（互動式 JavaScript）"""
    return '''<div class="dash-card">
  <div class="dash-title">🧮 碳費試算 Carbon Fee Simulator</div>
  <div style="font-size:14px;color:var(--textM);margin-bottom:10px">輸入年度排放量，試算不同費率下的碳費成本</div>

  <div style="margin-bottom:10px">
    <label style="font-size:15px;font-weight:600;color:var(--text1);display:block;margin-bottom:4px">
      年排放量（公噸 CO₂e）
    </label>
    <input id="cf-input" type="number" min="0" value="25000"
      style="width:100%;padding:8px 10px;border:1px solid var(--border);border-radius:var(--r-md);font-size:18px;outline:none;background:var(--bg)"
      oninput="calcCF()">
  </div>

  <div id="cf-results" style="display:flex;flex-direction:column;gap:6px"></div>

  <div style="margin-top:10px;padding:8px;background:var(--bg);border-radius:var(--r-md);font-size:14px;color:var(--textM)">
    💡 2025年正式開徵 · 門檻：年排放 ≥ 25,000 tCO₂e<br>優惠費率 NT$50/t 需提交自主減量計畫通過環境部審查<br>資料來源：環境部 2025 公告
  </div>
</div>

<script>
function calcCF() {
  var em = parseFloat(document.getElementById("cf-input").value) || 0;
  var rows = [
    ["2025 一般費率", 300,  "#2d7a4f", "已公告"],
    ["2025 優惠費率", 100,  "#4caf80", "需提自主減量計畫"],
    ["2027 預估費率", 800,  "#f59e0b", "政策預估，供參考"],
    ["2030 目標費率", 2000, "#ef4444", "長期目標"],
  ];
  var maxFee = em * 2000;
  var html = "";
  for (var i = 0; i < rows.length; i++) {
    var r = rows[i];
    var fee = em * r[1];
    var pct = maxFee > 0 ? Math.round(fee/maxFee*100) : 0;
    var feeStr = fee >= 1000000
      ? (fee/1000000).toFixed(2) + " 百萬"
      : fee >= 1000
      ? (fee/1000).toFixed(0) + " 千"
      : fee.toFixed(0);
    html += '<div style="border:1px solid var(--border);border-left:3px solid '+r[2]+';border-radius:6px;padding:7px 10px">';
    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">';
    html += '<span style="font-size:15px;font-weight:600">'+r[0]+'</span>';
    html += '<span style="font-size:18px;font-weight:700;color:'+r[2]+'">NT$'+feeStr+'</span>';
    html += '</div>';
    html += '<div style="background:#e5e7eb;border-radius:20px;height:5px;margin-bottom:3px">';
    html += '<div style="width:'+pct+'%;height:100%;background:'+r[2]+';border-radius:20px"></div>';
    html += '</div>';
    html += '<div style="font-size:14px;color:var(--textM)">NT$'+r[1]+'/t · '+r[3]+'</div>';
    html += '</div>';
  }
  document.getElementById("cf-results").innerHTML = html;
}
window.onload = calcCF;
</script>'''


# ── 高優先新增：產業專屬 ESG 資訊 ─────────────────────────────────────────────

def dashboard_re100():
    grid_data = [("2021","509","#ef4444",55),("2022","495","#f59e0b",48),("2023","490","#f59e0b",44),("2024","~482","#f97316",38)]
    grid_bars = "".join(
        f'<div style="text-align:center;flex:1">'
        f'<div style="font-size:16px;font-weight:700;color:{c};margin-bottom:4px">{v}</div>'
        f'<div style="height:{h}px;background:{c};border-radius:4px 4px 0 0;margin:0 3px"></div>'
        f'<div style="font-size:15px;color:var(--textM);margin-top:4px;font-weight:500">{y}</div>'
        f'</div>'
        for y,v,c,h in grid_data)
    companies = [
        ("台積電","2030: 40%","2050: RE100",40,"#2d7a4f"),
        ("日月光","2030: 50%","2050: RE100",50,"#22c55e"),
        ("聯電","2030: 50%","承諾申請中",50,"#4caf80"),
        ("友達","2030: 30%","2050: RE100",30,"#f59e0b"),
        ("群創","2030: 20%","2050: 碳中和",20,"#f97316"),
        ("台達電","2030:100%","RE100已加入",100,"#2d7a4f"),
    ]
    co_rows = "".join(
        f'<tr><td style="font-size:15px;font-weight:600">{n}</td><td style="font-size:14px;color:{c};font-weight:600">{t}</td><td style="font-size:14px;color:var(--textM)">{g}</td><td style="width:70px"><div style="background:#e5e7eb;border-radius:4px;height:6px"><div style="width:{p}%;height:100%;background:{c};border-radius:4px"></div></div></td></tr>'
        for n,t,g,p,c in companies)
    return ('<div class="dash-card"><div class="dash-title">⚡ 台灣電網碳強度 + RE100 進度</div>'
        +'<div style="font-size:14px;color:var(--textM);margin-bottom:6px">電網碳強度（gCO₂/kWh）— 資料來源：台電年報</div>'
        +f'<div style="display:flex;align-items:flex-end;height:90px;border-bottom:1px solid var(--border);margin-bottom:8px;padding:0 4px">{grid_bars}</div>'
        +'<div style="font-size:14px;color:var(--textM);margin-bottom:6px">🏭 主要半導體/光電廠商 RE100 承諾進度</div>'
        +'<table class="dash-table"><thead><tr><th>企業</th><th>2030目標</th><th>長期承諾</th><th>進度</th></tr></thead>'
        +f'<tbody>{co_rows}</tbody></table>'
        +'<div style="font-size:14px;color:var(--textM);margin-top:6px">資料來源：各企業永續報告書（2023–2024）· RE100官網</div></div>')

def dashboard_fgas():
    gases = [
        ("CF₄","45,200","42,100","38,800","#8b5cf6","晶圓蝕刻主要排放"),
        ("C₂F₆","18,600","17,200","15,900","#ec4899","CVD腔體清洗"),
        ("NF₃","22,400","20,800","18,500","#3b82f6","Remote Plasma"),
        ("SF₆","8,900","7,600","6,200","#ef4444","蝕刻/腔體清洗"),
    ]
    rows = "".join(f'<tr><td style="font-size:15px;font-weight:600;color:{c}">{g}</td><td style="text-align:right;font-size:15px">{v21}</td><td style="text-align:right;font-size:15px">{v22}</td><td style="text-align:right;font-size:15px;color:#22c55e">{v23}↓</td><td style="font-size:14px;color:var(--textM)">{note}</td></tr>' for g,v21,v22,v23,c,note in gases)
    techs = [("🔥","熱氧化裂解器","CF₄削減>90%，台積電已全面導入"),("🌀","Remote Plasma Cleaning","NF₃削減>95%，取代in-situ清洗"),("♻️","PFCs替代化學品","C₃F₆等低GWP替代品，部分製程導入中")]
    t_html = "".join(f'<div style="display:flex;gap:8px;padding:4px 0;border-bottom:1px dotted var(--border)"><span style="font-size:18px">{icon}</span><div><div style="font-size:15px;font-weight:600">{name}</div><div style="font-size:14px;color:var(--textM)">{note}</div></div></div>' for icon,name,note in techs)
    return ('<div class="dash-card"><div class="dash-title">🧪 半導體 F-Gas 排放趨勢與削減</div>'
        +'<div style="font-size:14px;color:var(--textM);margin-bottom:6px">台灣半導體業年排放量（公噸CO₂e）— 環保署盤查平台</div>'
        +'<table class="dash-table"><thead><tr><th>氣體</th><th>2021</th><th>2022</th><th>2023</th><th>主要用途</th></tr></thead>'
        +f'<tbody>{rows}</tbody></table>'
        +'<div style="font-size:14px;font-weight:600;color:var(--g600);margin:8px 0 4px">🔧 主要削減技術</div>'
        +f'{t_html}<div style="font-size:14px;color:var(--textM);margin-top:6px">資料來源：環保署盤查平台 · SEMI F47/F98 · 2024</div></div>')

def dashboard_water():
    parks = [("竹科","3,180","87.2","#ef4444","高度水壓力"),("中科","1,850","82.5","#f59e0b","中高水壓力"),("南科","5,240","91.3","#ef4444","高度水壓力"),("竹南","620","79.8","#f59e0b","中高水壓力")]
    rows = "".join(f'<tr><td style="font-size:15px;font-weight:600">{n}</td><td style="text-align:right;font-size:15px">{v}</td><td style="text-align:right;font-size:15px">{r}%</td><td><span style="background:{c}22;color:{c};padding:1px 6px;border-radius:4px;font-size:12px;font-weight:600">{risk}</span></td></tr>' for n,v,r,c,risk in parks)
    trends = [("台積電","用水強度↓18%（2020→2023）","2030目標↓30%"),("聯電","廢水回收率 94.2%","2023年"),("友達","節水 280萬m³","2023年"),("群創","純水回收率 85%","業界領先")]
    t_html = "".join(f'<div style="display:flex;gap:6px;padding:4px 0;border-bottom:1px dotted var(--border);font-size:15px"><span style="font-weight:600;min-width:50px">{co}</span><span style="color:var(--textM);flex:1">{kpi}</span><span style="color:var(--g600);font-weight:600">{yr}</span></div>' for co,kpi,yr in trends)
    return ('<div class="dash-card"><div class="dash-title">💧 水資源壓力指標</div>'
        +'<div style="font-size:14px;color:var(--textM);margin-bottom:6px">科學園區用水量（萬m³/年）+ WRI Aqueduct 水壓力評估</div>'
        +'<table class="dash-table"><thead><tr><th>園區</th><th>用水(萬m³)</th><th>回收率</th><th>風險評級</th></tr></thead>'
        +f'<tbody>{rows}</tbody></table>'
        +'<div style="font-size:14px;font-weight:600;color:var(--g600);margin:8px 0 4px">🏭 主要廠商節水成效（2023）</div>'
        +f'{t_html}<div style="font-size:14px;color:var(--textM);margin-top:6px">資料來源：科學園區管理局年報2023 · WRI Aqueduct 3.0 · 各企業永續報告書</div></div>')

def dashboard_uflpa():
    timeline = [
        ("2022/06","UFLPA正式生效","美國強制執行，源自新疆產品一律扣押","#ef4444"),
        ("2023/06","實體清單擴大","新增多家新疆多晶矽及紡織品供應商","#f59e0b"),
        ("2024/03","CBP執法加強","太陽能板抽查率提升，港口扣押案件增加","#f59e0b"),
        ("2024/09","台廠因應完成","台灣面板/模組廠完成供應鏈溯源文件","#22c55e"),
        ("2025","持續監控","預計擴大至電池、多晶矽材料全鏈追溯","#f97316"),
    ]
    t_html = "".join(f'<div style="display:flex;gap:8px;padding:5px 0;border-bottom:1px dotted var(--border);align-items:flex-start"><span style="background:{c}22;color:{c};padding:1px 6px;border-radius:4px;font-size:12px;font-weight:600;flex-shrink:0;white-space:nowrap">{d}</span><div><div style="font-size:15px;font-weight:600">{t}</div><div style="font-size:14px;color:var(--textM)">{n}</div></div></div>' for d,t,n,c in timeline)
    impacts = [("多晶矽","新疆佔全球供應約35%（2024）↓（較2022年55%降低）"),("台廠","AUO、Innolux、元晶已建立溯源機制完成認證"),("因應工具","IECRE、SolarTrace第三方溯源驗證為主流方案")]
    i_html = "".join(f'<div style="padding:4px 0;border-bottom:1px dotted var(--border);font-size:15px"><span style="font-weight:600;color:var(--g600)">{k}</span>：<span style="color:var(--textM)">{v}</span></div>' for k,v in impacts)
    return ('<div class="dash-card"><div class="dash-title">🇺🇸 UFLPA 多晶矽溯源追蹤</div>'
        +'<div style="font-size:14px;color:var(--textM);margin-bottom:8px">維吾爾強迫勞動預防法 · 光電業供應鏈合規關鍵</div>'
        +f'{t_html}'
        +'<div style="font-size:14px;font-weight:600;color:var(--g600);margin:8px 0 4px">📊 台灣光電產業影響現況</div>'
        +f'{i_html}<div style="font-size:14px;color:var(--textM);margin-top:6px">資料來源：U.S. CBP · UFLPA Entity List · SEMI · 2024</div></div>')

def dashboard_pfas():
    timeline = [
        ("2023/02","EU ECHA提案","歐盟提出PFAS通用限制草案，覆蓋約1萬種物質","#ef4444"),
        ("2023–24","意見徵詢","業界提交技術可行性意見，半導體業爭取豁免","#f59e0b"),
        ("2024","3M退出PFAS","3M宣布2025年停止生產所有PFAS，供應衝擊開始","#ef4444"),
        ("2025","替代品供應","DuPont/Chemours替代品，但價格高3–5倍","#f59e0b"),
        ("2026–27","預計決議","歐盟最終限制範圍與豁免清單，半導體業關注","#f97316"),
    ]
    t_html = "".join(f'<div style="display:flex;gap:8px;padding:5px 0;border-bottom:1px dotted var(--border);align-items:flex-start"><span style="background:{c}22;color:{c};padding:1px 6px;border-radius:4px;font-size:12px;font-weight:600;flex-shrink:0;white-space:nowrap">{d}</span><div><div style="font-size:15px;font-weight:600">{t}</div><div style="font-size:14px;color:var(--textM)">{n}</div></div></div>' for d,t,n,c in timeline)
    uses = [("蝕刻液","HF系含氟蝕刻液","高風險，替代方案研發中"),("CMP漿料","含PFAS研磨液添加劑","部分已有替代品"),("光阻溶劑","含氟溶劑","低替代性，爭取豁免"),("密封材料","PTFE/FKM管件","短期難以替代")]
    u_html = "".join(f'<tr><td style="font-size:15px;font-weight:600">{t}</td><td style="font-size:14px">{m}</td><td style="font-size:14px;color:var(--textM)">{s}</td></tr>' for t,m,s in uses)
    return ('<div class="dash-card"><div class="dash-title">⚗️ PFAS 法規追蹤（半導體製程關鍵）</div>'
        +'<div style="font-size:14px;color:var(--textM);margin-bottom:8px">歐盟全氟化合物通用限制 · 預計2026–2027年決議</div>'
        +f'{t_html}'
        +'<div style="font-size:14px;font-weight:600;color:var(--g600);margin:8px 0 4px">🔬 半導體製程主要PFAS使用點</div>'
        +'<table class="dash-table"><thead><tr><th>用途</th><th>主要物質</th><th>替代可行性</th></tr></thead>'
        +f'<tbody>{u_html}</tbody></table>'
        +'<div style="font-size:14px;color:var(--textM);margin-top:6px">資料來源：EU ECHA · SEMI PFAS Task Force · 2024</div></div>')

def dashboard_critical_minerals():
    controls = [
        ("鎵 Ga","2023/08","許可證制","LED/化合物半導體","中國佔全球供應80%+","#ef4444"),
        ("鍺 Ge","2023/08","許可證制","光纖/紅外/半導體","中國佔全球供應60%+","#ef4444"),
        ("銦 In","2024/01","管制強化","ITO電極/光電","中國精煉佔57%","#f59e0b"),
        ("石墨","2023/10","許可證制","電池/半導體製程","中國天然石墨77%","#f59e0b"),
        ("銻 Sb","2024/09","出口禁止","半導體摻雜/阻燃","中國佔全球48%","#ef4444"),
        ("稀土","2024/12","出口管制","馬達/電子元件","中國精煉90%+","#ef4444"),
    ]
    rows = "".join(f'<tr><td style="font-size:15px;font-weight:600;color:{c}">{m}</td><td style="font-size:14px">{d}</td><td><span style="background:{c}22;color:{c};padding:1px 5px;border-radius:4px;font-size:12px">{ctrl}</span></td><td style="font-size:14px;color:var(--textM)">{app}</td></tr>' for m,d,ctrl,app,supply,c in controls)
    risks = [("台積電","CoWoS封裝稀土材料，已啟動多元化採購"),("光電廠","GaN/GaAs基板鎵來源，尋求加拿大/德國供應商"),("面板廠","ITO靶材，台灣光洋科等已備足半年庫存")]
    r_html = "".join(f'<div style="padding:4px 0;border-bottom:1px dotted var(--border);font-size:15px"><span style="font-weight:600;color:var(--g600)">{co}</span><br><span style="color:var(--textM)">{action}</span></div>' for co,action in risks)
    return ('<div class="dash-card"><div class="dash-title">⛏️ 關鍵礦物供應鏈風險</div>'
        +'<div style="font-size:14px;color:var(--textM);margin-bottom:6px">中國出口管制時序 · 直接衝擊半導體與光電供應鏈</div>'
        +'<table class="dash-table"><thead><tr><th>礦物</th><th>管制日</th><th>措施</th><th>主要應用</th></tr></thead>'
        +f'<tbody>{rows}</tbody></table>'
        +'<div style="font-size:14px;font-weight:600;color:var(--g600);margin:8px 0 4px">🏭 台灣廠商因應動態</div>'
        +f'{r_html}<div style="font-size:14px;color:var(--textM);margin-top:6px">資料來源：中國商務部公告 · IEA Critical Minerals 2024 · 工研院</div></div>')


# ── 本週法規變動 ───────────────────────────────────────────────────────────────
def dashboard_reg_updates():
    updates = [
        {
            "reg":"CBAM","color":"#f59e0b","icon":"🌍",
            "status":"過渡期末段","date":"2025年持續",
            "update":"歐盟執委會確認2026/01正式徵費時程不變。過渡期最後一份季度申報截止2025/07/31，出口商需完成產品碳含量計算與文件準備。",
            "semi_impact":"中等","solar_impact":"高度",
            "url":"https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism_en"
        },
        {
            "reg":"台灣碳費","color":"#ef4444","icon":"🇹🇼",
            "status":"已開徵","date":"2025年第一季",
            "update":"環境部公告首批約500家業者納管名單，2025Q1完成排放量申報。自主減量計畫審查進入第二批，截止2025/06/30。優惠費率NT$50/t需通過減量路徑審查。",
            "semi_impact":"高度","solar_impact":"中等",
            "url":"https://www.epa.gov.tw/climate/4B9E1E3855AAEE81"
        },
        {
            "reg":"歐盟CSRD","color":"#f97316","icon":"🇪🇺",
            "status":"Omnibus審議中","date":"2025年",
            "update":"歐洲議會2025年4月通過一讀：擬將強制適用企業從5萬家縮至1千家（資本額5億歐元以上）。中小型供應商仍受大型客戶要求影響，台灣出口廠商需持續關注客戶ESG查核要求。",
            "semi_impact":"中等","solar_impact":"中等",
            "url":"https://finance.ec.europa.eu/capital-markets-union-and-financial-markets/company-reporting-and-auditing/company-reporting/corporate-sustainability-reporting_en"
        },
        {
            "reg":"台灣ISSB接軌","color":"#22c55e","icon":"📋",
            "status":"準備期","date":"2025–2027",
            "update":"金管會發布「永續發展行動方案2.0」，2026年資本額100億以上試行ISSB格式，2027年全面強制。建議企業2025年完成Gap分析並培訓ESG揭露團隊。",
            "semi_impact":"高度","solar_impact":"高度",
            "url":"https://cgc.twse.com.tw/frontEN/sustainReport"
        },
    ]
    cards = ""
    for u in updates:
        semi_col = "#ef4444" if u["semi_impact"]=="高度" else "#f59e0b" if u["semi_impact"]=="中等" else "#22c55e"
        solar_col = "#ef4444" if u["solar_impact"]=="高度" else "#f59e0b" if u["solar_impact"]=="中等" else "#22c55e"
        cards += (
            f'<div style="border:1px solid var(--border);border-left:4px solid {u["color"]};border-radius:8px;padding:10px 12px;margin-bottom:8px">' +
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">' +
            f'<span style="font-size:20px">{u["icon"]}</span>' +
            f'<span style="font-weight:700;font-size:16px;color:{u["color"]}">{u["reg"]}</span>' +
            f'<span style="background:{u["color"]}22;color:{u["color"]};padding:1px 8px;border-radius:20px;font-size:14px;margin-left:auto">{u["status"]}</span>' +
            f'</div>' +
            f'<p style="font-size:15px;color:var(--text2);line-height:1.6;margin-bottom:6px">{u["update"]}</p>' +
            f'<div style="display:flex;gap:8px;align-items:center">' +
            f'<span style="font-size:14px;color:var(--textM)">半導體：</span><span style="background:{semi_col}22;color:{semi_col};padding:1px 6px;border-radius:4px;font-size:14px;font-weight:600">{u["semi_impact"]}</span>' +
            f'<span style="font-size:14px;color:var(--textM)">光電：</span><span style="background:{solar_col}22;color:{solar_col};padding:1px 6px;border-radius:4px;font-size:14px;font-weight:600">{u["solar_impact"]}</span>' +
            f'<a href="{u["url"]}" target="_blank" style="margin-left:auto;font-size:14px;color:var(--g600);text-decoration:none;font-weight:500">官方資訊 →</a>' +
            f'</div></div>'
        )
    return (
        '<div class="dash-card">' +
        '<div class="dash-title">📰 本週法規變動</div>' +
        '<div style="font-size:14px;color:var(--textM);margin-bottom:10px">CBAM · 台灣碳費 · CSRD · ISSB 最新進度</div>' +
        cards +
        '<div style="font-size:14px;color:var(--textM);margin-top:4px">每週自動更新 · 點擊「官方資訊」查閱原始文件</div>' +
        '</div>'
    )

# ── AI 監管影響分析 ────────────────────────────────────────────────────────────
def dashboard_impact_analysis():
    analyses = [
        {
            "reg":"CBAM（歐盟碳邊境）","icon":"🌍","color":"#f59e0b",
            "semi":{
                "level":"中等影響","color":"#f59e0b",
                "points":["半導體產品目前不在CBAM第一批清單（鋼鋁水泥電力）","間接影響：上游原材料（鋁封裝基板、鋼製設備）進口成本上升","2026年後若擴大至電子產品，影響將大幅提升","建議：追蹤原材料供應商碳含量，建立供應鏈碳數據庫"],
            },
            "solar":{
                "level":"高度影響","color":"#ef4444",
                "points":["太陽能模組出口歐盟若含高碳鋁框、鋼結構將受直接影響","多晶矽生產耗能高，碳含量高於歐盟競爭者","建議：優先完成光伏產品LCA碳足跡計算，準備CBAM申報文件","關注：歐盟擬2026年將太陽能模組納入CBAM範圍"],
            }
        },
        {
            "reg":"台灣碳費（2025已開徵）","icon":"🇹🇼","color":"#ef4444",
            "semi":{
                "level":"高度影響","color":"#ef4444",
                "points":["台積電、聯電、世界先進等晶圓廠年排放均超25萬噸，碳費負擔重","以台積電2023年約500萬噸Scope 2計，一般費率年碳費達NT$15億+","建議：立即申請自主減量計畫，爭取NT$50/t優惠費率（可節省83%）","購買再生能源憑證降低Scope 2，同步降低碳費計算基礎"],
            },
            "solar":{
                "level":"中等影響","color":"#f59e0b",
                "points":["LED磊晶廠（如富采）排放量約40萬噸，年碳費約NT$1.2億（一般費率）","光電面板廠（友達/群創）年碳費可達NT$2–5億","建議：優先完成ISO 14064-1盤查，確認排放基準年","太陽能電池製造相對耗能較低，碳費壓力小於晶圓廠"],
            }
        },
        {
            "reg":"CSRD + ISSB接軌","icon":"📋","color":"#22c55e",
            "semi":{
                "level":"高度影響","color":"#ef4444",
                "points":["台積電、日月光等為歐美大型企業供應商，間接受CSRD供應鏈條款約束","2027年台灣ISSB強制接軌，需揭露氣候財務影響（TCFD架構）","建議：2025年完成ISSB Gap分析，2026年試行揭露","設置ESG數據管理系統，確保數據可驗證性"],
            },
            "solar":{
                "level":"中等影響","color":"#f59e0b",
                "points":["光電廠歐洲客戶佔比較低，CSRD直接影響程度中等","UFLPA供應鏈溯源要求與CSRD盡職調查要求形成雙重壓力","建議：建立供應鏈ESG評估體系，優先針對歐美客戶","台灣ISSB接軌是主要合規壓力，需要提早準備"],
            }
        },
    ]
    html = ""
    for a in analyses:
        semi = a["semi"]; solar = a["solar"]
        semi_pts = "".join(f'<li style="font-size:15px;color:var(--text2);padding:2px 0">{p}</li>' for p in semi["points"])
        solar_pts = "".join(f'<li style="font-size:15px;color:var(--text2);padding:2px 0">{p}</li>' for p in solar["points"])
        html += (
            f'<div style="border:1px solid var(--border);border-radius:8px;margin-bottom:10px;overflow:hidden">' +
            f'<div style="background:{a["color"]}15;padding:8px 12px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:8px">' +
            f'<span style="font-size:20px">{a["icon"]}</span>' +
            f'<span style="font-weight:700;font-size:16px">{a["reg"]}</span>' +
            f'</div>' +
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:0">' +
            f'<div style="padding:8px 10px;border-right:1px solid var(--border)">' +
            f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:5px">' +
            f'<span style="font-size:16px">🔬</span><span style="font-size:15px;font-weight:600">半導體業</span>' +
            f'<span style="background:{semi["color"]}22;color:{semi["color"]};padding:1px 6px;border-radius:4px;font-size:14px;font-weight:600;margin-left:auto">{semi["level"]}</span>' +
            f'</div><ul style="list-style:disc;padding-left:14px">{semi_pts}</ul></div>' +
            f'<div style="padding:8px 10px">' +
            f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:5px">' +
            f'<span style="font-size:16px">☀️</span><span style="font-size:15px;font-weight:600">光電業</span>' +
            f'<span style="background:{solar["color"]}22;color:{solar["color"]};padding:1px 6px;border-radius:4px;font-size:14px;font-weight:600;margin-left:auto">{solar["level"]}</span>' +
            f'</div><ul style="list-style:disc;padding-left:14px">{solar_pts}</ul></div>' +
            f'</div></div>'
        )
    return (
        '<div class="dash-card">' +
        '<div class="dash-title">🤖 ESG 監管影響分析</div>' +
        '<div style="font-size:14px;color:var(--textM);margin-bottom:10px">主要法規對半導體業 🔬 與光電業 ☀️ 的影響評估</div>' +
        html +
        '<div style="font-size:14px;color:var(--textM);margin-top:4px">分析基準：各企業公開永續報告書 · 環境部公告 · 2025年</div>' +
        '</div>'
    )

# ── ESG 行動建議 ───────────────────────────────────────────────────────────────
def dashboard_action_items():
    actions = [
        {
            "title":"CBAM 應準備文件清單","icon":"🌍","color":"#f59e0b","urgent":"2025/07前完成",
            "items":[
                ("📄","CBAM申報書","CE-3號表格，每季度申報一次，過渡期內免費"),
                ("⚖️","產品碳含量計算","直接排放+間接排放，依歐盟CBAM法規計算方法"),
                ("🏭","生產設施資料","製程說明、能源使用量、燃料類型與用量"),
                ("💳","生產國碳價憑證","台灣已開徵碳費，可抵扣CBAM差額（需取得官方證明）"),
                ("🔍","第三方查驗","建議2025年完成預查驗，確保2026年正式徵費前達標"),
                ("📊","供應商碳數據","要求鋼鋁原材料供應商提供碳排放數據"),
            ]
        },
        {
            "title":"台灣碳費 優惠費率申請","icon":"🇹🇼","color":"#ef4444","urgent":"2025/06前申請",
            "items":[
                ("📋","排放量申報","完成2024年度溫室氣體排放量申報（ISO 14064-1）"),
                ("📈","自主減量計畫","訂定2030年減碳目標、年度里程碑、具體措施"),
                ("🌿","再生能源購買","採購T-REC再生能源憑證，可降低Scope 2計算基礎"),
                ("✅","減量路徑審查","送環境部審查，通過後可適用NT$50/t優惠費率"),
                ("💰","費用試算","使用平台碳費試算器，預估未來3年財務衝擊"),
            ]
        },
        {
            "title":"ISSB 接軌準備（2027前）","icon":"📋","color":"#22c55e","urgent":"2025年啟動",
            "items":[
                ("🔍","Gap分析","對照IFRS S1/S2要求，盤點現有揭露缺口"),
                ("📊","氣候財務影響","完成TCFD四大架構揭露（治理/策略/風險管理/指標）"),
                ("🌡","情境分析","至少完成1.5°C與2°C兩種氣候情境財務影響評估"),
                ("💻","數據管理系統","建立ESG數據收集與驗證平台，確保數據可追溯"),
                ("🎓","人員培訓","財務、法務、永續部門人員接受ISSB揭露培訓"),
                ("🔒","第三方確信","提前接觸查驗機構，規劃有限確信→合理確信路徑"),
            ]
        },
    ]
    html = ""
    for a in actions:
        items_html = "".join(
            f'<div style="display:flex;gap:8px;padding:4px 0;border-bottom:1px dotted var(--border);align-items:flex-start">' +
            f'<span style="font-size:18px;flex-shrink:0">{icon}</span>' +
            f'<div><div style="font-size:15px;font-weight:600">{title}</div>' +
            f'<div style="font-size:14px;color:var(--textM)">{desc}</div></div></div>'
            for icon,title,desc in a["items"]
        )
        html += (
            f'<div style="border:1px solid var(--border);border-left:4px solid {a["color"]};border-radius:8px;padding:10px 12px;margin-bottom:8px">' +
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">' +
            f'<span style="font-size:20px">{a["icon"]}</span>' +
            f'<span style="font-weight:700;font-size:16px">{a["title"]}</span>' +
            f'<span style="background:#ef444422;color:#ef4444;padding:1px 8px;border-radius:4px;font-size:14px;font-weight:600;margin-left:auto">⏰ {a["urgent"]}</span>' +
            f'</div>{items_html}</div>'
        )
    return (
        '<div class="dash-card">' +
        '<div class="dash-title">✅ ESG 行動建議</div>' +
        '<div style="font-size:14px;color:var(--textM);margin-bottom:10px">企業應準備的文件與行動清單</div>' +
        html +
        '</div>'
    )

# ── ESG 名詞庫 ─────────────────────────────────────────────────────────────────
def dashboard_glossary():
    terms = [
        ("CBAM","Carbon Border Adjustment Mechanism","碳邊境調整機制","歐盟對進口高碳產品徵收費用，防止碳洩漏。2026年正式生效。","歐盟法規","#f59e0b"),
        ("CSRD","Corporate Sustainability Reporting Directive","企業永續報告指令","要求歐盟大型企業揭露永續資訊，取代NFRD。2025年Omnibus提案擬縮小範圍。","歐盟法規","#f97316"),
        ("IFRS S1","IFRS Sustainability Disclosure Standard 1","永續相關財務資訊揭露","ISSB發布的通用永續揭露準則，要求企業揭露對財務有影響的永續風險與機會。","ISSB準則","#22c55e"),
        ("IFRS S2","IFRS Sustainability Disclosure Standard 2","氣候相關揭露","ISSB發布的氣候專屬準則，涵蓋治理/策略/風險管理/指標目標四大主題。","ISSB準則","#22c55e"),
        ("TNFD","Taskforce on Nature-related Financial Disclosures","自然相關財務揭露","仿照TCFD架構，要求企業揭露對自然生態系的依賴與影響。2023年正式發布。","新興框架","#8b5cf6"),
        ("SBTi","Science Based Targets initiative","科學基礎減量目標","要求企業設定符合1.5°C氣候目標的減碳路徑，2024年更新更嚴格標準。","自願倡議","#3b82f6"),
        ("TCFD","Task Force on Climate-related Financial Disclosures","氣候財務揭露","四大架構：治理/策略/風險管理/指標，已被IFRS S2全面納入。","揭露框架","#2563eb"),
        ("GRI","Global Reporting Initiative","全球報告倡議","最廣泛使用的永續報告準則，GRI Standards適用於所有組織規模。","報告準則","#2d7a4f"),
        ("CDP","Carbon Disclosure Project","碳揭露計畫","全球最大氣候揭露平台，評級A–D，台積電2023年獲A評級。","評級平台","#22c55e"),
        ("PFAS","Per- and Polyfluoroalkyl Substances","全氟及多氟烷基物質","半導體製程廣泛使用的含氟化學品，歐盟擬2026–27年全面限制。","製程法規","#ef4444"),
        ("UFLPA","Uyghur Forced Labor Prevention Act","維吾爾強迫勞動預防法","美國法案，源自新疆的商品一律扣押，光電業多晶矽溯源關鍵。","美國法規","#ef4444"),
        ("RE100","Renewable Energy 100%","百分之百再生能源倡議","企業承諾2050年前達到100%使用再生能源，全球逾400家企業加入。","自願倡議","#22c55e"),
        ("Scope 1","—","直接排放","企業自身擁有或控制的設施直接產生的溫室氣體排放。","溫室氣體","#2d7a4f"),
        ("Scope 2","—","能源間接排放","購買電力、熱能、蒸汽的溫室氣體排放，半導體廠最大排放來源。","溫室氣體","#2d7a4f"),
        ("Scope 3","—","其他間接排放","供應鏈上下游、員工通勤、產品使用等的排放，最難量化但佔比最高。","溫室氣體","#f59e0b"),
        ("GWP","Global Warming Potential","全球暖化潛勢","衡量溫室氣體相對CO₂的增溫效果，SF₆的GWP高達25,200。","計算方法","#8b5cf6"),
    ]
    # 分組顯示
    cats = {}
    for item in terms:
        c = item[5]  # category is index 4
        cat_name = item[4]
        if cat_name not in cats:
            cats[cat_name] = []
        cats[cat_name].append(item)
    
    html = '<div id="glossary-search" style="margin-bottom:10px"><input id="gls-input" type="text" placeholder="🔍 搜尋名詞...（輸入縮寫或中文）" oninput="filterGls()" style="width:100%;padding:7px 10px;border:1px solid var(--border);border-radius:var(--r-md);font-size:16px;outline:none;background:var(--bg)"></div>'
    html += '<div id="gls-list">'
    for cat_name, items in cats.items():
        color = items[0][5]
        html += f'<div style="margin-bottom:8px"><div style="font-size:14px;font-weight:600;color:{color};background:{color}15;padding:2px 8px;border-radius:4px;margin-bottom:4px">{cat_name}</div>'
        for abbr,en,zh,desc,cat,col in items:
            html += (
                f'<div class="gls-item" style="padding:5px 0;border-bottom:1px dotted var(--border)">' +
                f'<div style="display:flex;align-items:center;gap:6px">' +
                f'<span style="font-weight:700;font-size:16px;color:{col}">{abbr}</span>' +
                f'<span style="font-size:14px;color:var(--textM)">{zh}</span>' +
                f'</div>' +
                f'<div style="font-size:14px;color:var(--text2);margin-top:1px">{desc}</div>' +
                f'</div>'
            )
        html += '</div>'
    html += '</div>'
    html += """<script>
function filterGls(){
  var q=document.getElementById('gls-input').value.toLowerCase();
  document.querySelectorAll('.gls-item').forEach(function(el){
    el.style.display=el.textContent.toLowerCase().includes(q)?'':'none';
  });
}
</script>"""
    return (
        '<div class="dash-card">' +
        '<div class="dash-title">📖 ESG 名詞庫</div>' +
        '<div style="font-size:14px;color:var(--textM);margin-bottom:8px">CBAM · CSRD · IFRS S1/S2 · TNFD · SBTi · Scope 1/2/3 共16個核心名詞</div>' +
        html +
        '</div>'
    )

def build_html(news, market, reg_news):
    news_html     = '\n'.join(news_card(i) for i in news)
    market_html   = '\n'.join(news_card(i) for i in market)
    stat_reg_html = '\n'.join(reg_static_card(r,i) for i,r in enumerate(STATIC_REGULATIONS))
    live_reg_html = '\n'.join(reg_news_card(r,i) for i,r in enumerate(reg_news))

    # 中欄：儀表板
    right_col = (
        dashboard_summary(news, market, reg_news) +
        dashboard_reg_updates() +
        dashboard_impact_analysis() +
        dashboard_esg_radar() +
        dashboard_carbon_sim() +
        dashboard_re100() +
        dashboard_temp() +
        dashboard_cbam() +
        dashboard_tw_carbon_2027() +
        dashboard_enterprise_response()
    )

    # 右欄：永續報告書指引
    third_col = (
        dashboard_action_items() +
        dashboard_glossary() +
        dashboard_critical_minerals() +
        dashboard_uflpa() +
        dashboard_pfas() +
        dashboard_fgas() +
        dashboard_water() +
        dashboard_semi() +
        dashboard_gwp() +
        dashboard_ncv()
    )

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>ESG Regulatory Intelligence Platform | {DATE_STR}</title>
<style>
:root{{--g900:#0d2e1a;--g800:#1a4d2e;--g600:#2d7a4f;--g400:#4caf80;--g100:#e8f5ee;--amber:#f59e0b;--amberL:#fef3c7;--blue:#2563eb;--blueL:#dbeafe;--text1:#1a2e1f;--text2:#4b6358;--textM:#7a9488;--border:#c8e6d4;--bg:#f5fbf7;--card:#fff;--r-lg:14px;--r-md:8px}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Noto Sans TC',system-ui,sans-serif;background:var(--bg);color:var(--text1);line-height:1.7;font-size:21px}}
.header{{background:linear-gradient(135deg,var(--g900) 0%,#0a3d20 60%,#1a4d2e 100%);color:#fff;padding:2rem 2rem 1.5rem;text-align:center;border-bottom:4px solid var(--g400)}}
.h-badge{{display:inline-block;background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.25);border-radius:20px;padding:3px 12px;font-size:16px;letter-spacing:.06em;margin-bottom:.75rem}}
.header h1{{font-size:clamp(2.0rem,4vw,3.0rem);font-weight:700;margin-bottom:.3rem}}
.header h1 span{{color:var(--g400)}}
.header p{{opacity:.7;margin-bottom:1.5rem;font-size:20px}}
.stats{{display:flex;justify-content:center;gap:1.5rem;flex-wrap:wrap}}
.stat{{text-align:center}}
.stat-n{{font-size:2.4rem;font-weight:700;color:var(--g400);line-height:1}}
.stat-l{{font-size:15px;opacity:.6;margin-top:2px}}
.free-badge{{display:inline-block;background:rgba(76,175,128,.2);border:1px solid var(--g400);color:var(--g400);border-radius:20px;padding:2px 10px;font-size:16px;margin-top:.75rem}}
nav{{position:sticky;top:0;z-index:100;background:var(--card);border-bottom:1px solid var(--border);padding:0 1.5rem;display:flex;overflow-x:auto;box-shadow:0 2px 8px rgba(0,0,0,.06)}}
nav a{{display:flex;align-items:center;gap:5px;padding:.75rem 1rem;color:var(--text2);text-decoration:none;font-size:20px;font-weight:500;white-space:nowrap;border-bottom:3px solid transparent;transition:.2s}}
nav a:hover{{color:var(--g600);border-color:var(--g400)}}
.layout{{display:grid;grid-template-columns:1fr 400px 360px;gap:1.25rem;max-width:100%;margin:0;padding:1.25rem 1.5rem}}
@media(max-width:1300px){{.layout{{grid-template-columns:1fr 380px}}}}
@media(max-width:900px){{.layout{{grid-template-columns:1fr}}}}
.section{{margin-bottom:2.5rem}}
.sec-head{{display:flex;align-items:center;gap:10px;margin-bottom:1.25rem;padding-bottom:.75rem;border-bottom:2px solid var(--g100)}}
.sec-icon{{width:38px;height:38px;background:var(--g100);border-radius:var(--r-md);display:flex;align-items:center;justify-content:center;font-size:22px;flex-shrink:0}}
.sec-head h2{{font-size:1.65rem;font-weight:700;color:var(--g900)}}
.sec-head p{{font-size:16px;color:var(--textM);margin-top:1px}}
.sec-cnt{{margin-left:auto;background:var(--g100);color:var(--g600);padding:2px 8px;border-radius:20px;font-size:16px;font-weight:600;white-space:nowrap}}
.cards{{display:flex;flex-direction:column;gap:.75rem}}
.card{{background:var(--card);border:1px solid var(--border);border-left:4px solid var(--g400);border-radius:var(--r-lg);padding:1rem 1.25rem;display:flex;gap:.75rem;transition:.15s}}
.card:hover{{transform:translateY(-1px);box-shadow:0 4px 16px rgba(45,122,79,.1)}}
.reg-card{{border-left-color:var(--blue)}}
.card-rank{{font-size:1.8rem;font-weight:800;color:var(--g100);min-width:36px;text-align:center;padding-top:1px;line-height:1}}
.card-body{{flex:1;min-width:0}}
.card-meta{{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:6px}}
.card-title{{font-size:1.35rem;font-weight:600;color:var(--text1);margin-bottom:4px;line-height:1.4}}
.card-summary{{font-size:18px;color:var(--text2);line-height:1.6}}
.card-footer{{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin-top:8px;font-size:16px;color:var(--textM)}}
.areas{{display:flex;flex-wrap:wrap;gap:4px;margin-top:6px}}
.badge{{display:inline-block;padding:2px 7px;border-radius:20px;font-size:15px;font-weight:600}}
.badge-green{{background:var(--g100);color:var(--g600)}}
.badge-amber{{background:var(--amberL);color:#92400e}}
.badge-gray{{background:#f1efeb;color:#5f5e5a}}
.badge-blue{{background:var(--blueL);color:var(--blue)}}
.tag{{display:inline-block;padding:2px 7px;background:var(--bg);border:1px solid var(--border);border-radius:20px;font-size:15px;color:var(--text2)}}
.read-more{{color:var(--g600);text-decoration:none;font-weight:500;font-size:16px;margin-left:auto;white-space:nowrap}}
.read-more:hover{{text-decoration:underline}}
.divider{{display:flex;align-items:center;gap:8px;margin:1rem 0;font-size:16px;color:var(--textM)}}
.divider::before,.divider::after{{content:'';flex:1;border-top:1px dashed var(--border)}}
.empty{{text-align:center;padding:1.5rem;color:var(--textM);font-size:20px}}
.right-col{{display:flex;flex-direction:column;gap:1rem}}
.dash-card{{background:var(--card);border:1px solid var(--border);border-radius:var(--r-lg);padding:1.25rem 1.35rem}}
.dash-title{{font-size:1.27rem;font-weight:700;color:var(--g900);margin-bottom:.75rem;padding-bottom:.5rem;border-bottom:1px solid var(--g100)}}
.dash-stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:.5rem;text-align:center}}
.ds-item{{background:var(--bg);border-radius:var(--r-md);padding:.5rem .25rem}}
.ds-n{{font-size:2.1rem;font-weight:700;color:var(--g600);line-height:1}}
.ds-l{{font-size:15px;color:var(--textM);margin-top:2px}}
.dash-table{{width:100%;border-collapse:collapse;font-size:18px}}
.dash-table th{{background:var(--bg);padding:4px 6px;text-align:left;font-size:15px;color:var(--textM);font-weight:600;border-bottom:1px solid var(--border)}}
.dash-table td{{padding:5px 6px;border-bottom:1px solid var(--g100);vertical-align:middle}}
.dash-table tr:last-child td{{border-bottom:none}}
.rank-badge{{display:inline-block;background:var(--g100);color:var(--g600);border-radius:4px;padding:1px 5px;font-size:15px;font-weight:700}}
.ncv-tabs{{display:flex;flex-direction:column;gap:.5rem}}
.ncv-label{{font-size:15px;font-weight:600;color:var(--g600);background:var(--g100);padding:2px 8px;border-radius:4px;display:inline-block;margin-bottom:3px}}
.bar-chart{{display:flex;align-items:flex-end;gap:6px;height:140px;padding:4px 0}}
.bar-item{{display:flex;flex-direction:column;align-items:center;flex:1;position:relative;cursor:default}}
.bar-item:hover .bar-tooltip{{display:block}}
.bar-tooltip{{display:none;position:absolute;bottom:100%;left:50%;transform:translateX(-50%);background:var(--g900);color:#fff;padding:4px 8px;border-radius:6px;font-size:15px;white-space:nowrap;z-index:10;margin-bottom:4px}}
.bar-fill{{width:100%;border-radius:4px 4px 0 0;min-height:4px}}
.bar-val{{font-size:14px;font-weight:600;color:var(--text2);margin-top:2px}}
.bar-yr{{font-size:14px;color:var(--textM)}}
footer{{background:var(--g900);color:rgba(255,255,255,.6);text-align:center;padding:1.5rem;font-size:18px;margin-top:1rem}}
footer strong{{color:rgba(255,255,255,.9)}}
</style>
</head>
<body>
<header class="header">
  <div class="h-badge">🏛 ESG REGULATORY INTELLIGENCE PLATFORM</div>
  <h1>🏛 <span>ESG</span> Regulatory Intelligence</h1>
  <p>{DATE_STR} &nbsp;·&nbsp; {WEEK_STR} &nbsp;·&nbsp; 半導體業 · 光電業</p>
  <div class="stats">
    <div class="stat"><div class="stat-n">{len(news)}</div><div class="stat-l">精選新聞</div></div>
    <div class="stat"><div class="stat-n">{len(market)}</div><div class="stat-l">市場消息</div></div>
    <div class="stat"><div class="stat-n">{len(STATIC_REGULATIONS)}</div><div class="stat-l">追蹤法規</div></div>
    <div class="stat"><div class="stat-n">{len(reg_news)}</div><div class="stat-l">法規動態</div></div>
  </div>
  <div class="free-badge">✅ 免費開放 · 每週自動更新 · 半導體業 · 光電業 ESG 合規情報</div>
</header>
<nav>
  <a href="#news">📰 ESG NEWS</a>
  <a href="#market">📊 市場消息</a>
  <a href="#regulations">⚖️ 法規動態</a>
</nav>
<div class="layout">
  <div class="left-col">
    {news_summary_card(news, market)}
    <section class="section" id="news">
      <div class="sec-head">
        <div class="sec-icon">📰</div>
        <div><h2>ESG NEWS</h2><p>國際 + 台灣動態 · 自動過濾低價值資訊 · 連結已驗證</p></div>
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
        <div><h2>⚖️ 法規動態</h2><p>全球與台灣法規持續追蹤 · 點擊法規名稱連結官方資訊</p></div>
        <span class="sec-cnt">{len(STATIC_REGULATIONS)+len(reg_news)} 項</span>
      </div>
      <div class="divider">📋 重要法規持續追蹤</div>
      <div class="cards">{stat_reg_html}</div>
      <div class="divider">🔴 本週最新法規動態</div>
      <div class="cards">{live_reg_html or '<div class="empty">本週暫無有效法規動態連結</div>'}</div>
    </section>
  </div>
  <div class="right-col">{right_col}</div>
  <div class="right-col">{third_col}</div>
</div>
<footer>
  <p><strong>ESG 智能週報（免費版）</strong> &nbsp;·&nbsp; 資料來源：Google News RSS · IPCC AR6 · WMO · 環境部 · 各企業永續報告書 &nbsp;·&nbsp; {DATE_STR} 更新</p>
  <p style="margin-top:4px">所有新聞連結已自動驗證可開啟 · 本報告僅供參考，投資決策請諮詢專業人士</p>
</footer>
</body>
</html>"""

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
