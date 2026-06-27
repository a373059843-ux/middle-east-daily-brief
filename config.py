"""
RSS 新闻源 & 分类关键词配置

来源覆盖（RSS + 网页抓取）：
  www.txt 中 13 个网站，全部有对应的信息获取路径：
  - 可用 RSS：SANA, AA, Al Riyadh, Anadolu EN, Al-Monitor, Daily News Egypt,
    Jerusalem Post, UN News, The National, Press TV, Arab News, Gulf News,
    Khaleej Times, Zawya, Al Arabiya, BBC, Al Jazeera, Haaretz, The New Arab
  - 网页抓取（scraper.py）：Youm7, Ahram Gate, SPA, GCC, QNA, Al Araby,
    Reuters, Al Jazeera EN, Al Arabiya EN（详见 scraper.py 注册表）
"""
RSS_FEEDS = [
    # ============ 已确认可用 RSS ============
    {
        "name": "Anadolu Agency (TR)",
        "url": "https://www.aa.com.tr/en/rss/default?cat=middle-east",
        "lang": "en",
    },
    {
        "name": "Al-Monitor",
        "url": "https://www.al-monitor.com/feed",
        "lang": "en",
    },
    {
        "name": "Daily News Egypt",
        "url": "https://www.dailynewsegypt.com/feed",
        "lang": "en",
    },
    # --- 阿拉伯语 RSS ---
    {
        "name": "SANA — الوكالة العربية السورية للأنباء",
        "url": "https://www.sana.sy/?feed=rss2",
        "lang": "ar",
    },
    {
        "name": "Anadolu Ajansı عربي (TR)",
        "url": "https://www.aa.com.tr/ar/rss/default?cat=guncel",
        "lang": "ar",
    },
    {
        "name": "Al Riyadh — جريدة الرياض (SA)",
        "url": "https://www.alriyadh.com/section.main.xml",
        "lang": "ar",
    },
    # --- 原有英文 RSS ---
    {
        "name": "The Jerusalem Post",
        "url": "https://www.jpost.com/rss/rssfeedsfrontpage.aspx",
        "lang": "en",
    },
    {
        "name": "UN News — Middle East",
        "url": "https://news.un.org/feed/subscribe/en/news/region/middle-east/feed/rss.xml",
        "lang": "en",
    },
    # --- The National (UAE) - 偶尔波动但可用 ---
    {
        "name": "The National (UAE)",
        "url": "https://www.thenational.ae/arc/outboundfeeds/rss/?outputType=xml",
        "lang": "en",
    },
    {
        "name": "Press TV (Iran)",
        "url": "https://www.presstv.ir/rss/latest",
        "lang": "en",
    },
]

# --- 抓取设置 ---
FETCH_TIMEOUT = 15          # 单个源超时秒数
MAX_CONCURRENT = 6          # 最大并行抓取数
TITLE_SIMILARITY_THRESHOLD = 0.82   # difflib 标题相似度去重阈值
MAX_ARTICLE_AGE_HOURS = 24  # 只保留最近 N 小时内的报道，超出丢弃

# --- 调度设置 (24 小时制) ---
SCHEDULE_TIMES = ["22:00"]  # 北京时间每天 22:00 抓取

# --- 数据保留 ---
DATA_RETENTION_DAYS = 0     # 设为 0 表示永久保留，不自动删除

# --- 本地服务端口 ---
HTTP_PORT = 8765

