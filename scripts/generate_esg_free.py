"""
ESG Weekly Newsletter - 完全免費版
使用 Google News RSS，不需要任何 API Key
所有連結皆為可直接開啟的有效網址
"""

import feedparser
import requests
import html as html_lib
import os
import re
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

# ── 時間設定 ─────────────────────────────────────────────────────────────────
TW_TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TW_TZ)
DATE_STR = NOW.strftime("%Y年%m月%d日")
WEEK_STR = NOW.strftime("第%W週")
FILENAME = NOW.strftime("%Y-%m-%d")

# ── 已知 403 / 無法直接開啟的網域黑名單 ──────────────────────────────────────
# 遇到這些網域的連結一律跳過，如發現新的問題網域可在此新增
BLOCKED_DOMAINS = [
    'esgtoday.com',
    'ft.com',
    'wsj.com',
    'bloomberg.com',
    'barrons.com',
]

# ── RSS 來源設定（全部使用 Google News，連結穩定可直接開啟）─────────────────

# 全球 ESG 新聞
NEWS_FEEDS = [
    {
        "name": "Google News - ESG 綜合",
        "url": "https://news.google.com/rss/search?q=ESG+sustainability&hl=en&gl=US&ceid=US:en",
        "category": "ESG綜合", "region": "全球"
    },
    {
        "name": "Google News - 氣候變遷",
        "url": "https://news.google.com/rss/search?q=climate+change+carbon+emissions&hl=en&gl=US&ceid=US:en",
        "category": "氣候", "region": "全球"
    },
    {
        "name": "Google News - ESG 投資",
        "url": "https://news.google.com/rss/search?q=ESG+investing+sustainable+finance&hl=en&gl=US&ceid=US:en",
        "category": "投資", "region": "全球"
    },
    {
        "name": "Google News - 再生能源",
        "url": "https://news.google.com/rss/search?q=renewable+energy+solar+wind+power&hl=en&gl=US&ceid=US:en",
        "category": "能源", "region": "全球"
    },
    {
        "name": "Google News - 企業永續",
        "url": "https://news.google.com/rss/search?q=corporate+sustainability+ESG+report&hl=en&gl=US&ceid=US:en",
        "category": "ESG綜合", "region": "全球"
    },
    {
        "name": "Google News - 亞洲 ESG",
        "url": "https://news.google.com/rss/search?q=ESG+Asia+Pacific+sustainability&hl=en&gl=US&ceid=US:en",
        "category": "ESG綜合", "region": "亞洲"
    },
    # 台灣在地資訊
    {
        "name": "Google News - 台灣ESG",
        "url": "https://news.google.com/rss/search?q=台灣+ESG+永續&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
        "category": "ESG綜合", "region": "台灣"
    },
    {
        "name": "Google News - 台灣碳費",
        "url": "https://news.google.com/rss/search?q=台灣+碳費+碳排放&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
        "category": "氣候", "region": "台灣"
    },
    {
        "name": "Google News - 台灣永續報告",
        "url": "https://news.google.com/rss/search?q=永續報告書+ESG揭露+金管會&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
        "category": "ESG綜合", "region": "台灣"
    },
]

# 市場消息
MARKET_FEEDS = [
    {
        "name": "Google News - 綠色債券",
        "url": "https://news.google.com/rss/search?q=green+bond+sustainable+finance&hl=en&gl=US&ceid=US:en",
        "category": "債券", "region": "全球"
    },
    {
        "name": "Google News - ESG 基金",
        "url": "https://news.google.com/rss/search?q=ESG+fund+sustainable+investment&hl=en&gl=US&ceid=US:en",
        "category": "基金", "region": "全球"
    },
    {
        "name": "Google News - 碳市場",
        "url": "https://news.google.com/rss/search?q=carbon+credit+carbon+market+price&hl=en&gl=US&ceid=US:en",
        "category": "碳市場", "region": "全球"
    },
    {
        "name": "Google News - ESG 評級",
        "url": "https://news.google.com/rss/search?q=ESG+rating+MSCI+Sustainalytics+score&hl=en&gl=US&ceid=US:en",
        "category": "評級", "region": "全球"
    },
    {
        "name": "Google News - 台灣綠色金融",
        "url": "https://news.google.com/rss/search?q=台灣+綠色金融+ESG投資&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
        "category": "投資", "region": "台灣"
    },
]

