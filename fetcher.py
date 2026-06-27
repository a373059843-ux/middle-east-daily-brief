"""
RSS 抓取器：并行抓取、代理支持、去重、分类
"""
import concurrent.futures
import os
import ssl
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
from urllib.parse import urlparse, urlunparse
from urllib.request import ProxyHandler, build_opener, install_opener, HTTPSHandler
import urllib.request as urllib_request

import feedparser

from config import (
    RSS_FEEDS,
    FETCH_TIMEOUT,
    MAX_CONCURRENT,
    TITLE_SIMILARITY_THRESHOLD,
    CATEGORY_KEYWORDS,
    FALLBACK_CATEGORY,
    FALLBACK_EMOJI,
    FALLBACK_LABEL_EN,
    FALLBACK_LABEL_ZH,
    MIDDLE_EAST_FILTER,
    MAX_ARTICLE_AGE_HOURS,
)


def _setup_urllib():
    """为 feedparser 配置代理和 SSL"""
    # 尝试从环境变量读取代理
    proxies = {}
    for env_key in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
        val = os.environ.get(env_key, "")
        if val:
            proxies["https"] = val
            proxies["http"] = val
            break

    # 放宽 SSL（部分 RSS 源证书可能有兼容性问题，如 Al Riyadh）
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    feedparser.PREFERRED_SSL_CONTEXT = ssl_ctx

    if proxies:
        handler = ProxyHandler(proxies)
        opener = build_opener(handler, context=ssl_ctx)
        install_opener(opener)
        print(f"[PROXY] 已设置代理: {proxies}")

    # Monkey-patch feedparser.http 以注入 SSL context
    # feedparser 内部使用 build_opener() 创建新的 opener，不会使用全局 install_opener
    _patch_feedparser_ssl(ssl_ctx)


def _patch_feedparser_ssl(ssl_ctx):
    """修改 feedparser.http.get 使其使用自定义 SSL context"""
    import feedparser.http as fp_http
    _original_get = fp_http.get
    _original_build_opener = urllib_request.build_opener

    def _patched_build_opener(*handlers):
        """注入自定义 SSL context 到 HTTPSHandler"""
        # 替换所有默认 HTTPSHandler 为使用自定义 SSL context 的
        from urllib.request import HTTPSHandler
        has_https = any(isinstance(h, HTTPSHandler) for h in handlers)
        if not has_https:
            handlers = tuple(handlers) + (HTTPSHandler(context=ssl_ctx),)
        else:
            handlers = tuple(
                HTTPSHandler(context=ssl_ctx) if isinstance(h, HTTPSHandler) else h
                for h in handlers
            )
        return _original_build_opener(*handlers)

    # 修改 feedparser.http 模块中的 build_opener 引用
    urllib_request.build_opener = _patched_build_opener



# 模块导入时自动配置
_setup_urllib()


def _normalize_url(url: str) -> str:
    """统一 URL 格式：小写 scheme+host，去除 fragment"""
    p = urlparse(url)
    scheme = p.scheme.lower()
    host = p.hostname or ""
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    path = p.path.rstrip("/") or "/"
    return urlunparse((scheme, host, path, "", "", ""))


def _compute_title_fingerprint(title: str) -> str:
    """对标题做轻量标准化"""
    t = title.strip().lower()
    for ch in ":：-—–'\"“”‘’«»":
        t = t.replace(ch, " ")
    words = [w for w in t.split() if w]
    return " ".join(words)


def _titles_similar(a: str, b: str) -> bool:
    """两个标题是否高度相似"""
    s = SequenceMatcher(None, a, b).ratio()
    return s >= TITLE_SIMILARITY_THRESHOLD


def categorize(title: str, summary: str) -> dict:
    """根据标题和摘要返回分类信息"""
    text = (title + " " + summary).lower()
    for cat_key, cat_def in CATEGORY_KEYWORDS.items():
        for kw in cat_def["keywords"]:
            if kw in text:
                return {
                    "key": cat_key,
                    "emoji": cat_def["emoji"],
                    "label_en": cat_def["label_en"],
                    "label_zh": cat_def["label_zh"],
                }
    return {
        "key": FALLBACK_CATEGORY,
        "emoji": FALLBACK_EMOJI,
        "label_en": FALLBACK_LABEL_EN,
        "label_zh": FALLBACK_LABEL_ZH,
    }


