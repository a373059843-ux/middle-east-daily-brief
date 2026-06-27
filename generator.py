"""
HTML 仪表盘生成器 — 四栏报纸风格日报
输出为完全自包含的单个 HTML 文件（CSS 内联），无需服务器即可在任何浏览器打开。
"""
import os
import re
from datetime import date

from jinja2 import Environment, FileSystemLoader

from storage import load_digest, list_dates

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)

# 四栏顺序
COLUMN_ORDER = ["political", "diplomacy", "economy", "military"]

# 栏位元数据
COLUMN_META = {
    "political":  {"emoji": "🏛️", "zh": "政治", "en": "Politics", "css": "col-political"},
    "diplomacy":  {"emoji": "🌍", "zh": "外交", "en": "Diplomacy", "css": "col-diplomacy"},
    "economy":    {"emoji": "💰", "zh": "经济", "en": "Economy", "css": "col-economy"},
    "military":   {"emoji": "⚔️", "zh": "军事冲突", "en": "Military / Conflict", "css": "col-military"},
}

# 用于 general 文章智能重分配的关键词模式
_COLUMN_PATTERNS = {
    "military": [
        r'\b(war|military|troops|soldier|army|navy|air force|strike|airstrike|missile|drone|drones|attack|assault|offensive|battle|fighting|clash|ceasefire|cease-fire|truce|conflict|hostilit|bombing|bombardment|shelling|rocket|artillery|tank|fighter jet|militia|armed|weapon|casualt|killed|wounded|dead|death toll|idf|hezbollah|hamas|houthi|rebel|insurgent|breaking|urgent|crisis|emergency|explosion|blast|terror|massacre)',
        r'\b(حرب|عسكري|جيش|قوات|جنود|بحرية|غارة|صاروخ|طائرة مسيرة|هجوم|معركة|قتال|اشتباك|وقف إطلاق|هدنة|نزاع|قصف|قذائف|صواريخ|مدفعية|دبابة|مقاتلة|ميليشيا|مسلح|سلاح|عنف|ضحايا|قتلى|جرحى|متمرد|حزب الله|حماس|حوثي|عاجل|طارئ|أزمة|طوارئ|انفجار|إرهاب|قنبلة|مذبحة)',
    ],
    "economy": [
        r'\b(economy|economic|inflation|gdp|growth|oil|gas|energy|petroleum|opec|sanctions|trade|export|import|tariff|investment|market|stock|currency|dollar|budget|debt|deficit|bank|finance|prices|fuel|subsid|agricultur|crop|harvest|farm)',
        r'\b(اقتصاد|اقتصادي|تضخم|نمو|ناتج|نفط|غاز|طاقة|بترول|عقوبات|تجارة|تصدير|استيراد|استثمار|سوق|أسهم|عملة|دولار|ميزانية|دين|عجز|بنوك|أسعار|وقود|دعم|زراع|محصول|حصاد)',
    ],
    "diplomacy": [
        r'\b(diplomacy|diplomat|diplomatic|talks|negotiation|summit|meeting|foreign minister|envoy|ambassador|united nations|security council|nato|peace|treaty|agreement|accord|deal|mediation|mediator|state visit|bilateral|multilateral|alliance|ally|allies|relations|dialogue|resolution|condemn)',
        r'\b(دبلوماسية|دبلوماسي|محادثات|مفاوضات|قمة|اجتماع|وزير خارجية|مبعوث|سفير|أمم متحدة|مجلس أمن|سلام|معاهدة|اتفاق|وساطة|وسيط|زيارة|تحالف|حليف|علاقات|حوار|قرار|بيان|يدين|إدانة|تطبيع)',
    ],
}


def _reassign_general(art: dict) -> str:
    """尝试将 general 分类文章重新分配到合适的栏位"""
    text = (art.get("title", "") + " " + art.get("summary", "")).lower()
    for col, patterns in _COLUMN_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, text):
                return col
    return "political"  # 默认归入政治


def _group_by_column(articles: list[dict]) -> dict[str, dict]:
    """将文章按四栏分组，未匹配的默认归入 political"""
    groups: dict[str, dict] = {k: {"key": k, **COLUMN_META[k], "articles": []} for k in COLUMN_ORDER}
    for art in articles:
        cat_key = art.get("category", {}).get("key", "general")
        # breaking → military
        if cat_key == "breaking":
            cat_key = "military"
        # general → 智能重分配
        elif cat_key == "general":
            cat_key = _reassign_general(art)
        col = cat_key if cat_key in COLUMN_ORDER else "political"
        groups[col]["articles"].append(art)
    return groups


def _count_by_column(article_groups: dict) -> dict:
    counts = {}
    for key, grp in article_groups.items():
        counts[key] = {
            "key": key,
            "emoji": COLUMN_META[key]["emoji"],
            "label_zh": COLUMN_META[key]["zh"],
            "label_en": COLUMN_META[key]["en"],
            "count": len(grp["articles"]),
        }
    return counts


def generate(d: date | None = None, output_name: str = "index.html") -> str:
    """生成指定日期的四栏日报 HTML → 返回输出文件路径"""
    if d is None:
        d = date.today()

    digest = load_digest(d)
    all_dates = list_dates()

    if digest is None:
        articles = []
        total = 0
    else:
        articles = digest.get("articles", [])
        total = digest.get("total_articles", len(articles))

    article_groups = _group_by_column(articles)
    column_counts = _count_by_column(article_groups)

    # 按 pub_date 降序排列每组内的文章
    for key in article_groups:
        article_groups[key]["articles"].sort(
            key=lambda a: a.get("pub_date", ""), reverse=True
        )

    # 计算前后一天
    prev_date = None
    next_date = None
    for i, dt in enumerate(all_dates):
        if dt == d:
            if i + 1 < len(all_dates):
                prev_date = all_dates[i + 1]
            if i - 1 >= 0:
                next_date = all_dates[i - 1]
            break

    if not digest and all_dates:
        prev_date = all_dates[0]

    template = _env.get_template("dashboard.html")
    html = template.render(
        date=d.isoformat(),
        date_display=d.strftime("%Y-%m-%d"),
        total_articles=total,
        article_groups=article_groups,
        column_counts=column_counts,
        prev_date=prev_date.isoformat() if prev_date else None,
        next_date=next_date.isoformat() if next_date else None,
        has_prev=prev_date is not None,
        has_next=next_date is not None,
        all_dates=[dt.isoformat() for dt in all_dates],
    )

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, output_name)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[GENERATED] {output_path}")
    return output_path