# 法規動態
REGULATION_FEEDS = [
    {
        "name": "Google News - CSRD/SFDR",
        "url": "https://news.google.com/rss/search?q=CSRD+SFDR+ESG+regulation+Europe&hl=en&gl=US&ceid=US:en",
        "category": "法規", "region": "歐洲"
    },
    {
        "name": "Google News - SEC 氣候披露",
        "url": "https://news.google.com/rss/search?q=SEC+climate+disclosure+rule&hl=en&gl=US&ceid=US:en",
        "category": "法規", "region": "美洲"
    },
    {
        "name": "Google News - ISSB 準則",
        "url": "https://news.google.com/rss/search?q=ISSB+IFRS+sustainability+standard&hl=en&gl=US&ceid=US:en",
        "category": "標準", "region": "全球"
    },
    {
        "name": "Google News - 碳定價政策",
        "url": "https://news.google.com/rss/search?q=carbon+tax+carbon+pricing+policy&hl=en&gl=US&ceid=US:en",
        "category": "碳政策", "region": "全球"
    },
    {
        "name": "Google News - 台灣碳費法規",
        "url": "https://news.google.com/rss/search?q=台灣+碳費+氣候法+環境部&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
        "category": "法規", "region": "台灣"
    },
]

# ── 工具函式 ──────────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def is_valid_url(url: str) -> bool:
    """
    檢查連結是否有效：
    1. 必須是 http/https 開頭
    2. 不在黑名單網域內
    3. 實際發送請求確認回傳 200
    """
    if not url or not url.startswith("http"):
        return False
    # 黑名單過濾
    for domain in BLOCKED_DOMAINS:
        if domain in url:
            print(f"    ✗ 黑名單封鎖: {domain}")
            return False
    # 實際測試連結
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8,
                            allow_redirects=True, stream=True)
        resp.close()
        if resp.status_code >= 400:
            print(f"    ✗ HTTP {resp.status_code}: {url[:60]}")
            return False
        return True
    except Exception as e:
        print(f"    ✗ 連線失敗: {url[:60]}")
        return False

def clean_html(text: str) -> str:
    text = re.sub(r'<[^>]+>', ' ', text or '')
    text = html_lib.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:200] + '…' if len(text) > 200 else text

def parse_date(entry) -> str:
    for attr in ('published', 'updated'):
        val = getattr(entry, attr, None)
        if val:
            try:
                dt = parsedate_to_datetime(val)
                return dt.astimezone(TW_TZ).strftime('%Y/%m/%d')
            except Exception:
                return val[:10] if len(val) >= 10 else val
    return '近期'

def fetch_feed(feed_cfg: dict, max_items: int = 6) -> list:
    """抓取單一 RSS Feed，每筆都驗證連結可用性"""
    items = []
    try:
        resp = requests.get(feed_cfg['url'], headers=HEADERS, timeout=15)
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)

        checked = 0
        for entry in parsed.entries:
            if checked >= max_items:
                break
            title = clean_html(entry.get('title', ''))
            summary = clean_html(entry.get('summary', '') or entry.get('description', ''))
            link = entry.get('link', '')

            if not title or len(title) < 10:
                continue

            checked += 1
            print(f"    檢查: {title[:50]}…")

            if not is_valid_url(link):
                continue

            items.append({
                'title': title,
                'summary': summary or '點擊標題查看詳情',
                'source': feed_cfg['name'],
                'date': parse_date(entry),
                'category': feed_cfg['category'],
                'region': feed_cfg.get('region', '全球'),
                'url': link,
            })

    except Exception as e:
        print(f"  ⚠ 無法取得 {feed_cfg['name']}: {e}")
    return items

def fetch_all(feeds: list, top_n: int = 10) -> list:
    """抓取所有來源並去重，有幾筆算幾筆，不強湊 top_n"""
    all_items = []
    seen_titles = set()

    for feed in feeds:
        if len(all_items) >= top_n:
            break
        print(f"  → {feed['name']}")
        items = fetch_feed(feed, max_items=5)
        for item in items:
            if len(all_items) >= top_n:
                break
            key = item['title'][:40].lower()
            if key not in seen_titles:
                seen_titles.add(key)
                all_items.append(item)

    for i, item in enumerate(all_items):
        item['rank'] = i + 1
    return all_items

