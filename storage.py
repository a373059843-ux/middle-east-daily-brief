"""
JSON 数据持久化
"""
import json
import os
from datetime import date, datetime, timedelta

from config import DATA_RETENTION_DAYS

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _date_to_str(d: date) -> str:
    return d.isoformat()


def _str_to_date(s: str) -> date:
    return date.fromisoformat(s)


def save_digest(d: date, articles: list[dict]) -> str:
    """保存每日摘要 → 返回文件路径"""
    _ensure_dir()
    filename = f"{_date_to_str(d)}.json"
    filepath = os.path.join(DATA_DIR, filename)
    payload = {
        "date": _date_to_str(d),
        "generated_at": datetime.now().isoformat(),
        "total_articles": len(articles),
        "articles": articles,
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[SAVED] {filepath}")
    return filepath


def load_digest(d: date) -> dict | None:
    """读取指定日期摘要，不存在返回 None"""
    filepath = os.path.join(DATA_DIR, f"{_date_to_str(d)}.json")
    if not os.path.isfile(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def list_dates() -> list[date]:
    """列出 data/ 下所有已有摘要的日期，降序排列"""
    _ensure_dir()
    dates = []
    for fn in os.listdir(DATA_DIR):
        if fn.endswith(".json"):
            try:
                d = _str_to_date(fn[:-5])
                dates.append(d)
            except ValueError:
                continue
    dates.sort(reverse=True)
    return dates


def cleanup_old():
    """删除超过 DATA_RETENTION_DAYS 的旧摘要"""
    if DATA_RETENTION_DAYS <= 0:
        return
    cutoff = date.today() - timedelta(days=DATA_RETENTION_DAYS)
    _ensure_dir()
    for fn in os.listdir(DATA_DIR):
        if not fn.endswith(".json"):
            continue
        filepath = os.path.join(DATA_DIR, fn)
        try:
            d = _str_to_date(fn[:-5])
            if d < cutoff:
                os.remove(filepath)
                print(f"[CLEANUP] 删除过期文件: {fn}")
        except (ValueError, OSError):
            continue