# ============================================================
#  分类关键词（英语 + 阿拉伯语，均转为小写匹配）
# ============================================================
CATEGORY_KEYWORDS = {
    "political": {
        "emoji": "🏛️",
        "label_en": "Politics",
        "label_zh": "政治",
        "keywords": [
            # English
            "election", "government", "parliament", "president", "minister",
            "vote", "voting", "referendum", "constitution", "congress",
            "legislation", "bill", "lawmaker", "opposition", "party",
            "protest", "protests", "protesters", "demonstration", "rally",
            "coup", "regime", "authority", "cabinet", "resign",
            "prime minister", "presidency", "senate", "assembly", "ruling",
            "reform", "political", "politician", "opposition",
            # Arabic
            "انتخابات", "حكومة", "برلمان", "رئيس", "وزير",
            "تصويت", "استفتاء", "دستور", "مجلس", "تشريع",
            "قانون", "معارضة", "حزب", "احتجاج", "احتجاجات",
            "متظاهر", "مظاهرة", "انقلاب", "نظام", "سلطة",
            "استقالة", "رئيس وزراء", "مجلس شيوخ", "إصلاح", "سياسي",
            "سياسة", "حاكم", "انتخابي",
        ],
    },
    "military": {
        "emoji": "⚔️",
        "label_en": "Military / Conflict",
        "label_zh": "军事/冲突",
        "keywords": [
            # English
            "war", "military", "troops", "soldiers", "army", "navy", "air force",
            "strike", "air strike", "airstrike", "missile", "drone", "drones",
            "attack", "assault", "offensive", "battle", "fighting", "clashes",
            "ceasefire", "cease-fire", "truce", "conflict", "hostilities",
            "bombing", "bombardment", "shelling", "rocket", "artillery",
            "tank", "fighter jet", "deployment", "militia", "armed",
            "weapon", "weapons", "violence", "casualties", "killed", "wounded",
            "idf", "hezbollah", "hamas", "houthi", "rebels", "insurgent",
            # Arabic
            "حرب", "عسكري", "جيش", "قوات", "جنود", "بحرية", "سلاح جو",
            "غارة", "غارة جوية", "صاروخ", "طائرة مسيرة", "طائرات مسيرة",
            "هجوم", "اعتداء", "معركة", "قتال", "اشتباكات", "اشتباك",
            "وقف إطلاق نار", "هدنة", "نزاع", "أعمال عدائية",
            "قصف", "قذائف", "صواريخ", "مدفعية", "دبابة", "مقاتلة",
            "انتشار", "ميليشيا", "مسلح", "سلاح", "أسلحة", "عنف",
            "ضحايا", "قتلى", "جرحى", "متمرد", "متمردون",
            "حزب الله", "حماس", "حوثي", "حوثيون", "جيش دفاع",
        ],
    },
    "economy": {
        "emoji": "💰",
        "label_en": "Economy",
        "label_zh": "经济",
        "keywords": [
            # English
            "economy", "economic", "inflation", "gdp", "growth",
            "oil", "gas", "energy", "petroleum", "opec",
            "sanctions", "trade", "export", "import", "tariff",
            "investment", "market", "stock", "currency", "dollar",
            "budget", "debt", "deficit", "banking", "finance", "financial",
            "prices", "cost of living", "fuel", "subsidy",
            # Arabic
            "اقتصاد", "اقتصادي", "تضخم", "نمو", "ناتج محلي",
            "نفط", "غاز", "طاقة", "بترول", "أوبك",
            "عقوبات", "تجارة", "تصدير", "استيراد", "رسوم",
            "استثمار", "سوق", "أسهم", "عملة", "دولار",
            "ميزانية", "دين", "عجز", "بنوك", "مصرفي", "مالية",
            "أسعار", "تكلفة معيشة", "وقود", "دعم", "بورصة",
        ],
    },
    "diplomacy": {
        "emoji": "🌍",
        "label_en": "Diplomacy",
        "label_zh": "外交",
        "keywords": [
            # English
            "diplomacy", "diplomat", "diplomatic", "talks", "negotiation",
            "summit", "meeting", "foreign minister", "envoy", "ambassador",
            "united nations", "security council", "un ", "u.n.", "nato",
            "peace", "treaty", "agreement", "accord", "deal",
            "mediation", "mediator", "state visit", "bilateral", "multilateral",
            "alliance", "ally", "allies", "relations", "dialogue",
            "resolution", "statement", "condemns", "condemnation",
            # Arabic
            "دبلوماسية", "دبلوماسي", "محادثات", "مفاوضات", "تفاوض",
            "قمة", "اجتماع", "وزير خارجية", "مبعوث", "سفير",
            "أمم متحدة", "مجلس أمن", "ناتو", "سلام",
            "معاهدة", "اتفاق", "اتفاقية", "صفقة",
            "وساطة", "وسيط", "زيارة دولة", "ثنائي", "متعدد أطراف",
            "تحالف", "حليف", "حلفاء", "علاقات", "حوار",
            "قرار", "بيان", "يدين", "إدانة", "تطبيع",
        ],
    },
    "breaking": {
        "emoji": "🔴",
        "label_en": "Breaking / Crisis",
        "label_zh": "突发事件",
        "keywords": [
            # English
            "breaking", "urgent", "developing", "alert",
            "crisis", "emergency", "explosion", "blast", "earthquake",
            "flood", "disaster", "evacuation", "hostage", "kidnap",
            "terror", "terrorist", "terrorism", "bomb", "shooting",
            "death toll", "dead", "killed", "massacre", "genocide",
            # Arabic
            "عاجل", "طارئ", "أزمة", "طوارئ", "انفجار",
            "زلزال", "فيضان", "كارثة", "إخلاء", "رهينة", "اختطاف",
            "إرهاب", "إرهابي", "قنبلة", "إطلاق نار",
            "حصيلة قتلى", "قتلى", "مذبحة", "إبادة", "ضرب",
        ],
    },
}

# 未匹配到任何关键词时，放入此分类
FALLBACK_CATEGORY = "general"
FALLBACK_EMOJI = "📰"
FALLBACK_LABEL_EN = "General"
FALLBACK_LABEL_ZH = "综合"

# --- 中东相关过滤关键词（用于过滤不含"中东"字段的通用源） ---
MIDDLE_EAST_FILTER = [
    "middle east", "israel", "gaza", "palestine", "palestinian",
    "iran", "iraq", "syria", "lebanon", "jordan", "egypt",
    "saudi arabia", "saudi", "uae", "emirates", "qatar", "kuwait",
    "oman", "bahrain", "yemen", "turkey", "türkiye", "libya",
    "hezbollah", "hamas", "houthi", "idf", "west bank", "jerusalem",
    "tel aviv", "tehran", "riyadh", "dubai", "doha", "ankara",
    "gulf", "arab", "arabian", "levant", "mesopotamia",
]