# ── 固定法規資料（官方網址，穩定可靠）───────────────────────────────────────

STATIC_REGULATIONS = [
    {
        "name": "歐盟企業永續報告指令 (CSRD)",
        "jurisdiction": "歐盟",
        "status": "已生效",
        "effective_date": "2024年起分階段實施",
        "summary": "要求大型企業及上市公司進行標準化永續資訊揭露，取代原有 NFRD，適用範圍擴展至約 5 萬家企業，並需經第三方確信。",
        "impact_areas": ["永續報告", "資訊揭露", "供應鏈"],
        "url": "https://finance.ec.europa.eu/capital-markets-union-and-financial-markets/company-reporting-and-auditing/company-reporting/corporate-sustainability-reporting_en"
    },
    {
        "name": "ISSB 永續揭露準則 (IFRS S1/S2)",
        "jurisdiction": "全球",
        "status": "已生效",
        "effective_date": "2023年發布，各國陸續採用",
        "summary": "國際財務報告準則基金會發布全球統一永續揭露基準，S1 為一般要求，S2 專注氣候相關揭露，台灣、日本、英國等多國已宣布採用時程。",
        "impact_areas": ["氣候揭露", "財務報告", "永續準則"],
        "url": "https://www.ifrs.org/issued-standards/ifrs-sustainability-disclosure-standards/"
    },
    {
        "name": "歐盟永續金融揭露規範 (SFDR)",
        "jurisdiction": "歐盟",
        "status": "已生效",
        "effective_date": "2021年起，持續更新中",
        "summary": "要求金融市場參與者揭露 ESG 整合方式，將產品分為 Article 6/8/9 三類，並規範主要不利影響 (PAI) 揭露，目前進行修訂。",
        "impact_areas": ["基金管理", "投資產品", "ESG標籤"],
        "url": "https://finance.ec.europa.eu/sustainable-finance/disclosures/sustainability-related-disclosure-financial-services-sector_en"
    },
    {
        "name": "美國 SEC 氣候披露規則",
        "jurisdiction": "美國",
        "status": "即將生效",
        "effective_date": "2025–2026年分階段",
        "summary": "要求上市公司揭露氣候相關風險及溫室氣體排放量（Scope 1&2），目前仍在司法審查中，最終範圍尚未確定。",
        "impact_areas": ["氣候揭露", "溫室氣體", "上市公司"],
        "url": "https://www.sec.gov/rules-regulations/2024/03/the-enhancement-and-standardization-of-climate-related-disclosures"
    },
    {
        "name": "台灣上市櫃公司永續報告書申報規範",
        "jurisdiction": "台灣",
        "status": "已生效",
        "effective_date": "分階段：2023年起擴大適用",
        "summary": "金管會要求上市櫃公司依規模分階段申報永續報告書，逐步接軌 ISSB 準則，資本額 20 億以上須取得第三方確信。",
        "impact_areas": ["永續報告", "公司治理", "ESG揭露"],
        "url": "https://cgc.twse.com.tw/frontEN/sustainReport"
    },
    {
        "name": "台灣碳費徵收制度",
        "jurisdiction": "台灣",
        "status": "已生效",
        "effective_date": "2024年起徵收，2025年正式開徵",
        "summary": "環境部對年排放量逾 2.5 萬噸 CO₂ 的排放源徵收碳費，初期費率每噸 300 元（自主減量可申請優惠），為亞洲首批碳定價機制之一。",
        "impact_areas": ["碳定價", "製造業", "能源業"],
        "url": "https://www.epa.gov.tw/climate/4B9E1E3855AAEE81"
    },
    {
        "name": "歐盟碳邊境調整機制 (CBAM)",
        "jurisdiction": "歐盟",
        "status": "已生效",
        "effective_date": "2023年10月試行，2026年正式",
        "summary": "對進口至歐盟的鋼鐵、鋁、水泥、化肥、電力、氫等高碳產品徵收碳邊境稅，防止碳洩漏，對台灣出口商影響深遠。",
        "impact_areas": ["碳關稅", "國際貿易", "製造業"],
        "url": "https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism_en"
    },
]

def fetch_regulation_news() -> list:
    return fetch_all(REGULATION_FEEDS, top_n=5)

# ── HTML 生成 ─────────────────────────────────────────────────────────────────