def _fetch_one(feed_def: dict) -> list[dict]:
    """抓取单个 RSS 源，返回文章列表，失败或超时返回空列表"""
    name = feed_def["name"]
    url = feed_def["url"]
    try:
        parsed = feedparser.parse(
            url,
            agent="Mozilla/5.0 (compatible; MiddleEastBot/1.0)",
            response_headers={"Accept": "application/rss+xml, application/xml, text/xml, */*"},
        )
    except Exception as exc:
        print(f"[WARN] {name}: {exc}")
        return []

    # bozo 只是非致命解析警告，如果有条目仍然使用
    if parsed.bozo and not parsed.entries:
        bozo = str(parsed.bozo_exception)[:120] if parsed.bozo_exception else "unknown"
        print(f"[WARN] {name}: 解析错误 / 无条目 — {bozo}")
        return []

    if parsed.bozo and parsed.entries:
        print(f"[NOTE] {name}: 有 {len(parsed.entries)} 条有效条目 (忽略非致命 XML 警告)")
    elif not parsed.entries:
        print(f"[NOTE] {name}: 无可抓取条目")
        return []

    articles = []
    from re import sub as re_sub

    for entry in parsed.entries:
        title = entry.get("title", "").strip()
        if not title:
            continue

        link = entry.get("link", "").strip()
        if isinstance(link, str) and link.startswith(">"):
            # Some feeds (e.g. Al Riyadh) emit malformed URLs like ">http://..."
            _, _, link = link.partition(">")
        # Normalize "http:/domain/path" (single-slash scheme) to "http://domain/path"
        if isinstance(link, str) and link.startswith("http:/") and not link.startswith("http://"):
            link = link.replace("http:/", "http://", 1)
        if isinstance(link, str) and link.startswith("https:/") and not link.startswith("https://"):
            link = link.replace("https:/", "https://", 1)
        link = link.strip()
        if not link and hasattr(entry, "guid"):
            link = entry.get("guid", "").strip()

        summary = ""
        if hasattr(entry, "summary"):
            summary = entry.get("summary", "")
        elif hasattr(entry, "description"):
            summary = entry.get("description", "")
        summary = re_sub(r"<[^>]+>", "", summary).strip() or ""

        pub_date = ""
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                pub_date = dt.isoformat()
            except (ValueError, TypeError):
                pass
        if not pub_date and hasattr(entry, "published"):
            pub_date = entry.get("published", "")

        articles.append({
            "title": title,
            "url": link,
            "summary": summary[:500],
            "pub_date": pub_date,
            "source": name,
            "lang": feed_def.get("lang", "en"),
        })

    return articles


def _filter_by_age(articles: list[dict], max_hours: int) -> list[dict]:
    """丢弃超过 max_hours 小时的旧文章（无 pub_date 的保留）"""
    if max_hours <= 0:
        return articles
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_hours)
    kept = []
    dropped = 0
    for art in articles:
        pd = art.get("pub_date", "")
        if not pd:
            # 没有日期信息的保留
            kept.append(art)
        else:
            try:
                dt = datetime.fromisoformat(pd)
                if dt >= cutoff:
                    kept.append(art)
                else:
                    dropped += 1
            except (ValueError, TypeError):
                kept.append(art)
    if dropped:
        print(f"[FILTER] 丢弃 {dropped} 篇超过 {max_hours} 小时的旧报道")
    return kept


def fetch_all() -> list[dict]:
    """并行抓取所有 RSS 源 + 网页抓取，返回去重+分类后的文章列表"""
    import scraper as _scraper
    all_articles: list[dict] = []

    # --- 1. RSS 抓取 ---
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as executor:
        futures = {executor.submit(_fetch_one, fd): fd for fd in RSS_FEEDS}
        for fut in concurrent.futures.as_completed(futures):
            fd = futures[fut]
            try:
                articles = fut.result()
                print(f"[RSS] {fd['name']} — {len(articles)} 篇")
                all_articles.extend(articles)
            except Exception as exc:
                print(f"[ERR] {fd['name']}: {exc}")

    # --- 2. 网页抓取（为没有 RSS 的网站补充内容） ---
    print("\n--- 网页抓取 ---")
    scraper_articles = _scraper.scrape_all()
    for art in scraper_articles:
        # 标准化字段以匹配 RSS 格式
        all_articles.append({
            "title": art["title"],
            "url": art["url"],
            "summary": art.get("summary", ""),
            "pub_date": art.get("pub_date", ""),
            "source": art["source"],
            "lang": art.get("lang", "en"),
        })

    print(f"\n总计 {len(all_articles)} 篇 (RSS + Scraper, 去重前)")

    # 过滤 24 小时以外的旧报道
    filtered = _filter_by_age(all_articles, MAX_ARTICLE_AGE_HOURS)

    deduped = _deduplicate(filtered)
    print(f"去重后 {len(deduped)} 篇")

    for art in deduped:
        art["category"] = categorize(art["title"], art.get("summary", ""))

    deduped.sort(key=lambda a: a.get("pub_date", ""), reverse=True)
    return deduped


def _deduplicate(articles: list[dict]) -> list[dict]:
    """两步去重：URL 精确匹配 + 标题相似度"""
    seen_urls: set[str] = set()
    result: list[dict] = []

    for art in articles:
        url = art.get("url", "")
        norm = _normalize_url(url) if url else ""
        if norm and norm in seen_urls:
            continue
        if norm:
            seen_urls.add(norm)

        fp = _compute_title_fingerprint(art["title"])
        dup = False
        for kept in result:
            kept_fp = _compute_title_fingerprint(kept["title"])
            if fp == kept_fp or _titles_similar(fp, kept_fp):
                dup = True
                break
        if dup:
            continue

        result.append(art)

    return result
