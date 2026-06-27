"""
scraper.py — 网页新闻抓取器
为没有 RSS 或 RSS 不可达的中东新闻网站提供 HTML 页面直接抓取能力。

支持策略: ld+json → article links → manual title extraction
每个抓取器带超时保护，超时返回空列表不阻塞整体流程。
"""
import re
import ssl
import urllib.request
import json
from urllib.parse import urljoin


_CTX = None

def _ctx():
    global _CTX
    if _CTX is None:
        _CTX = ssl.create_default_context()
        _CTX.check_hostname = False
        _CTX.verify_mode = ssl.CERT_NONE
    return _CTX


def _fetch(url: str, timeout: int = 12) -> str | None:
    """下载页面内容，超时或失败返回 None"""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en,ar;q=0.9",
        })
        resp = urllib.request.urlopen(req, timeout=timeout, context=_ctx())
        return resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return None


def _ld_json_articles(html: str) -> list[dict]:
    """从 ld+json 提取所有 NewsArticle/Article"""
    results = []
    for m in re.finditer(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.DOTALL,
    ):
        try:
            data = json.loads(m.group(1))
            items = data.get("@graph", [data]) if isinstance(data, dict) else data
            if isinstance(items, list):
                for item in items:
                    t = (item.get("@type") or [])
                    if isinstance(t, list):
                        t = " ".join(t)
                    if isinstance(item, dict) and any(k in str(t) for k in
                        ("NewsArticle", "Article", "BlogPosting", "Report")):
                        results.append({
                            "title": item.get("headline") or item.get("name", ""),
                            "url": item.get("url", ""),
                            "summary": item.get("description", ""),
                            "pub_date": item.get("datePublished", ""),
                        })
        except Exception:
            continue
    return results


def _link_articles(html: str, base: str, patterns: list[str]) -> list[dict]:
    """用正则从 HTML 中提取文章链接 + 链接文本作为标题"""
    results = []
    seen = set()
    for pat in patterns:
        for m in re.finditer(pat, html, re.IGNORECASE):
            href = m.group(1) if m.lastindex else m.group(0)
            if not href or href in seen:
                continue
            seen.add(href)
            full_url = urljoin(base, href)
            # 取链接附近文本做标题
            ctx_end = min(len(html), m.end() + 500)
            ctx_text = html[m.start():ctx_end]
            title = ""
            # 策略1: 离链接最近的 heading (h1-h3)
            tm = re.search(r'<h[123][^>]*>\s*([^<]{10,300})\s*</h[123]>', ctx_text)
            if tm:
                title = re.sub(r'<[^>]+>', '', tm.group(1)).strip()
            # 策略2: 链接内部文本
            if not title:
                tm = re.search(r'>\s*([^<]{10,300}?)\s*</a>', ctx_text)
                if tm:
                    title = re.sub(r'<[^>]+>', '', tm.group(1)).strip()
            # 策略3: title attribute
            if not title:
                tm = re.search(r'title=[\"\\\']([^\"\\\']{10,300})[\"\\\']', ctx_text)
                if tm:
                    title = tm.group(1).strip()
            # 策略4: URL stem fallback
            if not title:
                title = href.rstrip('/').rsplit('/', 1)[-1].replace('-', ' ').replace('_', ' ')[:120]
            if title:
                results.append({"title": title, "url": full_url, "summary": "", "pub_date": ""})
    return results


# ================================================================
#  各网站专用抓取器（按 www.txt 列表）
# ================================================================

def fetch_youm7() -> list[dict]:
    """اليوم السابع (Youm7) - 首页文章链接 + ld+json"""
    html = _fetch("https://www.youm7.com/")
    if not html:
        return []
    articles = _link_articles(html, "https://www.youm7.com", [
        r'/story/\d{4}/\d{1,2}/\d{1,2}/[^"\'\s]+',
    ])
    articles += _ld_json_articles(html)
    return _dedup(articles)[:50]