CAT_ICONS = {
    "氣候": "🌍", "投資": "📈", "能源": "⚡", "治理": "🏛️",
    "基金": "💼", "債券": "📋", "評級": "⭐", "法規": "📜",
    "標準": "📐", "碳市場": "♻️", "碳政策": "🌿", "ESG綜合": "🌱",
    "全球": "🌐", "亞洲": "🌏", "歐洲": "🇪🇺", "美洲": "🌎", "台灣": "🇹🇼",
}

STATUS_COLOR = {
    "已生效":   ("badge-green", "已生效"),
    "即將生效": ("badge-amber", "即將生效"),
    "草案":     ("badge-gray",  "草案"),
}

def news_card(item: dict) -> str:
    rank     = item.get('rank', '')
    title    = item.get('title', '')
    summary  = item.get('summary', '')
    source   = item.get('source', '')
    date     = item.get('date', '')
    url      = item.get('url', '')
    category = item.get('category', '')
    region   = item.get('region', '')

    cat_icon = CAT_ICONS.get(category, '📌')
    reg_icon = CAT_ICONS.get(region, '🌐')
    link = f'<a href="{url}" target="_blank" rel="noopener" class="read-more">閱讀原文 →</a>' if url else ''

    return f"""<div class="card">
      <div class="card-rank">#{rank}</div>
      <div class="card-body">
        <div class="card-meta">
          <span class="tag">{cat_icon} {category}</span>
          <span class="tag">{reg_icon} {region}</span>
        </div>
        <h3 class="card-title">{title}</h3>
        <p class="card-summary">{summary}</p>
        <div class="card-footer">
          <span>📰 {source}</span>
          <span>🗓 {date}</span>
          {link}
        </div>
      </div>
    </div>"""

def reg_static_card(item: dict, idx: int) -> str:
    name           = item.get('name', '')
    jurisdiction   = item.get('jurisdiction', '')
    status         = item.get('status', '草案')
    effective_date = item.get('effective_date', '')
    summary        = item.get('summary', '')
    areas          = item.get('impact_areas', [])
    url            = item.get('url', '')

    cls, label = STATUS_COLOR.get(status, ("badge-gray", status))
    areas_html = ' '.join(f'<span class="tag">{a}</span>' for a in areas)
    jur_icon   = CAT_ICONS.get(jurisdiction, '🏛️')
    link = f'<a href="{url}" target="_blank" rel="noopener" class="read-more">查看詳情 →</a>' if url else ''

    return f"""<div class="card reg-card">
      <div class="card-rank">#{idx+1}</div>
      <div class="card-body">
        <div class="card-meta">
          <span class="badge {cls}">{label}</span>
          <span class="tag">{jur_icon} {jurisdiction}</span>
        </div>
        <h3 class="card-title">{name}</h3>
        <p class="card-summary">{summary}</p>
        <div class="areas">{areas_html}</div>
        <div class="card-footer">
          <span>📅 {effective_date}</span>
          {link}
        </div>
      </div>
    </div>"""

def reg_news_card(item: dict, idx: int) -> str:
    title   = item.get('title', '')
    summary = item.get('summary', '')
    source  = item.get('source', '')
    date    = item.get('date', '')
    url     = item.get('url', '')
    region  = item.get('region', '')

    reg_icon = CAT_ICONS.get(region, '🌐')
    link = f'<a href="{url}" target="_blank" rel="noopener" class="read-more">閱讀原文 →</a>' if url else ''

    return f"""<div class="card reg-card">
      <div class="card-rank">◉</div>
      <div class="card-body">
        <div class="card-meta">
          <span class="badge badge-blue">最新動態</span>
          <span class="tag">{reg_icon} {region}</span>
        </div>
        <h3 class="card-title">{title}</h3>
        <p class="card-summary">{summary}</p>
        <div class="card-footer"><span>📰 {source}</span><span>🗓 {date}</span>{link}</div>
      </div>
    </div>"""