def fetch_ahram() -> list[dict]:
    """بوابة الأهرام (Ahram Gate) - 英文版首页"""
    html = _fetch("https://english.ahram.org.eg/", timeout=12)
    if not html:
        return []
    # Ahram EN uses relative URLs without leading slash: NewsContent/1/1234/ID/...
    # and absolute URLs via QueryString: ?NewsContentID=1234
    articles = _link_articles(html, "https://english.ahram.org.eg/", [
        r'NewsContent/\d+/\d+/\d+/[^"\'\s]+\.aspx',
        r'/[^"\'\s]*\?NewsContentID=\d+',
    ])
    return _dedup(articles)[:50]


def fetch_arabnews() -> list[dict]:
    """Arab News - 英文首页"""
    html = _fetch("https://www.arabnews.com/", timeout=12)
    if not html:
        return []
    articles = _ld_json_articles(html)
    if not articles:
        articles = _link_articles(html, "https://www.arabnews.com", [
            r'/node/\d+',
        ])
    return _dedup(articles)[:50]


def fetch_spa() -> list[dict]:
    """SPA - extract from __NEXT_DATA__ JSON in page"""
    html = _fetch("https://www.spa.gov.sa/en/", timeout=12)
    if not html:
        return []
    articles = []
    # SPA uses Next.js; news data is in a script tag as JSON
    for m in re.finditer(
        r'<script[^>]*>\s*(\{"props".*?)\s*</script>', html, re.DOTALL
    ):
        try:
            data = json.loads(m.group(1))
            # Navigate: props -> pageProps -> mainNews
            news = (
                data.get("props", {})
                .get("pageProps", {})
                .get("mainNews", [])
            )
            for item in news:
                title = item.get("title", "")
                # sharable_link is like "spa.gov.sa/en/N2621278?type=news&uuid=..."
                link = item.get("sharable_link", "")
                if link and not link.startswith("http"):
                    link = "https://" + link
                pub_date = item.get("published_at", "")
                if title and link:
                    articles.append({
                        "title": title, "url": link,
                        "summary": item.get("subtitle", ""),
                        "pub_date": pub_date,
                    })
            if articles:
                break
        except Exception:
            continue
    return _dedup(articles)[:50]


def fetch_gcc() -> list[dict]:
    """GCC Secretariat - RSS/News 页面不可用，返回空"""
    return []


def fetch_qna() -> list[dict]:
    """Qatar News Agency - 英文首页"""
    html = _fetch("https://www.qna.org.qa/en/", timeout=12)
    if not html:
        return []
    articles = _ld_json_articles(html)
    if not articles:
        articles = _link_articles(html, "https://www.qna.org.qa", [
            r'/en/[^"\'\s]*(?:News|news|Article|article)[^"\'\s]*\.aspx',
        ])
    return _dedup(articles)[:50]


def fetch_alaraby() -> list[dict]:
    """العربي الجديد (Al Araby) - 网站 403，尝试通过已有 RSS"""
    # newarab.com RSS 已在 RSS_FEEDS 中覆盖；这里返回空
    return []


def fetch_reuters_me() -> list[dict]:
    """Reuters Middle East - 首页 ld+json"""
    html = _fetch("https://www.reuters.com/world/middle-east/", timeout=12)
    if not html:
        return []
    return _ld_json_articles(html)[:50]


def fetch_aljazeera_me() -> list[dict]:
    """Al Jazeera Middle East section - 英文版"""
    html = _fetch("https://www.aljazeera.com/middle-east/", timeout=12)
    if not html:
        return []
    articles = _ld_json_articles(html)
    if not articles:
        articles = _link_articles(html, "https://www.aljazeera.com", [
            r'/news/\d{4}/[^"\'\s]+',
            r'/features/\d{4}/[^"\'\s]+',
        ])
    return _dedup(articles)[:50]


def fetch_alarabiya_en() -> list[dict]:
    """Al Arabiya English - 网站 403; 已有 RSS_FEEDS 覆盖"""
    return []


def _dedup(articles: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for a in articles:
        u = a.get("url", "")
        if u and u not in seen:
            seen.add(u)
            out.append(a)
    return out


# ================================================================
#  注册表 —— 与 www.txt 网站对应
# ================================================================

SCRAPER_REGISTRY = {
    # www.txt #1: Al Arabiya → 已有 RSS + scraper (403 时返回空)
    "alarabiya_en": {
        "func": fetch_alarabiya_en, "name": "Al Arabiya English", "lang": "en",
        "note": "网站 403 反爬，RSS 已在 config.py 覆盖"
    },
    # www.txt #2: Al Jazeera → 已有 RSS + 英文版 scraper
    "aljazeera_me": {
        "func": fetch_aljazeera_me, "name": "Al Jazeera — Middle East", "lang": "en",
        "note": "英文版 scraper; 阿拉伯语网站连接超时"
    },
    # www.txt #3: Youm7 → 无 RSS，首页抓取
    "youm7": {
        "func": fetch_youm7, "name": "اليوم السابع (Youm7)", "lang": "ar",
        "note": "无有效 RSS，从首页抓取文章链接"
    },
    # www.txt #4: SANA → 已有 RSS ✅
    # www.txt #5: Al Riyadh → 已有 RSS ✅
    # www.txt #6: Ahram Gate → 无 RSS
    "ahram": {
        "func": fetch_ahram, "name": "بوابة الأهرام (Ahram Gate)", "lang": "ar",
        "note": "从英文版首页抓取"
    },
    # www.txt #7: AA → 已有 RSS (EN + AR) ✅
    # www.txt #8: Reuters → 无 RSS, 网页抓取
    "reuters_me": {
        "func": fetch_reuters_me, "name": "Reuters — Middle East", "lang": "en",
        "note": "从 ld+json 提取"
    },
    # www.txt #9: Arab News → 已有 RSS + scraper 备用
    "arabnews": {
        "func": fetch_arabnews, "name": "Arab News", "lang": "en",
        "note": "RSS 可能损坏，网页抓取备用"
    },
    # www.txt #10: Egypt Independent → 新的埃及英文媒体
    "egypt_independent": {
        "func": fetch_egypt_independent, "name": "Egypt Independent", "lang": "en",
        "note": "从首页抓取"
    },
    # www.txt #11: GCC → 无 RSS
    "gcc": {
        "func": fetch_gcc, "name": "GCC Secretariat", "lang": "en",
        "note": "从首页新闻抓取"
    },
    # www.txt #12: SPA → 无有效 RSS
    "spa": {
        "func": fetch_spa, "name": "SPA — وكالة الأنباء السعودية", "lang": "ar",
        "note": "从首页 N-link 抓取"
    },
    # www.txt #13: Al Araby / The New Arab → RSS 已覆盖
    "alaraby": {
        "func": fetch_alaraby, "name": "العربي الجديد (Al Araby)", "lang": "ar",
        "note": "网站 403; RSS 已在 config.py 覆盖"
    },
}


def scrape_all(max_per_source: int = 50, timeout: int = 15) -> list[dict]:
    """并行运行所有网页抓取器，返回标准化文章列表"""
    import concurrent.futures

    all_articles = []
    # 只跑 3 个 worker，避免过多并发连接
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}
        for key, cfg in SCRAPER_REGISTRY.items():
            # 跳过已知不可达或已被 RSS 完全覆盖的 scraper
            if key in ("alaraby", "alarabiya_en", "gcc"):
                continue
            futures[executor.submit(cfg["func"])] = cfg

        for fut in concurrent.futures.as_completed(futures):
            cfg = futures[fut]
            try:
                articles = fut.result(timeout=timeout)
                count = 0
                for art in articles[:max_per_source]:
                    if art.get("title") and art.get("url"):
                        all_articles.append({
                            "title": art.get("title", "").strip(),
                            "url": art.get("url", "").strip(),
                            "summary": art.get("summary", "")[:500],
                            "pub_date": art.get("pub_date", ""),
                            "source": cfg["name"],
                            "lang": cfg["lang"],
                        })
                        count += 1
                print(f"[SCRAPER] {cfg['name']} — {count} articles")
            except Exception as exc:
                print(f"[SCRAPER] {cfg['name']} — SKIP: {type(exc).__name__}")

    return all_articles