def build_html(news: list, market: list, reg_news: list) -> str:
    news_html       = '\n'.join(news_card(i) for i in news)
    market_html     = '\n'.join(news_card(i) for i in market)
    static_reg_html = '\n'.join(reg_static_card(r, i) for i, r in enumerate(STATIC_REGULATIONS))
    live_reg_html   = '\n'.join(reg_news_card(r, i) for i, r in enumerate(reg_news))

    news_cnt   = f"Top {len(news)}"   if news   else "本週暫無資料"
    market_cnt = f"Top {len(market)}" if market else "本週暫無資料"

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>ESG 每週報告 | {DATE_STR}</title>
<style>
:root{{
  --g900:#0d2e1a;--g800:#1a4d2e;--g600:#2d7a4f;--g400:#4caf80;--g100:#e8f5ee;--g50:#f0faf4;
  --amber:#f59e0b;--amberL:#fef3c7;
  --blue:#2563eb;--blueL:#dbeafe;
  --text1:#1a2e1f;--text2:#4b6358;--textM:#7a9488;
  --border:#c8e6d4;--bg:#f5fbf7;--card:#fff;
  --r-lg:14px;--r-md:8px;
}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Noto Sans TC',system-ui,sans-serif;background:var(--bg);color:var(--text1);line-height:1.7;font-size:15px}}
.header{{background:var(--g900);color:#fff;padding:3rem 2rem 2.5rem;text-align:center}}
.h-badge{{display:inline-block;background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.25);border-radius:20px;padding:4px 14px;font-size:11px;letter-spacing:.06em;margin-bottom:1rem}}
.header h1{{font-size:clamp(1.8rem,4vw,2.6rem);font-weight:700;margin-bottom:.4rem}}
.header h1 span{{color:var(--g400)}}
.header p{{opacity:.7;margin-bottom:2rem}}
.stats{{display:flex;justify-content:center;gap:2rem;flex-wrap:wrap}}
.stat{{text-align:center}}
.stat-n{{font-size:2rem;font-weight:700;color:var(--g400);line-height:1}}
.stat-l{{font-size:11px;opacity:.6;margin-top:2px}}
.free-badge{{display:inline-block;background:rgba(76,175,128,.2);border:1px solid var(--g400);color:var(--g400);border-radius:20px;padding:3px 12px;font-size:11px;margin-top:1rem}}
nav{{position:sticky;top:0;z-index:100;background:var(--card);border-bottom:1px solid var(--border);padding:0 2rem;display:flex;overflow-x:auto;box-shadow:0 2px 8px rgba(0,0,0,.06)}}
nav a{{display:flex;align-items:center;gap:6px;padding:1rem 1.25rem;color:var(--text2);text-decoration:none;font-size:14px;font-weight:500;white-space:nowrap;border-bottom:3px solid transparent;transition:.2s}}
nav a:hover{{color:var(--g600);border-color:var(--g400)}}
.container{{max-width:1100px;margin:0 auto;padding:2.5rem 1.5rem}}
.section{{margin-bottom:3.5rem}}
.sec-head{{display:flex;align-items:center;gap:12px;margin-bottom:1.5rem;padding-bottom:1rem;border-bottom:2px solid var(--g100)}}
.sec-icon{{width:44px;height:44px;background:var(--g100);border-radius:var(--r-md);display:flex;align-items:center;justify-content:center;font-size:22px}}
.sec-head h2{{font-size:1.3rem;font-weight:700;color:var(--g900)}}
.sec-head p{{font-size:12px;color:var(--textM);margin-top:2px}}
.sec-cnt{{margin-left:auto;background:var(--g100);color:var(--g600);padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600}}
.cards{{display:flex;flex-direction:column;gap:1rem}}
.card{{background:var(--card);border:1px solid var(--border);border-left:4px solid var(--g400);border-radius:var(--r-lg);padding:1.25rem 1.5rem;display:flex;gap:1rem;transition:.15s}}
.card:hover{{transform:translateY(-2px);box-shadow:0 6px 20px rgba(45,122,79,.1)}}
.reg-card{{border-left-color:var(--blue)}}
.card-rank{{font-size:1.4rem;font-weight:800;color:var(--g100);min-width:42px;text-align:center;padding-top:2px;line-height:1}}
.card-body{{flex:1;min-width:0}}
.card-meta{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px}}
.card-title{{font-size:1rem;font-weight:600;color:var(--text1);margin-bottom:6px;line-height:1.45}}
.card-summary{{font-size:14px;color:var(--text2);line-height:1.65}}
.card-footer{{display:flex;flex-wrap:wrap;align-items:center;gap:12px;margin-top:10px;font-size:12px;color:var(--textM)}}
.areas{{display:flex;flex-wrap:wrap;gap:5px;margin-top:8px}}
.badge{{display:inline-block;padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600}}
.badge-green{{background:var(--g100);color:var(--g600)}}
.badge-amber{{background:var(--amberL);color:#92400e}}
.badge-gray{{background:#f1efeb;color:#5f5e5a}}
.badge-blue{{background:var(--blueL);color:var(--blue)}}
.tag{{display:inline-block;padding:2px 8px;background:var(--bg);border:1px solid var(--border);border-radius:20px;font-size:11px;color:var(--text2)}}
.read-more{{color:var(--g600);text-decoration:none;font-weight:500;font-size:12px;margin-left:auto}}
.read-more:hover{{text-decoration:underline}}
.divider{{display:flex;align-items:center;gap:10px;margin:1.25rem 0;font-size:12px;color:var(--textM)}}
.divider::before,.divider::after{{content:'';flex:1;border-top:1px dashed var(--border)}}
.empty{{text-align:center;padding:2rem;color:var(--textM);font-size:14px}}
footer{{background:var(--g900);color:rgba(255,255,255,.6);text-align:center;padding:2rem;font-size:13px}}
footer strong{{color:rgba(255,255,255,.9)}}
@media(max-width:640px){{.card{{flex-direction:column}}.stats{{gap:1.25rem}}}}
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

<main class="container">

  <section class="section" id="news">
    <div class="sec-head">
      <div class="sec-icon">📰</div>
      <div><h2>ESG 全球 + 台灣新聞</h2><p>來自 Google News 彙整，每筆連結皆已驗證可直接開啟</p></div>
      <span class="sec-cnt">{news_cnt}</span>
    </div>
    <div class="cards">{news_html if news_html else '<div class="empty">本週暫無有效新聞連結</div>'}</div>
  </section>

  <section class="section" id="market">
    <div class="sec-head">
      <div class="sec-icon">📊</div>
      <div><h2>ESG 市場消息</h2><p>綠色債券、ESG 基金、碳市場、投資評級最新動態</p></div>
      <span class="sec-cnt">{market_cnt}</span>
    </div>
    <div class="cards">{market_html if market_html else '<div class="empty">本週暫無有效市場消息連結</div>'}</div>
  </section>

  <section class="section" id="regulations">
    <div class="sec-head">
      <div class="sec-icon">🏛</div>
      <div><h2>ESG 法規動態</h2><p>全球與台灣重要法規持續追蹤 + 本週最新法規新聞</p></div>
      <span class="sec-cnt">{len(STATIC_REGULATIONS) + len(reg_news)} 項</span>
    </div>
    <div class="divider">📋 重要法規持續追蹤（含台灣）</div>
    <div class="cards">{static_reg_html}</div>
    <div class="divider">🔴 本週最新法規動態</div>
    <div class="cards">{live_reg_html if live_reg_html else '<div class="empty">本週暫無有效法規動態連結</div>'}</div>
  </section>

</main>

<footer>
  <p><strong>ESG 智能週報（免費版）</strong> &nbsp;·&nbsp; 資料來源：Google News RSS &nbsp;·&nbsp; {DATE_STR} 更新</p>
  <p style="margin-top:6px">所有新聞連結已自動驗證可開啟 · 本報告僅供參考，投資決策請諮詢專業人士</p>
</footer>
</body>
</html>"""

# ── 主程式 ────────────────────────────────────────────────────────────────────

def main():
    print(f"🌿 ESG 免費週報生成開始 — {DATE_STR}")
    print(f"🔍 每筆新聞連結將自動驗證，無效連結自動略過\n")

    print("📰 抓取全球+台灣新聞...")
    news = fetch_all(NEWS_FEEDS, top_n=10)

    print("\n📊 抓取市場消息...")
    market = fetch_all(MARKET_FEEDS, top_n=10)

    print("\n🏛 抓取法規動態...")
    reg_news = fetch_regulation_news()

    print("\n🎨 生成 HTML...")
    html = build_html(news, market, reg_news)

    os.makedirs("docs/archive", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    with open(f"docs/archive/{FILENAME}.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n🎉 完成！")
    print(f"   新聞：{len(news)} 筆 | 市場：{len(market)} 筆 | 法規動態：{len(reg_news)} 筆")
    print(f"   所有連結均已驗證可直接開啟")

if __name__ == "__main__":
    main()
    
